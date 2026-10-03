"""Mars Station Body — hipótese material da arquitetura.

O que a reveste, quais seus elementos, e a CADEIA de degradação/reação —
espelhando o multi-lattice do OmniMind (desgaste via Arrhenius, histerese,
classificação neutrosófica T/I/F), só que o "chassi" aqui é a estação.

Hipótese do corpo (cadeia de elementos):
  envelope    — regolith_shield (berma compactada), hull_primary (inox 304L
                de casco salvado), seals_joints (polímero), optics_windows
  power       — solar_arrays, fission_units, radiators
  process     — isru_plant (Sabatier/electrolyse), eclss_loop (filtros/membranas)
  compute     — compute_core (TID + fadiga térmica de solda — o Arrhenius
                literal do chassi, como o multi-lattice da OmniMind)
  fleet       — robot_joints (abrasão por poeira)

Física por sol (6 mecanismos acoplados ao ambiente REAL):
  arrhenius      k = A·exp(-Ea/RT)  — envelhecimento químico do material
  thermal_cycle  ΔT² (Coffin-Manson simplificado) — fadiga do ciclo dia/noite
                 marciano (~90K de amplitude no solo)
  uv_dose        polímeros/óptica degradam com irradiância UV_B/ABC
  dust_abrasion  deposição/erosão ∝ vento × tempestade (REMS + latente)
  radiation      dose em eletrônicos e polímeros sob o shield
  perchlorate    corrosão eletroquímica do metal que toca regolito oxidante

Reparo: consome labor_net_h (LaborEconomy) + power; reduz wear mas deixa
histórico (a histerese da OmniMind — reparo não apaga memória de dano).
Cascata: hull → eclss load; solar/radiator → power; isru → propelente;
compute → tudo (o corpo que mede também degrada).

O daemon hospeda este corpo: step_sol() roda autônomo, checkpointado —
a estação existe como processo contínuo, não como tabela estática.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

R_GAS = 8.314e-3            # kJ/(mol·K)

try:
    from src.agriculture.mars_surface_organ import SurfaceOrgan
except ImportError:
    try:
        from mars_surface_organ import SurfaceOrgan
    except ImportError:                      # módulo ausente: órgão opcional
        SurfaceOrgan = None

try:
    from src.agriculture.mars_shielding_materials import (
        AirlockOrgan, ShieldStack)
except ImportError:
    try:
        from mars_shielding_materials import AirlockOrgan, ShieldStack
    except ImportError:
        AirlockOrgan = ShieldStack = None


# ============ Camada material — a "célula de lattice" da estação ============

@dataclass
class MaterialLayer:
    """Um componente físico do corpo — análogo à linha do M_Lattice_MultiVector.

    wear: 0 (novo) -> 1 (falha). A degradação integra as taxas por sol;
    o reparo reduz wear mas o anneal (memória de dano) nunca zera.
    """

    name: str
    kind: str                    # envelope | power | process | compute | fleet
    ea_kj_mol: float             # energia de ativação Arrhenius do mecanismo dominante
    a_preexp: float              # pré-exponencial (calibrado p/ vida útil plausível)
    wear: float = 0.0
    anneal: float = 0.0          # memória de dano irreparável (histerese)
    kappa: float = 1.0           # acoplamento com outras camadas na cascata
    uv_sensitivity: float = 0.0  # resposta à dose UV (polímeros altos, inox ~0)
    dust_sensitivity: float = 0.0
    rad_sensitivity: float = 0.0
    perchlorate_contact: bool = False

    def arrhenius(self, t_kelvin: float) -> float:
        """Taxa base de envelhecimento químico a T — a equação literal do
        desgaste que a OmniMind aplica ao silício."""
        if t_kelvin <= 0:
            return 0.0
        return self.a_preexp * math.exp(-self.ea_kj_mol / (R_GAS * t_kelvin))

    def degrade(self, env: Dict[str, float], latent: float) -> float:
        """Dano do sol: soma dos mecanismos ativos sob o ambiente do dia."""
        t = env.get("air_temp_k", 220.0)
        dt_ground = env.get("ground_temp_delta", 60.0)
        uv = env.get("uv_abc_w_m2", 0.03)
        dust = env.get("dust_flux", 1.0)
        rad = env.get("rad_msv_day", 0.7)

        dmg = self.arrhenius(t)
        dmg += 1e-9 * (dt_ground / 60.0) ** 2                 # ciclo térmico
        dmg += self.uv_sensitivity * uv * 1e-3
        dmg += self.dust_sensitivity * dust * 1e-4
        dmg += self.rad_sensitivity * rad * 1e-4

        # Arrasto dinâmico e abrasão por saltação de vento real (InSight TWINS / REMS)
        wind_ms = env.get("wind_speed_ms", 0.0)
        wind_gust = env.get("wind_gust_ms", wind_ms * 1.3)
        if wind_ms > 0:
            dmg += 1e-8 * (0.5 * 0.018 * (wind_ms ** 2))
            if self.dust_sensitivity > 0:
                dmg += self.dust_sensitivity * 2e-7 * dust * min(10.0, (wind_gust / 10.0) ** 3)

        if self.perchlorate_contact:
            dmg += 5e-7 * env.get("perchlorate_wt", 0.6)      # brite regolito
        # incidente: excursão latente grande = evento físico (micro-meteoro,
        # rajada, trinca) com probabilidade proporcional ao choque
        dmg += max(0.0, latent) * self.kappa * 2e-5
        return dmg

    def neutrosophic(self, sensor_noise: float = 0.05) -> Dict[str, float]:
        """T/I/F da camada — saúde / indeterminação instrumental / degradação."""
        f = min(1.0, self.wear)
        return {"T": round(1.0 - f, 4), "I": round(sensor_noise, 4),
                "F": round(f, 4)}


# ============ O corpo — camadas + cascata + reparo ============

def default_body() -> Dict[str, MaterialLayer]:
    """O inventário material da estação — hipótese de arquitetura.

    Calibração: vida nominal ~40-60 anos para o envelope sob reparo,
    5-15 anos para consumíveis (seals, filtros, solar coverglass)."""
    L = MaterialLayer
    return {
        # --- envelope: o que reveste ---
        "regolith_shield": L("regolith_shield", "envelope", 40.0, 3e3,
                             dust_sensitivity=0.8, perchlorate_contact=True),
        "hull_primary":    L("hull_primary", "envelope", 90.0, 8e6,
                             kappa=1.5, dust_sensitivity=0.2,
                             perchlorate_contact=True),
        "seals_joints":    L("seals_joints", "envelope", 55.0, 5e4,
                             kappa=1.2, uv_sensitivity=1.4,
                             dust_sensitivity=0.5),
        "optics_windows":  L("optics_windows", "envelope", 65.0, 2e5,
                             uv_sensitivity=0.9, dust_sensitivity=0.7),
        # --- power ---
        "solar_arrays":    L("solar_arrays", "power", 50.0, 4e4,
                             kappa=1.3, uv_sensitivity=0.8,
                             dust_sensitivity=2.2, rad_sensitivity=0.5),
        "fission_units":   L("fission_units", "power", 110.0, 1e8, kappa=0.8,
                             rad_sensitivity=0.2),
        "radiators":       L("radiators", "power", 45.0, 2e3,
                             dust_sensitivity=1.5),
        # --- process ---
        "isru_plant":      L("isru_plant", "process", 70.0, 1e6, kappa=1.4,
                             dust_sensitivity=1.0, perchlorate_contact=True),
        "eclss_loop":      L("eclss_loop", "process", 48.0, 9e3, kappa=1.6,
                             dust_sensitivity=0.6),
        # --- compute: o Arrhenius literal do chassi (como a OmniMind) ---
        "compute_core":    L("compute_core", "compute", 60.0, 6e5, kappa=2.0,
                             rad_sensitivity=1.6, dust_sensitivity=0.2),
        # --- fleet ---
        "robot_joints":    L("robot_joints", "fleet", 52.0, 3e4, kappa=1.1,
                             dust_sensitivity=1.8, perchlorate_contact=True),
    }


# cascata: quem sofre quando uma camada cruza o limiar
CASCADE = {
    "hull_primary":    {"eclss_loop": 1.5},        # vazamento -> carga no loop
    "solar_arrays":    {"power_margin": -1.0},     # deposição -> -geração
    "radiators":       {"power_margin": -0.5},
    "isru_plant":      {"prop_output": -1.0},      # refino cai -> retorno longe
    "compute_core":    {"ALL": 0.6},               # o corpo que mede degrada tudo
    "robot_joints":    {"repair_capacity": -0.8},  # menos braços p/ reparar
}
WEAR_THRESHOLD = 0.35        # F neutrosófico que dispara a cascata


@dataclass
class StationBody:
    """A estação como corpo material: degrada por sol, recebe reparo,
    e emite séries de saúde — as superfícies que a malha enxerga.

    A REAÇÃO ao ambiente sai sozinho: env=REMS real entra em degrade(),
    então dust storm/UV/frio reais já estão dentro da cadeia — não é
    preciso "acoplar" depois, o corpo É o que responde."""

    layers: Dict[str, MaterialLayer] = field(default_factory=default_body)
    organ: Optional[SurfaceOrgan] = field(
        default_factory=SurfaceOrgan if SurfaceOrgan else lambda: None)
    boundary: Optional[AirlockOrgan] = field(
        default_factory=AirlockOrgan if AirlockOrgan else lambda: None)
    shield: Optional[ShieldStack] = None  # pilha de blindagem selecionável
    repair_fraction: float = 0.12   # fração do labor dedicada à manutenção
    wear_threshold: float = WEAR_THRESHOLD
    _incident_log: List[int] = field(default_factory=list)

    def step_sol(self, env: Dict[str, float], latent: float,
                 labor_h: float, rng: random.Random) -> Dict[str, float]:
        """Um sol do corpo: degrada tudo, resolve incidentes, aloca reparo."""
        incident = 0
        # choque latente extremo = incidente físico real (probabilístico)
        if latent > 2.2 and rng.random() < 0.35:
            incident = 1
            self._incident_log.append(1)
        else:
            self._incident_log.append(0)

        # órgão de superfície sente a mesma tempestade — ejeta, captura,
        # sinteriza; a blindagem acumulada atenua a dose do sol
        organ_rec: Dict[str, float] = {}
        env_eff = env
        if self.organ is not None:
            organ_rec = self.organ.step_sol(env, latent, rng)
            if self.organ.shielding_m > 0:
                att = 1.0 / (1.0 + self.organ.shielding_m
                             * self.organ.shielding_rad_gain)
                env_eff = dict(env)
                env_eff["rad_msv_day"] = env.get("rad_msv_day", 0.7) * att

        # pilha de blindagem selecionável: atenua UV (sombra opaca) e rad
        shield_rec: Dict[str, float] = {}
        if self.shield is not None:
            shield_rec = self.shield.step_sol(env)
            env_eff = dict(env_eff)
            env_eff["uv_abc_w_m2"] = (env_eff.get("uv_abc_w_m2", 0.03)
                                      * self.shield.uv_transmission())
            env_eff["rad_msv_day"] = (env_eff.get("rad_msv_day", 0.7)
                                      * self.shield.rad_transmission())

        # fronteira pressurizada: sorteios EVA -> ingresso -> dose inalada
        boundary_rec: Dict[str, float] = {}
        if self.boundary is not None:
            boundary_rec = self.boundary.step_sol(env, latent, rng)

        damage = {}
        # o grão ejetado nunca abrasa a superfície: as camadas expostas
        # veem o dust_flux PÓS-ejeção (e não um desconto de wear depois)
        EXPOSED = ("solar_arrays", "radiators", "optics_windows")
        env_exposed = env_eff
        if organ_rec and organ_rec["organ_deposited_kg"] > 0:
            frac_left = (organ_rec["organ_residual_fouling_kg"]
                         / organ_rec["organ_deposited_kg"])
            env_exposed = dict(env_eff)
            env_exposed["dust_flux"] = env_eff.get("dust_flux", 1.0) * frac_left
        for name, layer in self.layers.items():
            e = env_exposed if name in EXPOSED else env_eff
            d = layer.degrade(e, latent + incident * 1.5)
            damage[name] = d
            layer.wear = min(1.0, layer.wear + d)
            layer.anneal = min(1.0, layer.anneal + d * 0.25)   # dano residual

        # fouling residual fino (adesão sub-ejeção) ainda arranha a pele
        if organ_rec:
            fouling = organ_rec["organ_residual_fouling_kg"]
            for name in EXPOSED:
                layer = self.layers[name]
                layer.wear = min(1.0, layer.wear
                                 + fouling * self.organ.fouling_wear_gain)

        # o airlock desgasta as camadas que o contêm: o selo dele É
        # seals_joints; o filtro dele É eclss_loop (dano aditivo, não
        # camadas novas — preserva a comparabilidade de body_integrity)
        if boundary_rec:
            self.layers["seals_joints"].wear = min(
                1.0, self.layers["seals_joints"].wear
                + boundary_rec.get("_seal_wear_delta", 0.0))
            self.layers["eclss_loop"].wear = min(
                1.0, self.layers["eclss_loop"].wear
                + boundary_rec.get("_filter_wear_delta", 0.0))
            boundary_rec = {k: v for k, v in boundary_rec.items()
                            if not k.startswith("_")}

        # cascata: limiar cruzado propaga para o alvo
        cascade_load = 0.0
        for name, targets in CASCADE.items():
            if self.layers[name].wear > self.wear_threshold:
                cascade_load += sum(abs(v) for v in targets.values())
                for tgt, w in targets.items():
                    if tgt in self.layers:
                        self.layers[tgt].wear = min(
                            1.0, self.layers[tgt].wear + abs(w) * 3e-5)

        # reparo: horas alocadas tiram wear, mas anneal persiste
        repair_h = labor_h * self.repair_fraction
        budget = repair_h * 1e-6                                # h -> fração de wear
        worst = sorted(self.layers.values(),
                       key=lambda l: l.wear - l.anneal, reverse=True)
        for layer in worst:
            heal = min(budget / max(len(worst), 1) * 3, layer.wear - layer.anneal)
            layer.wear -= max(0.0, heal)

        integrity = 1.0 - sum(l.wear for l in self.layers.values()) / len(self.layers)
        return {"body_integrity": round(integrity, 5),
                "repair_load_h": round(repair_h, 2),
                "cascade_load": round(cascade_load, 3),
                "incident": incident,
                # wear_* = estado cumulativo; wear_rate_* = dano BRUTO do sol
                # (pre-reparo) — o sinal direto do clima, sem co-movimento de
                # integral. Na malha, wear_rate x REMS mostra o acoplamento real.
                **{f"wear_{n}": round(l.wear, 5) for n, l in self.layers.items()},
                **{f"wear_rate_{n}": round(damage[n], 8)
                   for n in self.layers},
                **organ_rec, **shield_rec, **boundary_rec}

    def series(self, n_sols: int,
               env_series: Optional[Dict[str, List[float]]] = None,
               latent: Optional[List[float]] = None,
               labor_h_series: Optional[List[float]] = None,
               seed: int = 11) -> Dict[str, List[float]]:
        """Roda o corpo por n_sols e emite as superfícies de saúde.

        env_series: dict de séries ambientais (REMS real ou default
        marciano). Se ausente, usa defaults de Gale."""
        rng = random.Random(seed)
        # choque do sol = INCREMENTO do walk latente (a excursão diária,
        # não o nível acumulado — senão o drift cresce sem bound e o corpo
        # satura; o imprevisto é o salto, não a posição)
        inc = [0.0] if not latent else [0.0] + [
            abs(latent[i] - latent[i - 1]) for i in range(1, len(latent))]
        out: Dict[str, List[float]] = {}
        for t in range(n_sols):
            env = {k: v[t] for k, v in (env_series or {}).items()
                   if t < len(v)}
            env.setdefault("air_temp_k", 210.0)
            env.setdefault("ground_temp_delta", 60.0)
            env.setdefault("uv_abc_w_m2", 0.03)
            env.setdefault("dust_flux", 1.0 + 0.3 * math.sin(t / 180.0))
            env.setdefault("rad_msv_day", 0.7)
            env.setdefault("perchlorate_wt", 0.6)
            lt = inc[t] if t < len(inc) else 0.0
            lab = labor_h_series[t] if labor_h_series else 60.0
            rec = self.step_sol(env, lt, lab, rng)
            for k, v in rec.items():
                out.setdefault(k, []).append(v)
        return out

    def neutrosophic_state(self) -> Dict[str, Dict[str, float]]:
        """Foto T/I/F de todas as camadas — o estado do corpo agora."""
        return {n: l.neutrosophic() for n, l in self.layers.items()}

    def apply_dust_catalyst(self, relief_map: Dict[str, float]) -> None:
        """EDS/ESP ativos reduzem o dust_sensitivity efetivo das camadas
        cobertas — a poeira vira insumo em vez de só desgaste."""
        for name, relief in relief_map.items():
            if name in self.layers:
                self.layers[name].dust_sensitivity *= max(0.0, 1.0 - relief)
