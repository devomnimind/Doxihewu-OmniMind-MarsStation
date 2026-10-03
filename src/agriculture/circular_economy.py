"""circular_economy — NutrientCycleOptimizer (ação E3).

MARS_SYSTEM_CONTRACT.yaml · evolução E3 (economia circular)

Gargalo identificado na análise input-output: ciclo de nutrientes a 88%
(target MELiSSA 90%). Três alavancas de fechamento:
  1. Digestor anaeróbio mais eficiente (85% -> 92% de recuperação)
  2. Biorreator de nitrificação (NH4+ -> NO3-): perdas 5% -> 2%
  3. Recuperação de nutrientes da biomassa residual (pirólise vs digestão)

O otimizador combina as alavancas e reporta o novo grau de fechamento
por ciclo, com o gargalo residual.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UrineBrineProcessor:
    """Processador de urina/brine — água 98% (conglomerar ISS UPA+BPA).

    Verificação 2026-09-28: ECLSS atingiu 98% de recuperação (jun/2023) com
    UPA (destilação a vácuo, 85-87%) + Brine Processor (membrana). O
    Monoculture está em 95% — esta unidade eleva o fechamento da água.
    """

    upa_recovery: float = 0.87       # destilação a vácuo
    brine_processor_recovery: float = 0.85  # recupera o resto do concentrado
    tn_mg_n_l: float = 3500.0        # N total na urina (Fausta 2024)
    distiller_kwh_per_kg_n: float = 31.0   # Fumasoli/Fausta (Eawag)
    aeration_kwh_per_kg_n: float = 1.7     # UrinExpres (Eawag)
    def process(self, urine_l: float) -> dict:
        water_up = urine_l * self.upa_recovery
        brine = urine_l - water_up
        water_bp = brine * self.brine_processor_recovery
        total = water_up + water_bp
        kg_n = urine_l * self.tn_mg_n_l / 1e6
        energy_kwh = kg_n * (self.distiller_kwh_per_kg_n + self.aeration_kwh_per_kg_n)
        return {"water_recovered_l": round(total, 3),
                "water_recovered_pct": round(total / max(urine_l, 1e-9), 4),
                "urine_l": urine_l, "brine_residual_l": round(brine - water_bp, 3),
                "energy_kwh": round(energy_kwh, 3),
                "kwh_per_l": round(energy_kwh / max(urine_l, 1e-9), 4)}


@dataclass
class NutrientCycleOptimizer:
    """Otimiza o fechamento do ciclo de nutrientes (ação E3)."""

    digester_efficiency: float = 0.85      # recuperação do digestor (MELiSSA baseline)
    nitrification_loss: float = 0.05       # perda NH4+ -> NO3- (baseline)
    pyrolysis_recovery: float = 0.12       # extra de recuperação via pirólise do digestato
    use_pyrolysis: bool = True

    TARGET_CLOSURE = 0.90

    def step(self, biomass_residual_kg: float) -> Dict:
        """Um ciclo: digestão + nitrificação (+ pirólise). Retorna fechamentos."""
        # 1. digestão
        recovered = biomass_residual_kg * self.digester_efficiency
        digestate = biomass_residual_kg * (1.0 - self.digester_efficiency)
        # 2. pirólise do digestato (recupera N/P/K do carvão/lixiviado)
        if self.use_pyrolysis:
            recovered += digestate * self.pyrolysis_recovery
        # 3. nitrificação (NH4+ -> NO3-) com perda controlada
        nitrified = recovered * (1.0 - self.nitrification_loss)
        closure = min(1.0, nitrified / max(biomass_residual_kg, 1e-9))
        return {"closure": round(closure, 4), "recovered_kg": round(nitrified, 3),
                "digester_efficiency": self.digester_efficiency,
                "nitrification_loss": self.nitrification_loss,
                "use_pyrolysis": self.use_pyrolysis,
                "gargalo_residual": "none" if closure >= self.TARGET_CLOSURE else "nitrificacao"}

    def optimize(self) -> Dict:
        """Aplica as 3 alavancas (digestor 92%, nitrificação 2%, pirólise) e valida."""
        self.digester_efficiency = 0.92
        self.nitrification_loss = 0.02
        self.use_pyrolysis = True
        r = self.step(1.0)
        r["optimized"] = True
        return r

    def compare(self, biomass_residual_kg: float = 1.0) -> List[Dict]:
        """Baseline vs otimizado."""
        baseline = NutrientCycleOptimizer(digester_efficiency=0.85,
                                          nitrification_loss=0.05, use_pyrolysis=False)
        return [{"config": "baseline_melissa", **baseline.step(biomass_residual_kg)},
                {"config": "optimized", **self.step(biomass_residual_kg)}]


@dataclass
class ThermophilicChainElongator:
    """Digestor termofílico com T. melissae — n-caproato de polissacarídeos.

    Nguyen et al. IJSEM 2023 (Thermocaproicibacter melissae, do consórcio
    MELiSSA C-I): digestor acidogênico termofílico de resíduos humanos que
    produz n-caproato (MCCA C6 — biocombustível/precursor) a 50-55 °C, pH 6.5.
    Termofílico é mais rápido e elimina mais patógenos que o mesofílico.
    """

    temp_opt_c: float = 52.5
    ph_opt: float = 6.5
    caproate_yield_kg_per_kg_sugar: float = 0.13  # ordem do RBO (n-caproato)
    @staticmethod
    def growth_rate(temp_c: float, ph: float) -> float:
        """Fração do ótimo (0-1) em T/pH — gaussiana simples."""
        t = max(0.0, 1.0 - ((temp_c - 52.5) / 22.5) ** 2)
        p = max(0.0, 1.0 - ((ph - 6.5) / 1.5) ** 2)
        return round(min(1.0, t * p), 3)
    def produce(self, polysaccharide_kg: float, temp_c: float, ph: float) -> Dict:
        rate = self.growth_rate(temp_c, ph)
        caproate = polysaccharide_kg * self.caproate_yield_kg_per_kg_sugar * rate
        return {"caproate_kg": round(caproate, 4), "rate": rate,
                "optimal_conditions": rate > 0.9}
