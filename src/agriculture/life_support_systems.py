"""LifeSupportSystems — suporte de vida além do ECLSS (gap_11).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs_critical.gap_11

Reator de algas (Spirulina: O2 + proteína 60-70%), digestor anaeróbio
(biomassa -> CH4 + CO2 + digestato), célula de combustível (H2+O2 -> H2O +
eletricidade), reator de plasma (resíduos -> syngas CO+H2). Referências:
MELiSSA (ESA), BIOS-3, fuel cells na ISS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class IceElevatorSupply:
    """Gelo dos elevadores (-500m) — fluxo CONTÍNUO de água (achado d2/d3).

    Sem fluxo contínuo, a água colapsa para ~40% e o gate batata->trigo
    (exige 80% de reserva) fica inatingível. O elevador entrega uma vazão
    contínua + reforço emergencial quando o tanque cai abaixo do piso.

    Config v5 (sweep 2026-09-28): 10 agentes × 2.5 L/dia exige fluxo 2.5 L/sol
    e reservatório ~20.000 L (emergência a 2.000 L) — o default antigo
    (0.25 L/sol) mantinha o buffer real em ~170 L, operando no limite.
    """

    flow_l_per_sol: float = 2.5
    emergency_l: float = 150.0
    emergency_threshold_l: float = 2000.0

    def step(self, water_l: float) -> float:
        """Retorna a água entregue neste sol (contínua + emergencial)."""
        delivered = self.flow_l_per_sol
        if water_l < self.emergency_threshold_l:
            delivered += self.emergency_l
        return delivered


@dataclass
class ElectrolysisOGS:
    """Eletrólise da água — backup de O2 não-biológico (conglomerar ISS/ECLSS).

    Verificação 2026-09-28: BIOS-3/Lunar Palace fecham ~100% do O2 por
    fotossíntese; o Monoculture fica em 92% — a eletrólise OGS da ISS
    (água + 4.3 kWh/kg O2) cobre o déficit quando a biomassa não basta
    (poeira, hibernação, pico de consumo).
    """

    kwh_per_kg_o2: float = 4.3
    efficiency: float = 0.85  # Faraday real ~85%
    o2_kg_per_l_water: float = 0.89  # 1L H2O -> ~0.89 kg O2

    def produce(self, water_l: float, energy_kwh: float) -> dict:
        """O2 produzido limitado por água e energia disponíveis."""
        o2_by_water = water_l * self.o2_kg_per_l_water * self.efficiency
        o2_by_energy = energy_kwh / self.kwh_per_kg_o2
        o2 = max(0.0, min(o2_by_water, o2_by_energy))
        return {"o2_kg": round(o2, 4), "limiting": "water" if o2_by_water < o2_by_energy else "energy",
                "water_used_l": round(o2 / (self.o2_kg_per_l_water * self.efficiency), 3)}


@dataclass
class AlgaeReactor:
    """Spirulina produz O2 e proteína."""

    o2_per_kg_biomass: float = 1.3  # kg O2 / kg biomassa algácea
    protein_frac: float = 0.65

    def run(self, biomass_kg: float) -> Dict[str, float]:
        return {"o2_kg": biomass_kg * self.o2_per_kg_biomass,
                "protein_kg": biomass_kg * self.protein_frac}


@dataclass
class BiogasDigester:
    """Anaeróbio: biomassa -> CH4 + CO2 + digestato."""

    ch4_per_kg: float = 0.25
    digestate_frac: float = 0.4

    def digest(self, biomass_kg: float) -> Dict[str, float]:
        return {"ch4_kg": biomass_kg * self.ch4_per_kg,
                "co2_kg": biomass_kg * 0.2,
                "digestate_kg": biomass_kg * self.digestate_frac}


@dataclass
class HydrogenFuelCell:
    """H2 + O2 -> H2O + eletricidade."""

    kwh_per_kg_h2: float = 33.0  # energia útil ~33 kWh/kg H2

    def generate(self, h2_kg: float) -> float:
        return h2_kg * self.kwh_per_kg_h2


@dataclass
class PlasmaGasifier:
    """Plasma térmico: resíduos -> syngas (CO + H2)."""

    syngas_per_kg: float = 0.8
    h2_frac: float = 0.4

    def gasify(self, waste_kg: float) -> Dict[str, float]:
        syngas = waste_kg * self.syngas_per_kg
        return {"co_kg": syngas * (1.0 - self.h2_frac), "h2_kg": syngas * self.h2_frac}


class LifeSupportSystems:
    """Sistemas avançados de suporte de vida."""

    def __init__(self) -> None:
        self.algae_reactor = AlgaeReactor()
        self.biogas_digester = BiogasDigester()
        self.fuel_cell = HydrogenFuelCell()
        self.plasma_reactor = PlasmaGasifier()

    def process_waste(self, biomass_residual_kg: float) -> Dict[str, object]:
        """Digestão -> fuel cell -> plasma do digestato."""
        biogas = self.biogas_digester.digest(biomass_residual_kg)
        # CH4 para célula (proxy: reforma CH4->H2)
        h2_equiv = biogas["ch4_kg"] * 0.5
        electricity_kwh = self.fuel_cell.generate(h2_equiv)
        syngas = self.plasma_reactor.gasify(biogas["digestate_kg"])
        return {"biogas": biogas, "electricity_kwh": electricity_kwh, "syngas": syngas}
