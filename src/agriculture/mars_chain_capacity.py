"""Mars Chain Capacity — Camada 1 do plano A100: classificador por
capacidade de cadeia.

Onde a Camada 0 mede *quanto tempo* o regime S_meta dura (arrival vs
persistence), a Camada 1 pergunta *por quê*: quais cadeias a configuração
consegue manter rodando, a que taxa, e cruzando quais bifurcações.

  estoque é foto; cadeia é filme.   (livro §22.4)

O classificador não lê `stocks_level` (estado) como veredito — lê
`production_sol` + `layer_wear_rates` (fluxos) e reconstrói as EDOs de
cadeia por sol:

  dO2/dt = P_foto + P_clo4 + P_refinaria − C_tripulacao − C_vazamento(I)
  dW/dt  = F_reciclagem + F_sabatier − C_estufa − C_vazamento(I)
  dI/dt  = R_reparo(labor × (1 − 0.8·wear_joints)) − W_desgaste(env)
  rho(t) = Σ_l f_l · cobertura_l / 11   (fechamento de reprodução funcional)
  repro_ratio = massa_fabricavel_modulos/sol ÷ massa_atrito/sol

A demanda (C_*) é parâmetro do mundo — o sim produz; a Camada 1 pergunta
se a cadeia aguenta a demanda daquele mundo. Estoques sombra (o2_shadow,
w_shadow) integram os fluxos líquidos: podem drenar onde o estoque real
só cresce — é aí que o regime aparece.

Regimes de capacidade (saída — livro §22.4):
  sterile_physical      nenhuma cadeia inicia / loop autocatalítico morto
  survival_only         cadeias rodam mas abaixo da bifurcação de
                        manutenção (dI < 0 sustentado, ou sombra drena)
  metabolic_habitat     manutenção sustentada (dI ≥ 0, dO2 ≥ 0, dW ≥ 0
                        sobre τ) — a estação já é corpo metabólico
  evolutionary_habitat  + cruzou a bifurcação de reprodução funcional:
                        rho ≥ rho_crit e repro_ratio ≥ 1 sustentados

ExcecaoTau (§17.3.4): predicado solvente-agnóstico — a configuração
sustenta uma cadeia autocatalítica a taxa positiva por janela τ. Na
estação o loop é literal: frota repara corpo → corpo hospeda ISRU/fab →
fab produz juntas → juntas reparam frota. A cascata
robot_joints→repair_capacity que CASCADE declara mas o sim não fecha é
fechada aqui.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

CHAIN_REGIMES = ("sterile_physical", "survival_only",
                 "metabolic_habitat", "evolutionary_habitat")

# ---------- fabricabilidade por camada do corpo ----------
# (strict, functional): 0 = gap estrutural (não fabricável local),
# 0.5 = substituto funcional parcial, 1.0 = fabricável pela cadeia local.
# 'functional' implementa a tese E.17.11: reprodução funcional ≠ cópia —
# seals de geopolímero e solar+storage como substituto de fission contam.
# feed = estoque dominante que cobre a reposição; demand_kg = massa do
# módulo a repor (ordem de grandeza defensável).
LAYER_FABRICABILITY: Dict[str, Dict] = {
    # name:            strict  func   feed stock           demand_kg
    "regolith_shield": dict(s=1.0, f=1.0, feed="sintered_bricks_kg",  m=400_000.0),
    "hull_primary":    dict(s=1.0, f=1.0, feed="fe_metal_kg",         m=25_000.0),
    "seals_joints":    dict(s=0.0, f=0.5, feed="cement_geopolymer_kg", m=500.0),
    "optics_windows":  dict(s=0.5, f=0.5, feed="silica_kg",           m=1_000.0),
    "solar_arrays":    dict(s=0.5, f=0.5, feed="silicon_metal_kg",    m=8_000.0),
    "fission_units":   dict(s=0.0, f=0.5, feed="silicon_metal_kg",    m=6_000.0),
    "radiators":       dict(s=1.0, f=1.0, feed="fe_metal_kg",         m=4_000.0),
    "isru_plant":      dict(s=1.0, f=1.0, feed="fe_metal_kg",         m=15_000.0),
    "eclss_loop":      dict(s=0.5, f=0.5, feed="fe_metal_kg",         m=5_000.0),
    "compute_core":    dict(s=0.5, f=0.5, feed="silicon_metal_kg",    m=2_000.0),
    "robot_joints":    dict(s=1.0, f=1.0, feed="fe_metal_kg",         m=10_000.0),
}

# massa "capaz de módulo" produzida por sol — a fração da produção que pode
# virar peça de reposição (aço, silício, cimento, tijolos sinterizados).
FAB_STOCKS = ("fe_metal_total_kg", "silicon_metal_kg",
              "cement_total_kg", "sintered_bricks_kg")

# demanda de tripulação-equivalente (a estufa e a urina do sim já assumem
# ~10–15 habitantes-equivalentes implícitos)
O2_PER_PERSON_KG_SOL = 0.84
H2O_PER_PERSON_L_SOL = 3.0
GREENHOUSE_WATER_L_SOL = 16.0          # sempre
GREENHOUSE_WATER_L_SOL_LATE = 51.0     # após sol 1500 (16 + 35)
GREENHOUSE_CUTOVER_SOL = 1500
GH_TRANSPIRATION_RECYCLE = 0.70        # transpiração → condensado (ECLSS)


@dataclass
class ExcecaoTau:
    """Predicado solvente-agnóstico (§17.3.4): a configuração sustenta
    uma cadeia autocatalítica a taxa positiva por janela τ.

    Não pergunta *qual* substância flui — pergunta se o loop se sustenta.
    `push(rate)` alimenta a taxa líquida do loop no sol; `verdict` é True
    quando a fração da janela acima do piso ≥ fill_floor. A cadeia tolera
    mergulhos (tempestade, incidente) — como a histerese do S_meta, é a
    violação SUSTENTADA que mata a cadeia, não a excursão de um sol.
    """

    tau: int = 30
    rate_floor: float = 0.0
    fill_floor: float = 0.8
    _window: Deque = field(init=False)

    def __post_init__(self):
        self._window = deque(maxlen=self.tau)

    def push(self, rate: float) -> bool:
        self._window.append(rate)
        return self.verdict

    @property
    def verdict(self) -> bool:
        return (len(self._window) == self.tau
                and self.fill >= self.fill_floor)

    @property
    def fill(self) -> float:
        """Fração da janela τ sustentada acima do piso (0..1)."""
        if not self._window:
            return 0.0
        return (sum(1 for r in self._window if r >= self.rate_floor)
                / self.tau)


@dataclass
class BifurcationEvent:
    sol: int
    kind: str          # rho_closure | repro_ratio | dI_sign | stock_drain
    direction: str     # up | down
    value: float

    def as_dict(self) -> Dict:
        return {"sol": self.sol, "kind": self.kind,
                "direction": self.direction, "value": round(self.value, 5)}


@dataclass
class ChainCapacityClassifier:
    """Classificador Camada 1 — um por trajetória/mundo.

    `observe(step_summary, world)` é chamado uma vez por sol, depois de
    `sim.step(env)`. Extrai fluxos, integra os estoques sombra, detecta
    cruzamentos de bifurcação e emite o regime de capacidade com
    histerese (mesmo padrão pending_windows do S_meta).
    """

    # janelas e limiares
    tau_maintenance: int = 30      # janela de sustentação dI/dO2/dW
    tau_repro: int = 90            # reprodução pede sustentação longa
    rho_crit: float = 0.60         # fechamento funcional mínimo
    pending_windows: int = 3       # histerese de regime
    policy: str = "functional"     # 'strict' | 'functional' (E.17.11)

    # demanda do mundo (set via observe/world)
    crew_eq: float = 10.0
    leak_base: float = 0.003       # fração/sol de vazamento no limiar I=0

    # estado sombra
    o2_shadow: float = 500.0
    w_shadow: float = 5000.0
    _prev_integrity: Optional[float] = None
    _prev_rho: float = 0.0
    _prev_wears: Dict[str, float] = field(default_factory=dict)

    regime: str = "sterile_physical"
    _pending: tuple = field(default_factory=lambda: (None, 0))
    events: List[BifurcationEvent] = field(default_factory=list)

    # janelas de fluxo para diagnóstico de bifurcação
    _dI_hist: Deque = field(default_factory=lambda: deque(maxlen=30))
    _repro_hist: Deque = field(default_factory=lambda: deque(maxlen=90))

    # predicado autocatalítico (loop frota→corpo→fab→frota)
    excecao: ExcecaoTau = field(default_factory=ExcecaoTau)

    n_sols: int = 0
    counts: Dict[str, int] = field(
        default_factory=lambda: {r: 0 for r in CHAIN_REGIMES})

    # ------------------------------------------------------------------
    def _rho(self, stocks: Dict[str, float]) -> float:
        """Fechamento de reprodução funcional: fração de módulos críticos
        cuja cadeia local cobre a massa de reposição."""
        key = "f" if self.policy == "functional" else "s"
        acc = 0.0
        for name, spec in LAYER_FABRICABILITY.items():
            cov = min(1.0, stocks.get(spec["feed"], 0.0) / spec["m"])
            acc += spec[key] * cov
        return acc / len(LAYER_FABRICABILITY)

    # ------------------------------------------------------------------
    def observe(self, step: Dict, world: Optional[Dict] = None) -> Dict:
        """Um sol da Camada 1. step = saída de StationUnifiedSimulator.step().
        world = demanda do mundo: crew_eq (habitantes-eq), leak_base."""
        self.n_sols += 1
        sol = step["sol"]
        w = world or {}
        crew_eq = w.get("crew_eq", self.crew_eq)
        leak_base = w.get("leak_base", self.leak_base)

        prod = step["production_sol"]
        stocks = step["stocks_level"]
        wears = step.get("layer_wears", {})
        wear_rates = step.get("layer_wear_rates", {})
        integrity = step["body_integrity"]

        # ---------- dO2/dt ----------
        leak = leak_base * (1.0 - integrity) * 10.0    # corpo furado vaza
        d_o2 = (prod["o2_net_kg"]
                - crew_eq * O2_PER_PERSON_KG_SOL
                - leak * self.o2_shadow)
        self.o2_shadow = max(0.0, self.o2_shadow + d_o2)

        # ---------- dW/dt ----------
        # demanda efetiva da estufa: transpiração retorna via condensado
        # atmosférico (ECLSS padrão) — só a fração não-reciclada sai do loop
        gh_gross = (GREENHOUSE_WATER_L_SOL_LATE
                    if sol >= GREENHOUSE_CUTOVER_SOL
                    else GREENHOUSE_WATER_L_SOL)
        gh = gh_gross * (1.0 - GH_TRANSPIRATION_RECYCLE)
        d_w = (prod["water_recovered_l"]
               - gh
               - crew_eq * H2O_PER_PERSON_L_SOL
               - leak * self.w_shadow)
        self.w_shadow = max(0.0, self.w_shadow + d_w)

        # ---------- dI/dt (realizado) + decomposição ----------
        d_i = 0.0 if self._prev_integrity is None else (
            integrity - self._prev_integrity)
        self._prev_integrity = integrity

        # atrito em massa-equivalente: dano bruto × massa da camada
        attrition_kg = sum(
            wear_rates.get(f"wear_rate_{name}", 0.0) * spec["m"]
            for name, spec in LAYER_FABRICABILITY.items())
        # fabricação capaz-de-módulo por sol
        fab_kg = sum(prod.get(k, 0.0) for k in FAB_STOCKS)
        repro_ratio = (fab_kg / attrition_kg) if attrition_kg > 0 else 0.0

        # ---------- rho: fechamento de reprodução ----------
        rho = self._rho(stocks)
        self._repro_hist.append(repro_ratio)

        # ---------- loop autocatalítico (Exceção_τ) ----------
        # reparo efetivo = horas de reparo × (1 − 0.8·wear_joints) — a
        # cascata robot_joints→repair_capacity de CASCADE fechada aqui.
        joints_wear = wears.get("wear_robot_joints", 0.0)
        eff_repair_h = step.get("repair_load_h", 0.0) * (1.0 - 0.8 * joints_wear)
        # taxa do loop: capacidade de reparo efetiva menos atrito do corpo
        body_damage = sum(wear_rates.values()) / max(1, len(wear_rates))
        loop_rate = eff_repair_h * 1e-6 - body_damage
        excecao_now = self.excecao.push(loop_rate)

        # ---------- eventos de bifurcação ----------
        if self._prev_rho < self.rho_crit <= rho:
            self.events.append(BifurcationEvent(
                sol, "rho_closure", "up", rho))
        elif self._prev_rho >= self.rho_crit > rho:
            self.events.append(BifurcationEvent(
                sol, "rho_closure", "down", rho))
        self._prev_rho = rho
        if len(self._repro_hist) == self.tau_repro:
            r_mean = sum(self._repro_hist) / self.tau_repro
            if r_mean >= 1.0 and not getattr(self, "_ratio_flag", False):
                self._ratio_flag = True
                self.events.append(BifurcationEvent(
                    sol, "repro_ratio", "up", r_mean))
            elif r_mean < 1.0 and getattr(self, "_ratio_flag", False):
                self._ratio_flag = False
                self.events.append(BifurcationEvent(
                    sol, "repro_ratio", "down", r_mean))
        self._dI_hist.append(d_i)
        if (self.o2_shadow <= 0.0 or self.w_shadow <= 0.0) and not getattr(
                self, "_drain_flag", False):
            self._drain_flag = True
            self.events.append(BifurcationEvent(
                sol, "stock_drain", "down", min(self.o2_shadow, self.w_shadow)))
        elif self.o2_shadow > 0.0 and self.w_shadow > 0.0:
            self._drain_flag = False

        # ---------- regime por capacidade de cadeia ----------
        raw = self._classify(d_i, d_o2, d_w, rho)
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
        self.counts[self.regime] += 1

        return {
            "regime_cadeia": self.regime,
            "regime_cadeia_pending": self._pending[0],
            "d_o2": round(d_o2, 3), "d_w": round(d_w, 3),
            "d_i": round(d_i, 6),
            "o2_shadow": round(self.o2_shadow, 1),
            "w_shadow": round(self.w_shadow, 1),
            "rho_repro": round(rho, 4),
            "repro_ratio": round(repro_ratio, 3),
            "attrition_kg": round(attrition_kg, 4),
            "fab_kg": round(fab_kg, 3),
            "loop_rate": round(loop_rate, 8),
            "excecao_tau": excecao_now,
            "excecao_fill": round(self.excecao.fill, 3),
        }

    # ------------------------------------------------------------------
    def _classify(self, d_i: float, d_o2: float, d_w: float,
                  rho: float) -> str:
        """Fluxos → regime. Lê a janela, não o sol isolado:

        manutenção  = integridade não declina em deriva líquida sobre τ
                      (ΣdI ≥ −0.005 tolera ruído de reparo worst-first)
                      E estoques sombra vivos — buffer existir é o que
                      permite tolerar fluxos instantâneos negativos;
        estéril     = corpo morrendo sustentado (I < 0.45 ∧ ΣdI < 0) —
                      loop autocatalítico realmente morto. Um mundo com
                      cadeias rodando nunca é estéril, mesmo drenando;
        survival    = intermediário: cadeias vivas, buffers drenando ou
                      integridade declinando — sobrevive, não sustenta;
        evolutionary= manutenção E fechamento: rho ≥ rho_crit e
                      repro_ratio ≥ 1 sustentados τ_rep sols.
        """
        integrity_ok = (len(self._dI_hist) == self._dI_hist.maxlen
                        and sum(self._dI_hist) >= -0.005)
        stocks_alive = self.o2_shadow > 0.0 and self.w_shadow > 0.0
        maint_ok = integrity_ok and stocks_alive
        repro_ok = (len(self._repro_hist) == self.tau_repro
                    and rho >= self.rho_crit
                    and all(r >= 1.0 for r in self._repro_hist))
        if maint_ok and repro_ok:
            return "evolutionary_habitat"
        if maint_ok:
            return "metabolic_habitat"
        body_dying = (self._prev_integrity is not None
                      and self._prev_integrity < 0.45
                      and len(self._dI_hist) == self._dI_hist.maxlen
                      and sum(self._dI_hist) < 0)
        return "sterile_physical" if body_dying else "survival_only"


# ----------------------------------------------------------------------

def classify_snapshot(flows: Dict[str, float], rho: float,
                      policy: str = "functional") -> str:
    """Classificação instantânea de um vetor de fluxos (uso offline /
    malha de síntese — não substitui a histerese temporal do classificador)."""
    maint = (flows.get("d_i", -1) >= 0 and flows.get("d_o2", -1) >= 0
             and flows.get("d_w", -1) >= 0)
    repro = rho >= 0.60 and flows.get("repro_ratio", 0.0) >= 1.0
    if maint and repro:
        return "evolutionary_habitat"
    if maint:
        return "metabolic_habitat"
    if any(flows.get(k, 0.0) > 0.0 for k in ("d_i", "d_o2", "d_w")):
        return "survival_only"
    return "sterile_physical"
