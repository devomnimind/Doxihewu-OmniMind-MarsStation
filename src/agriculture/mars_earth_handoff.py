"""MarsEarthHandoff — canal soberano Terra<->Marte (gap_4, decisão d2).

MARS_SYSTEM_CONTRACT.yaml · operator_decisions.d2_veto_classes

Canal com latência 3-22min (ida e volta), janelas de conjunção solar (~2
semanas sem canal), reordenação por sol (fora de ordem permitido).
Três níveis de decisão (decisão do operador 2026-09-28):
  - Nível 1 autonomy_total: executa SEMPRE (latência 3-22min não pode
    bloquear rotina: fotoperíodo, nutrientes, pH/CO2, quarentena local...)
  - Nível 2 veto_consultative: Terra opina, a estufa decide
    (expansões, mutação S09, perturbação S11)
  - Nível 3 veto_mandatory: Terra decide — executa só após resposta
    explícita (quarentena global, cultivar dominante, expansão estrutural,
    abortar missão, hibernação permanente)
Analogia OmniMind: basal -> autonomia_total; canonical -> consultative;
rust -> mandatory. Idempotente (handoff_id).
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

AUTONOMY_TOTAL = {
    "photoperiod_adjustment", "nutrient_balance", "ph_co2_regulation",
    "sector_quarantine_local", "routine_cultivation",
    "hysteresis_threshold_adjustment",
}
VETO_CONSULTATIVE = {
    "greenhouse_expansion", "cultivar_rotation_same_class",
    "mutation_experiments_S09", "controlled_perturbation_S11",
}
VETO_MANDATORY = {
    "quarentena_release_global", "dominant_cultivar_change",
    "structural_expansion", "mission_abort", "permanent_hibernation",
}
VETO_CLASSES = AUTONOMY_TOTAL | VETO_CONSULTATIVE | VETO_MANDATORY


def veto_level(msg_class: str) -> int:
    """Nível de veto (1 = autonomia total; 2 = consultivo; 3 = obrigatório)."""
    if msg_class in VETO_MANDATORY:
        return 3
    if msg_class in VETO_CONSULTATIVE:
        return 2
    return 1


@dataclass
class EarthMessage:
    """Mensagem assinada Terra<->Marte."""

    msg_id: str
    msg_class: str
    sol: int
    payload: Dict[str, Any]
    latency_min: float = 0.0
    sent_utc: float = field(default_factory=time.time)
    veto: bool = False
    reason: str = ""


class MarsEarthHandoff:
    """Canal soberano Terra<->Marte com latência e veto em 3 níveis (d2)."""

    def __init__(self, latency_min: tuple = (3, 22),
                 veto_classes: set = VETO_CLASSES, seed: int = 0) -> None:
        self.latency_min = latency_min
        self.veto_classes = set(veto_classes)
        self.rng = random.Random(seed)
        self.queue: List[EarthMessage] = []
        self.executed: List[Dict[str, Any]] = []

    @staticmethod
    def _make_id(msg_class: str, sol: int) -> str:
        return hashlib.sha256(f"{msg_class}:{sol}".encode()).hexdigest()[:12]

    def send_to_earth(self, decision: Dict[str, Any]) -> EarthMessage:
        """Envia decisão para a Terra (store-and-forward)."""
        msg = EarthMessage(
            msg_id=self._make_id(decision.get("class", "?"), decision.get("sol", 0)),
            msg_class=decision.get("class", "?"),
            sol=decision.get("sol", 0),
            payload=decision,
            latency_min=round(self.rng.uniform(*self.latency_min), 1),
        )
        self.queue.append(msg)
        return msg

    def receive_from_earth(self, now: float | None = None) -> Optional[EarthMessage]:
        """Recebe resposta após latência. Reordena por sol."""
        now = now if now is not None else time.time()
        due = [m for m in self.queue if now - m.sent_utc >= m.latency_min * 60]
        due.sort(key=lambda m: m.sol)  # reordenação por sol (fora de ordem ok)
        if due:
            m = due[0]
            self.queue.remove(m)
            return m
        return None

    def execute_with_veto(self, decision: Dict[str, Any],
                          earth_response: Optional[EarthMessage] = None) -> Dict[str, Any]:
        """Executa decisão pelos 3 níveis da política d2:
        1 (autonomia total) executa sempre; 2 (consultivo) executa com
        resposta, senão pending_earth; 3 (obrigatório) exige resposta
        explícita não-veto da Terra."""
        d_class = decision.get("class", "?")
        level = veto_level(d_class)
        if level == 1:
            self.executed.append({"action": "executed", "decision": decision,
                                  "level": 1, "autonomy": "total"})
            return {"action": "executed", "decision": decision, "level": 1}
        # níveis 2 e 3: envolvem a Terra
        if earth_response is None:
            self.send_to_earth(decision)  # aguarda resposta (latência)
            return {"action": "pending_earth", "decision": decision, "level": level}
        if earth_response.veto:
            self.executed.append({"action": "vetoed", "reason": earth_response.reason,
                                  "level": level})
            return {"action": "vetoed", "reason": earth_response.reason, "level": level}
        self.executed.append({"action": "executed", "decision": decision, "level": level})
        return {"action": "executed", "decision": decision, "level": level}
