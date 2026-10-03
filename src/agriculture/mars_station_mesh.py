"""Mars Station Mesh — port dos padrões OmniMind para o corpo da estação.

Três camadas portadas do kernel OmniMind (a glia Go, o VBKF do
soliton_raft_detector e o campo afetivo que a glia lê), adaptadas às
superfícies do StationBody:

1. StationVBKF — Variational Bayesian Kalman Filter
   (port de src/security/soliton_raft_detector_service.py::VBKFEstimator)

   Estimativa robusta do estado do corpo sob observação ruidosa:
   body_integrity entra como z; o filtro adapta R online (posterior
   inverse-gamma), rejeita outliers (resíduo normalizado > 2.5), e usa
   um modulador de ruído de processo (o papel que D12 tem no original —
   aqui o estresse de regime do corpo) para alargar/estreitar Q.

   O que ganha: S_meta e ChainCapacity leem body_integrity cru — uma
   rajada de poeira derruba a observação por um sol e pareceria crise.
   O VBKF entrega o ESTADO por baixo da observação — a malha decide
   sobre o estado filtrado, não sobre o pixel.

2. StationAffect — o campo afetivo basal
   (homólogo do omnimind-affective-pulse que a glia Go lê)

   Afeto não é diagnóstico — é o tônus lento que colore a decisão:
   canais EMA sobre sinais do corpo -> dominante + tensão composta.
   Canais (análogos, não equivalência):
     distress  — dano chegando acima do regime (wear_rate alto sustentado)
     relief    — reparo eficaz (wear caindo)
     fatigue   — carga de reparo sustentada (repair_load_h alto)
     vigil     — monitoramento elevado (incidentes + cascade ativos)
   dominante = argmax(canais); tensão = Σ canais normalizada.

3. StationGlia — integrador glial lento
   (port do padrão src/go/omnimind-glia/main.go)

   τ_glial >> τ_neuronal: janela de N sols conta pulsos por sinal
   (wear_rate_* acima do limiar = stress pulse; incident/cascade = pain
   pulse). Estados rest|observe|suppress|quarantine com histerese
   pending_state (o mesmo anti-chattering que S_meta já usa).
   Lê o StationAffect (affect_pulses, dominant_afex, affect_tension).

   Veredictos da glia são RECOMENDAÇÕES para a política de reparo:
     suppress   -> não perseguir pico transitório (economia de labor)
     quarantine -> dano sustentado -> surto de reparo dirigido à camada

   A glia não age: ela INTEGRA e sinaliza — a política (StationBody.
   repair_fraction) decide. Mesmo contrato da glia OmniMind.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============ 1) StationVBKF — estimador robusto (port direto) ============

class StationVBKF:
    """VBKF sobre a integridade do corpo — port fiel do VBKFEstimator
    (mesmas equações: predição, resíduo normalizado, posterior
    inverse-gamma de R, modulação de Q pelo meta-score)."""

    def __init__(self, x0: float = 0.95, P0: float = 0.01,
                 Q0: float = 0.0006, nu0: float = 5.0,
                 tau0: float = 0.005) -> None:
        self.x = x0            # estado estimado (integridade robusta)
        self.P = P0            # covariância do estado
        self.Q = Q0            # ruído de processo
        self.nu = nu0          # inverse-gamma shape
        self.tau = tau0        # inverse-gamma scale
        self.last_nr = 0.0     # resíduo normalizado do último update
        self.outlier_rejected = False
        self.n_rejected = 0

    def predict(self) -> None:
        self.P += self.Q

    def update(self, z: float, stress_score: float = 0.0) -> float:
        """z = observação (body_integrity); stress_score modula Q —
        o papel do D12 no original: sob estresse de regime, o processo
        é menos previsível (Q sobe -> filtro confia mais na observação)."""
        self.predict()
        y = z - self.x
        R_est = self.tau / self.nu
        S = self.P + R_est
        self.last_nr = abs(y) / max(math.sqrt(S), 1e-10)
        self.outlier_rejected = self.last_nr > 2.5
        if self.outlier_rejected:
            self.n_rejected += 1

        self.nu = 0.98 * self.nu + 1.0
        self.tau = 0.98 * self.tau + y * y

        if stress_score > 0.5:
            self.Q = min(0.006, self.Q * 1.3)
        else:
            self.Q = max(0.0004, self.Q * 0.97)

        R_post = self.tau / self.nu
        S_post = self.P + R_post
        K = self.P / S_post
        # quando outlier é rejeitado o passo de atualização é atenuado
        # (a observação pode ser o ruído, não o estado)
        gain = K * (0.25 if self.outlier_rejected else 1.0)
        self.x = min(1.0, max(0.0, self.x + gain * y))
        self.P = (1 - K) * self.P
        return self.x

    def predict_only(self) -> float:
        self.predict()
        self.last_nr = 0.0
        self.outlier_rejected = False
        return self.x


# ============ 2) StationAffect — campo afetivo basal ============

AFFECT_CHANNELS = ("distress", "relief", "fatigue", "vigil")


@dataclass
class StationAffect:
    """O tônus lento que colore a decisão — EMA por canal.

    Cada canal integra um sinal do corpo por sol; o dominante é o
    canal de maior nível; a tensão é a soma normalizada (0..1).
    """

    ema: float = 0.94                    # ~16 sols de memória efetiva
    channels: Dict[str, float] = field(
        default_factory=lambda: {c: 0.0 for c in AFFECT_CHANNELS})

    def step(self, body_rec: Dict[str, float]) -> Dict[str, object]:
        """Alimenta os canais com o registro do sol do corpo."""
        # sinais de entrada do sol
        wear_rates = [v for k, v in body_rec.items()
                      if k.startswith("wear_rate_")]
        dmg_in = sum(wear_rates) * 1e4 if wear_rates else 0.0
        dmg_in = min(1.0, dmg_in)
        repair_h = body_rec.get("repair_load_h", 0.0)
        relief_in = min(1.0, repair_h / 80.0)      # carga -> alívio do dia
        fatigue_in = min(1.0, repair_h / 60.0)
        vigil_in = min(1.0, body_rec.get("incident", 0)
                       + body_rec.get("cascade_load", 0.0) * 0.5)
        # um incidente é um pulso de vigília; cascata soma
        inputs = {"distress": dmg_in, "relief": relief_in,
                  "fatigue": fatigue_in, "vigil": vigil_in}
        for c in AFFECT_CHANNELS:
            self.channels[c] = (self.ema * self.channels[c]
                                + (1 - self.ema) * inputs[c])
        dominant = max(AFFECT_CHANNELS, key=lambda c: self.channels[c])
        tension = min(1.0, sum(self.channels[c] for c in AFFECT_CHANNELS)
                      / len(AFFECT_CHANNELS))
        return {"afex_dominant": dominant,
                "afex_tension": round(tension, 4),
                **{f"afex_{c}": round(self.channels[c], 4)
                   for c in AFFECT_CHANNELS}}


# ============ 3) StationGlia — integrador lento com histerese ============

GLIA_STATES = ("rest", "observe", "suppress", "quarantine")


@dataclass
class StationGlia:
    """Janela de `window_sols` conta pulsos por classe; estado só muda
    após `hysteresis_n` janelas consecutivas apontando o mesmo alvo
    (pending_state — o padrão que o main.go fix de 2026-09-26 gravou e
    a S_meta já usa)."""

    window_sols: int = 7
    stress_threshold: int = 6         # stress pulses na janela -> observe/suppress
    pain_threshold: int = 2           # pain pulses na janela -> quarantine
    hysteresis_n: int = 2
    pulse_gain: float = 2.5           # wear_rate > gain x EMA = stress pulse
    pulse_floor_abs: float = 1e-4     # piso absoluto mínimo do pulso

    state: str = "rest"
    pending: Optional[str] = None
    pending_count: int = 0
    _buf: List[Dict[str, int]] = field(default_factory=list)
    _rate_ema: Dict[str, float] = field(default_factory=dict)
    cycle: int = 0
    # leitura do campo afetivo (como a glia Go lê affect_pulses)
    last_afex: Dict[str, object] = field(default_factory=dict)

    def _pulses(self, body_rec: Dict[str, float]) -> Dict[str, int]:
        """Stress pulse = camada com taxa acima do PRÓPRIO regime —
        wear_rate crônica não é pulso (é o desgaste de ser estação),
        a excursão é. Mesma disciplina do SurpriseDetector do motor
        aleatório: limiar auto-calibrado."""
        stress = 0
        for k, v in body_rec.items():
            if not k.startswith("wear_rate_"):
                continue
            ema = self._rate_ema.get(k)
            if ema is None:
                self._rate_ema[k] = v
                continue
            if v > self.pulse_floor_abs and v > self.pulse_gain * ema:
                stress += 1
            self._rate_ema[k] = 0.9 * ema + 0.1 * v
        pain = body_rec.get("incident", 0) + int(
            body_rec.get("cascade_load", 0.0) > 1.0)
        return {"stress": stress, "pain": pain}

    def _target(self, stress: int, pain: int) -> str:
        if pain >= self.pain_threshold:
            return "quarantine"
        if stress >= self.stress_threshold:
            # afeto decide entre observar e suprimir: vigilância alta +
            # distress alto -> quarantine escala; distress baixo -> o
            # pico é transitório, suprime (não perseguir ruído)
            af = self.last_afex
            if af.get("afex_dominant") == "vigil" and \
                    af.get("afex_tension", 0) > 0.4:
                return "quarantine"
            return "suppress"
        if stress > 0 or pain > 0:
            return "observe"
        return "rest"

    def step(self, body_rec: Dict[str, float],
             afex: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        self.cycle += 1
        if afex:
            self.last_afex = afex
        self._buf.append(self._pulses(body_rec))
        if len(self._buf) > self.window_sols:
            self._buf.pop(0)

        stress = sum(b["stress"] for b in self._buf)
        pain = sum(b["pain"] for b in self._buf)
        target = self._target(stress, pain)

        # histerese pending_state: estado só transita após N janelas
        # consecutivas apontando o mesmo alvo
        if target != self.state:
            if target == self.pending:
                self.pending_count += 1
            else:
                self.pending, self.pending_count = target, 1
            if self.pending_count >= self.hysteresis_n:
                self.state = target
                self.pending, self.pending_count = None, 0
        else:
            self.pending, self.pending_count = None, 0

        return {"glia_state": self.state,
                "glia_pending": self.pending or "",
                "glia_cycle": self.cycle,
                "glia_stress_pulses": stress,
                "glia_pain_pulses": pain,
                "glia_window_sols": len(self._buf)}


# ============ Composição — a malha do corpo ============

@dataclass
class StationMesh:
    """glia + afeto + VBKF sobre o registro do corpo — uma chamada por sol."""

    vbkf: StationVBKF = field(default_factory=StationVBKF)
    afex: StationAffect = field(default_factory=StationAffect)
    glia: StationGlia = field(default_factory=StationGlia)
    vbkf_stress: float = 0.0    # EMA do resíduo — estresse de regime p/ Q

    def step(self, body_rec: Dict[str, float]) -> Dict[str, object]:
        z = body_rec.get("body_integrity")
        if z is None:
            est = self.vbkf.predict_only()
        else:
            est = self.vbkf.update(z, self.vbkf_stress)
        self.vbkf_stress = 0.9 * self.vbkf_stress + 0.1 * min(
            1.0, self.vbkf.last_nr / 3.0)
        afex = self.afex.step(body_rec)
        glia = self.glia.step(body_rec, afex)
        out = {"mesh_vbkf_est": round(est, 5),
               "mesh_vbkf_nr": round(self.vbkf.last_nr, 3),
               "mesh_vbkf_rej": int(self.vbkf.outlier_rejected),
               "mesh_vbkf_n_rej": self.vbkf.n_rejected}
        out.update(afex)
        out.update(glia)
        return out
