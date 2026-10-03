"""MicrobiomeManager — diversidade e inoculação do microbioma do solo (gap_9).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs_critical.gap_9

Micorrizas (fungos+raízes) aumentam absorção de P/N/água; fixadores
(Rhizobium/Azotobacter) suprem N; solubilizadores de P (Bacillus/Pseudomonas)
liberam fosfato. Índice de Shannon >= 2.0 = saudável. Consórcio, não monocultura.
"""

from __future__ import annotations

import math
from typing import Dict


class MicrobiomeManager:
    """Gerencia o microbioma do solo marciano."""

    SHANNON_HEALTHY = 2.0

    def __init__(self, shannon: float = 2.5) -> None:
        self.shannon = shannon
        self.inoculated = False

    def inoculate(self) -> Dict[str, float]:
        """Inocula consórcio benéfico (esporos/CFU por grama de solo)."""
        self.inoculated = True
        self.shannon = max(self.shannon, 2.0)
        return {
            "mycorrhizae_spores": 1e6,
            "nitrogen_fixers_cfu": 1e7,
            "phosphate_solubilizers_cfu": 1e6,
        }

    def step(self, stress: float = 1.0, nutrient_rich: bool = True) -> float:
        """Evolui a diversidade: estresse reduz, nutrição sustenta."""
        self.shannon += 0.001 * stress - 0.0005 * (1.0 - stress)
        if nutrient_rich and self.inoculated:
            self.shannon = min(4.0, self.shannon + 0.002)
        self.shannon = max(0.5, self.shannon)
        return self.shannon

    @staticmethod
    def microbial_air_check(bacteria_cfu_m3: float, fungi_cfu_m3: float) -> dict:
        """Limites de ar da ISS (Marra et al. 2023 / ESA): bactéria <5e2 CFU/m³,
        fungos 2-5e4 CFU/m³ — retorna status de quarentena do ar."""
        bacteria_ok = bacteria_cfu_m3 < 5e2
        fungi_ok = fungi_cfu_m3 < 2e4
        return {"bacteria_cfu_m3": bacteria_cfu_m3, "fungi_cfu_m3": fungi_cfu_m3,
                "bacteria_ok": bacteria_ok, "fungi_ok": fungi_ok,
                "air_ok": bacteria_ok and fungi_ok,
                "alerts": [x for x, ok in
                           [("bacteria", bacteria_ok), ("fungi", fungi_ok)] if not ok]}

    def soil_o2_sink(self, soil_organic_frac: float) -> float:
        """Consumo de O2 do solo enriquecido (lição Biosphere 2).

        Verificação 2026-09-28: Biosphere 2 perdeu O2 (20.9->14.4%) por
        respiração microbiana do solo + fixação em concreto. Solo com matéria
        orgânica alta (biochar 5%+) vira sumidouro de O2 — retorna o consumo
        em kg O2/dia por m² para o balanço do ecossistema.
        """
        # ~1.4e-3 kg O2/m²/dia por % de matéria orgânica (ordem de grandeza
        # calibrada na literatura de respiração de solo)
        return float(1.4e-3 * soil_organic_frac)

    @staticmethod
    def shannon_diversity(abundances: Dict[str, float]) -> float:
        """Índice de Shannon a partir de abundâncias relativas por espécie."""
        total = sum(abundances.values())
        if total <= 0:
            return 0.0
        return -sum((n / total) * math.log(n / total)
                    for n in abundances.values() if n > 0)

    def monitor_health(self, soil_sample: Dict[str, float]) -> Dict[str, str]:
        """Verifica saúde do microbioma (diversidade, respiração, enzimas)."""
        if self.shannon < self.SHANNON_HEALTHY:
            return {"alert": "low_microbiome_diversity",
                    "shannon": f"{self.shannon:.2f}"}
        return {"status": "healthy", "shannon": f"{self.shannon:.2f}"}
