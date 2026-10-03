"""MonodGrowthModel — crescimento de monocultura com fatores limitantes (gap_1).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs.gap_1_monod_growth_model

Crescimento logístico de Monod com lei do mínimo de Liebig:
    mu = mu_max * f_luz * f_temp * f_pH * f_CO2 * f_nutr
    dB/dt = mu * B * (1 - B/K)

Defaults por cultura (contrato): spirulina (mu_max 0.3, K 2.0, T 37, pH 9.5,
CO2 3%, luz 200), potato, dwarf_wheat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np


@dataclass
class CropParams:
    """Parâmetros ideais de uma cultura."""

    mu_max: float = 0.3
    K: float = 2.0
    temp_ideal_c: float = 37.0
    ph_ideal: float = 9.5
    co2_ideal_pct: float = 3.0
    light_ideal_umol: float = 200.0
    temp_sigma: float = 5.0
    ph_sigma: float = 1.0


CROP_DEFAULTS: Dict[str, CropParams] = {
    "spirulina": CropParams(),
    "chlorella": CropParams(mu_max=0.35, K=1.8, temp_ideal_c=30.0, ph_ideal=7.0,
                            co2_ideal_pct=4.0, light_ideal_umol=180.0),
    "potato": CropParams(mu_max=0.1, K=8.0, temp_ideal_c=20.0, ph_ideal=6.0,
                         co2_ideal_pct=1.5, light_ideal_umol=400.0),
    "dwarf_wheat": CropParams(mu_max=0.08, K=10.0, temp_ideal_c=22.0, ph_ideal=6.5,
                              co2_ideal_pct=1.5, light_ideal_umol=500.0),
    "wheat_bwt931": CropParams(mu_max=0.35, K=0.30, temp_ideal_c=22.0, ph_ideal=6.5,
                               co2_ideal_pct=1.5, light_ideal_umol=500.0),
}


class MonodGrowthModel:
    """Modelo de crescimento de monocultura (Spirulina, Batata, etc.)."""

    def __init__(self, crop_type: str = "spirulina",
                 mu_max: Optional[float] = None, K: Optional[float] = None) -> None:
        if crop_type not in CROP_DEFAULTS:
            raise ValueError(f"cultura desconhecida: {crop_type}")
        params = CROP_DEFAULTS[crop_type]
        self.crop_type = crop_type
        self.mu_max = mu_max if mu_max is not None else params.mu_max
        self.K = K if K is not None else params.K
        self.params = params
        self.biomass = 0.5  # kg/m³ inicial

    # --- fatores de limitação (0-1) ---
    LIGHT_QUALITY_BOOST = {"FL": 1.0, "RGB": 1.06, "RB": 1.12}  # Vitale 2022

    def light_factor(self, light_umol: float, light_mode: str = "FL",
                     radiation_stress: float = 0.0) -> float:
        """Luz + qualidade espectral (Vitale 2022: RB > RGB > FL) + radiação.

        Luz RB (red-blue) compensa o dano de radiação de íons pesados:
        fotossíntese base × boost espectral × (1 - 0.10×radiação).
        """
        base = float(min(1.0, light_umol / self.params.light_ideal_umol))
        boost = self.LIGHT_QUALITY_BOOST.get(light_mode, 1.0)
        damage = max(0.0, 1.0 - 0.10 * radiation_stress)
        return float(min(1.0, base * boost * damage))

    def temp_factor(self, temp_c: float) -> float:
        return float(np.exp(-((temp_c - self.params.temp_ideal_c) ** 2)
                            / (2 * self.params.temp_sigma ** 2)))

    def ph_factor(self, ph: float) -> float:
        return float(np.exp(-((ph - self.params.ph_ideal) ** 2)
                            / (2 * self.params.ph_sigma ** 2)))

    def co2_factor(self, co2_pct: float) -> float:
        return float(min(1.0, co2_pct / self.params.co2_ideal_pct))

    def nutrient_factor(self, nutrients: Dict[str, float]) -> float:
        """Lei do mínimo de Liebig: o nutriente mais escasso domina."""
        if not nutrients:
            return 0.0
        return float(min(nutrients.values()))

    # --- passo ---
    # --- Calibração BWT931 (Breadboard Project / KSC, trigo Yecora Rojo) ---
    # Dataset NASA NTRS 19940009506: câmara fechada 20 m², ~60 dias.
    # μ_max do trigo BWT931 ~0.35/dia, K_nutriente ~0.30 — o melhor dataset
    # quantitativo de cultura em câmara fechada (agente verificação 2026-09-28).
    BWT931_WHEAT_MU_MAX: float = 0.35
    BWT931_WHEAT_K: float = 0.30
    BWT931_WHEAT_CYCLE_DAYS: int = 60

    @classmethod
    def calibrate_wheat_bwt931(cls) -> "MonodGrowthModel":
        """Retorna um modelo de trigo calibrado com o dataset real BWT931."""
        return cls(crop_type="wheat_bwt931")

    # --- fatores emergentes P3/P4 (marcian_evolution) ---
    MARS_SOL_HOURS: float = 88775.244 / 3600.0  # 24.6598 h

    def circadian_factor(self, organism_period_h: float = 24.0,
                         sol_hours: float | None = None) -> float:
        """P3: dessincronia circadiana com o sol marciano custa fotossíntese.

        Organismo terrestre (24 h): mismatch 0.66 h -> ~0.72.
        Organismo entranhado (24.66 h): -> ~1.0 (+39% efetivo).
        """
        sol = self.MARS_SOL_HOURS if sol_hours is None else sol_hours
        return float(np.exp(-0.5 * abs(sol - organism_period_h)))

    def machine_symbiosis_factor(self, responsiveness: float,
                                 pump_light_overlap: float) -> float:
        """P4: plantas sincronizadas ao ciclo elétrico da máquina ganham
        eficiência fotossintética (bomba×luz coincidentes economizam energia)."""
        return float(1.0 + responsiveness * pump_light_overlap)

    def step(self, light_umol_m2_s: float, temp_c: float, ph: float,
             co2_percent: float, nutrients: Dict[str, float],
             dt_days: float = 1.0,
             circadian_period_h: float | None = None,
             machine_responsiveness: float | None = None,
             pump_light_overlap: float | None = None) -> Dict[str, float]:
        """Avança dt_days com fatores limitantes. Retorna estado do passo.

        Fatores emergentes opcionais (P3/P4): circadian_period_h aplica o
        custo de dessincronia com o sol de 24h39; machine_responsiveness +
        pump_light_overlap aplicam o ganho de simbiose máquina-planta.
        """
        factors = {
            "light": self.light_factor(light_umol_m2_s),
            "temp": self.temp_factor(temp_c),
            "ph": self.ph_factor(ph),
            "co2": self.co2_factor(co2_percent),
            "nutrient": self.nutrient_factor(nutrients),
        }
        if circadian_period_h is not None:
            factors["circadian"] = self.circadian_factor(circadian_period_h)
        if machine_responsiveness is not None and pump_light_overlap is not None:
            factors["machine"] = self.machine_symbiosis_factor(
                machine_responsiveness, pump_light_overlap)
        mu = self.mu_max
        for f in factors.values():
            mu *= f
        growth = mu * self.biomass * (1.0 - self.biomass / self.K)
        self.biomass += growth * dt_days
        self.biomass = float(max(0.0, min(self.K, self.biomass)))  # clamp [0, K]
        return {"biomass_kg_m3": self.biomass, "growth_rate": float(mu),
                "factors": factors}

    def reset(self, biomass: float = 0.5) -> None:
        self.biomass = float(biomass)

    def capacity_yield(self, stress: float = 1.0) -> float:
        """Yield de colheita NORMALIZADO por estresse (achado d2/d3).

        Mede a CAPACIDADE da cultivar (produção steady-state ~ mu_max*K/2),
        independente do clima: a poeira anual não pode punir a consistência —
        o estresse entra no componente stress_tolerance do gate
        (CultivarStabilityScore). O argumento stress é aceito por compatibilidade
        e NÃO afeta a capacidade (normalização deliberada).
        """
        return self.mu_max * self.K * 0.5
