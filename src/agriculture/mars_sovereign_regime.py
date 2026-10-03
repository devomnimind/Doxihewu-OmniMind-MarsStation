"""Mars Sovereign Regime — S_meta_station: a estação vive em regimes
metaestáveis, não em thresholds.

Portado da teoria unificada de metaestabilidade (zenodo v2) para o
substrato marciano. Na Terra, S_meta = w_P·P + w_T·T + w_R·R + w_O·O + w_K·K
sobre observáveis de host; aqui os cinco eixos são:

  P  proximity_to_threshold — pior margem normalizada entre os limites
     operacionais declarados (poeira/vento/O₂/água/integridade)
  T  persistence_outside_nominal — decai conforme sols fora do nominal
  R  recovery_slope — inclinação recente da integridade do corpo
  O  observability_coverage — fração dos canais ambientes reportando
  K  reconstruction_error — proxy: saúde do compute_core (quem estima
     o estado é o próprio substrato que erra sob radiação)

Regimes (tabela Lyapunov, mars_station_charter.yaml §metastability_lane):
  stable   0.8–1.0  → nominal_ecopoiesis (modo de oportunidade decide)
  decaying 0.6–0.8  → heightened_monitoring (modo oportunidade + flag)
  critical 0.4–0.6  → dust_storm_defense (ameaça env) | containment_repair
  collapse 0.0–0.4  → survival_lockdown + homeostatic_refusal

Anti-chattering (padrão glia pending_state, main.go fix 2026-09-26):
transição de regime só confirma após `pending_windows` janelas
consecutivas no mesmo candidato. Defesa de poeira tem banda assimétrica:
entra flux>2.2|wind>14, só sai flux<1.6 e wind<10 — nunca oscila na borda.

homeostatic_refusal (A3): S_meta < 0.4 → a estação recusa carga externa
(missões Terra enfileiram). Preserva o corpo antes de obedecer.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class SMetaStation:
    """Estimador de regime metaestável. Um por estação; passa um `step()`
    por sol com os observáveis disponíveis ANTES da decisão de modo."""

    # pesos (documentados; calibráveis)
    w_P: float = 0.30
    w_T: float = 0.20
    w_R: float = 0.20
    w_O: float = 0.15
    w_K: float = 0.15

    # limites operacionais (as mesmas constantes do if/else original)
    dust_enter: float = 2.2
    dust_exit: float = 1.6
    wind_enter: float = 14.0
    wind_exit: float = 10.0
    o2_floor_kg: float = 100.0        # abaixo disso, oxigênio é limiar
    water_floor_l: float = 500.0
    integrity_floor: float = 0.5

    # histerese de regime
    pending_windows: int = 2
    refusal_threshold: float = 0.4

    # janela de inclinação de recuperação
    slope_window: int = 30

    # --- estado ---
    regime: str = "stable"
    defense_active: bool = False
    homeostatic_refusal: bool = False
    s_meta: float = 1.0
    _pending: tuple = field(default_factory=lambda: (None, 0))
    _off_nominal_sols: int = 0
    _integrity_hist: Deque = field(default_factory=lambda: deque(maxlen=30))

    # ------------------------------------------------------------------
    def _proximity(self, obs: Dict[str, float]) -> float:
        """Pior margem normalizada: 1.0 = longe de todo limiar, 0 = no limiar."""
        margins = []
        margins.append(1.0 - min(1.0, obs["dust_flux"] / self.dust_enter))
        margins.append(1.0 - min(1.0, obs["wind_ms"] / self.wind_enter))
        margins.append(min(1.0, obs["o2_kg"] / (5.0 * self.o2_floor_kg)))
        margins.append(min(1.0, obs["water_l"] / (5.0 * self.water_floor_l)))
        margins.append(min(1.0, obs["body_integrity"]
                             / (2.0 * self.integrity_floor)))
        return min(margins)

    def _regime_of(self, s: float) -> str:
        if s >= 0.8: return "stable"
        if s >= 0.6: return "decaying"
        if s >= self.refusal_threshold: return "critical"
        return "collapse"

    def step(self, obs: Dict[str, float]) -> Dict:
        """obs: dust_flux, wind_ms, o2_kg, water_l, body_integrity,
        compute_wear, env_coverage (0..1). Retorna regime + override de modo."""
        # --- eixos ---
        P = self._proximity(obs)
        off_now = (obs["dust_flux"] > self.dust_enter
                   or obs["wind_ms"] > self.wind_enter
                   or obs["body_integrity"] < self.integrity_floor
                   or obs["o2_kg"] < self.o2_floor_kg
                   or obs["water_l"] < self.water_floor_l)
        self._off_nominal_sols = (self._off_nominal_sols + 1 if off_now
                                  else 0)
        T = 1.0 / (1.0 + self._off_nominal_sols / 10.0)

        self._integrity_hist.append(obs["body_integrity"])
        if len(self._integrity_hist) >= 5:
            h = list(self._integrity_hist)
            slope = (h[-1] - h[0]) / len(h)
            R = max(0.0, min(1.0, 0.5 + slope * 50.0))   # ±0.01/sol → satura
        else:
            R = 0.5
        O = max(0.0, min(1.0, obs.get("env_coverage", 1.0)))
        K = max(0.0, 1.0 - obs.get("compute_wear", 0.0))

        self.s_meta = (self.w_P * P + self.w_T * T + self.w_R * R
                       + self.w_O * O + self.w_K * K)
        raw = self._regime_of(self.s_meta)

        # --- histerese de regime (2 janelas no mesmo candidato) ---
        cand, count = self._pending
        if raw == self.regime:
            self._pending = (None, 0)
        elif raw == cand:
            count += 1
            self._pending = (cand, count)
            if count >= self.pending_windows:
                self.regime = raw
                self._pending = (None, 0)
        else:
            self._pending = (raw, 1)

        # --- defesa de poeira: latch com banda assimétrica ---
        threat = (obs["dust_flux"] > self.dust_enter
                  or obs["wind_ms"] > self.wind_enter)
        if self.defense_active:
            if (obs["dust_flux"] < self.dust_exit
                    and obs["wind_ms"] < self.wind_exit):
                self.defense_active = False
        elif threat or (self.regime in ("critical", "collapse") and threat):
            self.defense_active = True

        self.homeostatic_refusal = self.s_meta < self.refusal_threshold

        # --- regime → modo ---
        if self.regime == "collapse":
            mode = "survival_lockdown"
        elif self.defense_active:
            mode = "dust_storm_defense"
        elif self.regime == "critical":
            mode = "containment_repair"
        else:
            mode = None     # stable/decaying → quem decide é a oportunidade

        return {
            "s_meta": round(self.s_meta, 4),
            "regime": self.regime,
            "pending": self._pending[0],
            "components": {"P": round(P, 4), "T": round(T, 4),
                           "R": round(R, 4), "O": round(O, 4),
                           "K": round(K, 4)},
            "off_nominal_sols": self._off_nominal_sols,
            "defense_active": self.defense_active,
            "homeostatic_refusal": self.homeostatic_refusal,
            "heightened_monitoring": self.regime == "decaying",
            "mode_override": mode,
        }
