"""NitrogenCycle — fixação, nitrificação e monitoramento de desnitrificação (gap_8).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs_critical.gap_8

Marte tem só 2.7% N2 na atmosfera. Fixação por nitrogenase
(Rhizobium/Azotobacter/cianobactérias) -> NH4+; nitrificação
(Nitrosomonas NH4+->NO2-, Nitrobacter NO2-->NO3-) -> forma assimilável.
Desnitrificação (NO3-->N2) em anaerobiose = PERDA — monitorar (O2 < 5%).
"""

from __future__ import annotations

from typing import Dict


class NitrogenCycle:
    """Gerencia o ciclo do nitrogênio na estufa marciana."""

    FIXATION_RATE = 0.05   # kg N fixado / kg N2 / dia (baixo em Marte)
    NITRIFICATION_EFF = 0.90

    def __init__(self, nitrate_kg: float = 10.0, ammonium_kg: float = 1.0) -> None:
        self.nitrate_kg = nitrate_kg
        self.ammonium_kg = ammonium_kg
        self.n_fixed_total = 0.0
        self.denitrification_events = 0

    def fix_atmospheric_n2(self, n2_kg: float) -> float:
        """Fixa N2 atmosférico em NH4+ (nitrogenase)."""
        fixed = n2_kg * self.FIXATION_RATE
        self.ammonium_kg += fixed
        self.n_fixed_total += fixed
        return fixed

    def nitrify(self) -> float:
        """Converte NH4+ em NO3- (forma assimilável)."""
        converted = self.ammonium_kg * self.NITRIFICATION_EFF
        self.ammonium_kg -= converted
        self.nitrate_kg += converted
        return converted

    def step(self, n2_kg: float, o2_level: float) -> Dict[str, object]:
        """Ciclo de um dia. Retorna alerta se desnitrificação (perda)."""
        self.fix_atmospheric_n2(n2_kg)
        self.nitrify()
        alert: Dict[str, object] = {"alert": "none"}
        if o2_level < 0.05:  # anaerobiose -> desnitrificação
            loss = self.nitrate_kg * 0.1
            self.nitrate_kg -= loss
            self.denitrification_events += 1
            alert = {"alert": "denitrification_risk", "nitrate_loss_kg": loss}
        return alert
