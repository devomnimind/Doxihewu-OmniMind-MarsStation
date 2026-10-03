"""CultivarStabilityScore + EvolutionGate — gate evolutivo de culturas (d3).

MARS_SYSTEM_CONTRACT.yaml · operator_decisions.d3_gate_evolution

Decisão do operador (2026-09-28): transições de cultura são irreversíveis
(batata/trigo consomem solo não-reciclável) — só prossiga por GATE DE DADOS:
  - algae_to_potato: stability >= 0.90 por 55.7 sols, epsilon < 0.15,
    reservas energia >= 50%, água >= 60%, nutrientes >= 30%
  - potato_to_wheat: stability >= 0.95 por 111.4 sols, epsilon < 0.10,
    reservas energia >= 70%, água >= 80%, nutrientes >= 50%, solo >= 100 m³

Score ponderado: yield_consistency 0.30, contamination_resistance 0.25,
energy_efficiency 0.20, nutrient_uptake 0.15, stress_tolerance 0.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

STABILITY_WEIGHTS = {
    "yield_consistency": 0.30,
    "contamination_resistance": 0.25,
    "energy_efficiency": 0.20,
    "nutrient_uptake": 0.15,
    "stress_tolerance": 0.10,
}

GATE_THRESHOLDS = {
    "algae_to_potato": {
        "stability_score_min": 0.90,
        "duration_min_sols": 55.7,
        "epsilon_max": 0.15,
        "energy_reserve_min": 0.60,  # ação E5 (margem black swan)
        "water_reserve_min": 0.60,
        "nutrient_reserve_min": 0.30,
        "max_sectors_per_cycle": 2,
        "rollback_possible": False,
    },
    "potato_to_wheat": {
        "stability_score_min": 0.95,
        "duration_min_sols": 111.4,
        "epsilon_max": 0.10,
        "energy_reserve_min": 0.70,
        "water_reserve_min": 0.80,
        "nutrient_reserve_min": 0.50,
        "soil_volume_min_m3": 100.0,
        "max_sectors_per_cycle": 3,
        "rollback_possible": False,
    },
}


class CultivarStabilityScore:
    """Calcula o score de estabilidade [0,1] de uma cultivar para gate."""

    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        self.weights = dict(weights or STABILITY_WEIGHTS)

    def calculate(self, cultivar_data: Dict) -> Tuple[float, Dict[str, float]]:
        """Score ponderado a partir de dados históricos da cultivar."""
        yield_var = float(np.var(cultivar_data.get("yield_kg_m2_day", [0.0])))
        yield_score = 1.0 - min(1.0, yield_var / 0.10)

        contamination_loss = float(cultivar_data.get("contamination_loss_pct", 100.0))
        contamination_score = 1.0 - min(1.0, contamination_loss / 5.0)

        energy_eff = float(cultivar_data.get("energy_efficiency_pct", 0.0)) / 80.0
        energy_score = min(1.0, energy_eff)

        nutrient_eff = float(cultivar_data.get("nutrient_uptake_efficiency", 0.0))
        nutrient_score = min(1.0, nutrient_eff / 0.70)

        stress_recovery = float(cultivar_data.get("post_storm_recovery_days", 10.0))
        stress_score = max(0.0, 1.0 - stress_recovery / 10.0)

        scores = {
            "yield_consistency": yield_score,
            "contamination_resistance": contamination_score,
            "energy_efficiency": energy_score,
            "nutrient_uptake": nutrient_score,
            "stress_tolerance": stress_score,
        }
        total = sum(scores[k] * self.weights[k] for k in scores)
        return float(total), scores


@dataclass
class EvolutionGate:
    """Gate de dados para transição de cultura dominante (irreversível)."""

    stability: CultivarStabilityScore = field(default_factory=CultivarStabilityScore)
    # Radiação modulada (calibração E2-REF v3 — PDF operador 2026-09-28):
    # blindagem 0.0 (exposto) a 1.0 (total); a máquina modula a blindagem
    # para acelerar/desacelerar a mutagênese conforme a necessidade evolutiva.
    radiation_shielding: float = 0.0
    mu_bp: float = 1.5e-6       # wheat cosmic rays 1.79e-6 (PMC9131052) -> Spirulina
    genome_loci: int = 1000
    dose_ref_mSv_gen: float = 50.0  # calibração wheat

    def effective_dose(self, dose_mars_mSv_day: float = 0.67) -> float:
        """Dose efetiva após blindagem (regolito/água/compósito)."""
        return dose_mars_mSv_day * (1.0 - self.radiation_shielding)

    def mutation_rate(self, dose_effective_mSv_day: float, generation_days: float = 10.0) -> float:
        """μ_eff = μ_bp × L × (D×t_gen / D_ref) — E2-REF v3 (PDF operador)."""
        return self.mu_bp * self.genome_loci * (dose_effective_mSv_day * generation_days / self.dose_ref_mSv_gen)

    def check(self, transition: str, data: Dict) -> Dict:
        """Avalia o gate para uma transição. data carrega métricas reais."""
        if transition not in GATE_THRESHOLDS:
            raise ValueError(f"transição desconhecida: {transition}")
        thr = GATE_THRESHOLDS[transition]
        score, breakdown = self.stability.calculate(data.get("cultivar", {}))

        checks = {
            "stability_score": score >= thr["stability_score_min"],
            "duration_sols": data.get("duration_sols", 0) >= thr["duration_min_sols"],
            "epsilon": data.get("epsilon", 1.0) < thr["epsilon_max"],
            "energy_reserve": data.get("energy_reserve", 0.0) >= thr["energy_reserve_min"],
            "water_reserve": data.get("water_reserve", 0.0) >= thr["water_reserve_min"],
            "nutrient_reserve": data.get("nutrient_reserve", 0.0) >= thr["nutrient_reserve_min"],
        }
        if "soil_volume_min_m3" in thr:
            checks["soil_volume_m3"] = data.get("soil_volume_m3", 0.0) >= thr["soil_volume_min_m3"]

        passed = all(checks.values())
        return {
            "transition": transition,
            "score": round(score, 4),
            "score_breakdown": {k: round(v, 4) for k, v in breakdown.items()},
            "thresholds": thr,
            "checks": checks,
            "passed": passed,
            "irreversible": not thr["rollback_possible"],
            "max_sectors_per_cycle": thr["max_sectors_per_cycle"],
        }

    def food_gate(self, plant_protein_kg_day: float, mealworm_protein_kg_day: float,
                  n_people: int, min_fraction: float = 0.95) -> Dict:
        """Gate de comida/proteína — conglomerado Lunar Palace 1.

        LP1 fechou ~100% da comida com plantas + mealworms. Requisito:
        ~0.06 kg proteína/pessoa-dia; a fração de mealworm no total mede a
        dependência da cadeia animal (resíduo -> proteína).
        """
        total = plant_protein_kg_day + mealworm_protein_kg_day
        need = 0.06 * n_people
        fraction = total / need if need else 0.0
        return {"total_protein_kg_day": round(total, 4), "need_kg_day": round(need, 4),
                "mealworm_fraction": round(mealworm_protein_kg_day / max(total, 1e-9), 4),
                "fraction_of_need": round(fraction, 4),
                "passed": fraction >= min_fraction,
                "min_fraction": min_fraction}
