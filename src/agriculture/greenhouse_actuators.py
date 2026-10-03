"""GreenhouseActuators — atuadores da estufa setorial (gap_2).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs.gap_2_greenhouse_actuators

LED 450+660nm, válvula CO2, bombas de nutrientes N/P/K/Ca/Mg/S/Fe/Zn,
aquecedor 5kW, mister. Decisões (geophysical/IA) executam; invariant vigia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LEDArray:
    wavelengths_nm: List[int] = field(default_factory=lambda: [450, 660])
    max_intensity: float = 1.0
    intensity: float = 0.0

    def set_intensity(self, value: float) -> None:
        self.intensity = float(max(0.0, min(self.max_intensity, value)))


@dataclass
class CO2Valve:
    max_ppm: float = 2000.0
    ppm: float = 0.0

    def open(self, ppm: float) -> None:
        self.ppm = float(max(0.0, min(self.max_ppm, ppm)))


@dataclass
class NutrientPumps:
    elements: List[str] = field(default_factory=lambda: ["N", "P", "K", "Ca", "Mg", "S", "Fe", "Zn"])
    flow: Dict[str, float] = field(default_factory=dict)
    active_injection_rate: float = 0.004  # fração de reserva por passo

    def inject(self, amounts: Dict[str, float]) -> None:
        for k, v in amounts.items():
            if k in self.elements:
                self.flow[k] = self.flow.get(k, 0.0) + float(v)

    def respond_to_deficit(self, reserves: Dict[str, float], threshold: float = 0.6) -> Dict[str, float]:
        """Injeção ATIVA quando déficit (achado d2/d3): sem bombas ativas, os
        nutrientes colapsam e o gate evolutivo (d3) nunca passa."""
        injected: Dict[str, float] = {}
        for k in self.elements:
            if reserves.get(k, 0.0) < threshold:
                amt = self.active_injection_rate
                self.flow[k] = self.flow.get(k, 0.0) + amt
                injected[k] = amt
        return injected


@dataclass
class Heater:
    max_power_kw: float = 5.0
    power_kw: float = 0.0

    def set_power(self, kw: float) -> None:
        self.power_kw = float(max(0.0, min(self.max_power_kw, kw)))


@dataclass
class Mister:
    flow_rate_l_h: float = 10.0
    active: bool = False


class GreenhouseActuators:
    """Abstração dos atuadores da estufa marciana."""

    SUPPORTED = {"increase_light", "decrease_light", "inject_co2", "inject_nutrients",
                 "heat", "mist", "emergency_shutdown"}

    def __init__(self) -> None:
        self.led_array = LEDArray()
        self.co2_valve = CO2Valve()
        self.nutrient_pumps = NutrientPumps()
        self.heater = Heater()
        self.mister = Mister()
        self.last_action: str | None = None
        self.safety_override: bool = False

    def execute(self, action: Dict[str, Any]) -> bool:
        """Executa uma decisão. Canal Terra pode forçar via safety_override."""
        a_type = action.get("type")
        if a_type not in self.SUPPORTED:
            return False
        if self.safety_override and a_type != "emergency_shutdown":
            return False  # override soberano bloqueia
        if a_type == "increase_light":
            self.led_array.set_intensity(action.get("intensity", 1.0))
        elif a_type == "decrease_light":
            self.led_array.set_intensity(action.get("intensity", 0.0))
        elif a_type == "inject_co2":
            self.co2_valve.open(action.get("ppm", 1000.0))
        elif a_type == "inject_nutrients":
            self.nutrient_pumps.inject(action.get("amounts", {}))
        elif a_type == "heat":
            self.heater.set_power(action.get("kw", 0.0))
        elif a_type == "mist":
            self.mister.active = bool(action.get("on", True))
        elif a_type == "emergency_shutdown":
            self.led_array.set_intensity(0.0)
            self.co2_valve.open(0.0)
            self.heater.set_power(0.0)
            self.mister.active = False
        self.last_action = a_type
        return True

    def read_state(self) -> Dict[str, Any]:
        return {
            "led_intensity": self.led_array.intensity,
            "co2_ppm": self.co2_valve.ppm,
            "nutrient_flow": dict(self.nutrient_pumps.flow),
            "heater_kw": self.heater.power_kw,
            "mister_active": self.mister.active,
            "safety_override": self.safety_override,
            "last_action": self.last_action,
        }
