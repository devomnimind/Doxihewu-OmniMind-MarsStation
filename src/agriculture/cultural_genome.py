"""CulturalGenome — identidade cultural da estufa (gap_5).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs.gap_5_cultural_identity_genome

A estufa tem cultura: narrativa, valores e memória de traumas/conquistas.
Cada decisão é tomada por valores; eventos gravam lições que atualizam os
valores (histerese de valores — espelha hysteresis_operator).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


class CulturalGenome:
    """Identidade cultural da estufa (narrativa, valores, memória)."""

    DEFAULT_VALUES = {
        "survival": 1.0,
        "biomass_production": 0.9,
        "resource_efficiency": 0.7,
        "experimentation": 0.5,
    }

    def __init__(self, station_name: str = "Chryse Planitia Alpha") -> None:
        self.station_name = station_name
        self.narrative = f"Estufa autônoma em Marte — {station_name}"
        self.values: Dict[str, float] = dict(self.DEFAULT_VALUES)
        self.memory: List[Dict[str, Any]] = []
        # Higiene aprendida (achado de modelagem d2/d3): a quarentena local
        # (N1 autonomy) reduz a contaminação com a operação estável.
        self.hygiene = 0.0
        self.hygiene_rate = 0.0005  # por sol

    def step_hygiene(self, sol: int, stress: float = 1.0) -> float:
        """Evolui a higiene com a operação; estresse (poeira) atrasa."""
        self.hygiene = min(2.5, self.hygiene + self.hygiene_rate * (1.0 - 0.5 * (1.0 - stress)))
        return self.hygiene

    def contamination_pct(self, nominal: float = 2.5) -> float:
        """Contaminação real = nominal * exp(-higiene) — piso 0.2%."""
        return max(0.2, nominal * math.exp(-self.hygiene))

    def log_event(self, event_type: str, severity: float, lesson: str | None = None) -> None:
        """Registra evento na memória cultural; lição atualiza valores."""
        self.memory.append({
            "type": event_type, "severity": severity,
            "sequence": len(self.memory), "lesson": lesson,
        })
        if lesson == "survival":
            self.values["survival"] = min(1.0, self.values["survival"] + 0.05)
        elif lesson == "efficiency":
            self.values["resource_efficiency"] = min(1.0, self.values["resource_efficiency"] + 0.05)
        elif lesson == "experiment":
            self.values["experimentation"] = min(1.0, self.values["experimentation"] + 0.1)

    def get_decision(self, options: List[Dict[str, Any]]) -> str:
        """Decisão baseada em valores: score = Σ valor × impacto."""
        best = None
        best_score = float("-inf")
        for opt in options:
            impact = opt.get("impact_on_values", {})
            score = sum(self.values.get(k, 0.0) * v for k, v in impact.items())
            if score > best_score:
                best_score = score
                best = opt["name"]
        return best or options[0]["name"]

    def narrative_snapshot(self) -> str:
        return (f"{self.narrative} — {len(self.memory)} eventos registrados; "
                f"valores: {self.values}")
