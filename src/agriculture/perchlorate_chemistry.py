"""PerchlorateChemistry — toxicidade e remediação de percloratos (gap_3).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs.gap_3_perchlorate_chemistry

ClO4- é tóxico (inibidor de tireoide) e oxidante violento. Gate L4 obrigatório
antes de usar regolito in-situ: só cultivar após is_safe(ppm < threshold).
Redução: biológica (Dechloromonas/Azospira, 90%/ciclo) ou eletroquímica
(catodo Ti/Pt 2-3V, 95%/ciclo).
"""

from __future__ import annotations

from typing import Dict


class PerchlorateChemistry:
    """Modelo de toxicidade de percloratos no regolito."""

    def __init__(self, threshold_ppm: float = 1000.0,
                 reduction_rate: float = 0.9, method: str = "biological") -> None:
        if method not in ("biological", "electrochemical"):
            raise ValueError(f"método desconhecido: {method}")
        self.threshold_ppm = threshold_ppm
        self.reduction_rate = reduction_rate if method == "biological" else 0.95
        self.method = method
        self.remediated_kg = 0.0

    def is_safe(self, perchlorate_ppm: float) -> bool:
        """True se o solo é seguro para agricultura (gate L4)."""
        return perchlorate_ppm < self.threshold_ppm

    def remediate(self, soil_sample: Dict[str, float]) -> Dict[str, float]:
        """Simula lavagem/redução: ClO4- multiplicado por (1 - rate)."""
        sample = dict(soil_sample)
        ppm = sample.get("perchlorate_ppm", 0.0)
        sample["perchlorate_ppm"] = ppm * (1.0 - self.reduction_rate)
        self.remediated_kg += sample.get("soil_kg", 0.0)
        return sample

    def cycles_to_safe(self, perchlorate_ppm: float) -> int:
        """Nº de ciclos de remediação até is_safe."""
        n = 0
        ppm = perchlorate_ppm
        while ppm >= self.threshold_ppm and n < 50:
            ppm *= (1.0 - self.reduction_rate)
            n += 1
        return n

    def leach_water_needed(self, perchlorate_ppm: float, soil_kg: float) -> float:
        """Litros de água estimados (proxy: 10 L/kg solo por ciclo)."""
        cycles = self.cycles_to_safe(perchlorate_ppm)
        return soil_kg * 10.0 * cycles
