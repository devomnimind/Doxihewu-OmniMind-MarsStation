"""Mars Environment Series — tudo que varia no ambiente entra na malha.

Princípio do operador (2026-09-28): a série temporal correta inclui
TODAS as variáveis do ambiente — clima solar real (REMS), composição e
amostras dos solos, energia, estufa, processamento — MAIS uma margem
honesta de imprevistos: choques latentes não computados (tempestade de
poeira, flare solar, falha de equipamento, descoberta inesperada).

O ponto metodológico (honestidade estatística):
  - Choque latente atinge várias superfícies NO MESMO SOL ->
    correlação de INCREMENTO real (corr_diff alta) — não artefato
    de tendência. A malha descobre o acoplamento sem o driver ter nome.
  - Séries com tendência cumulativa mas incrementos independentes ->
    trend_artifact (a malha já sabe marcar).
  Assim a margem de imprevisto é modelada EXPLICITAMENTE, não escondida:
  a estação admite que o ambiente tem drivers não computados e mede
  quanto cada superfície responde a eles (loading).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List


# ============ Processo de choque latente — a margem de imprevistos ============

@dataclass
class LatentShockProcess:
    """Driver ambiental NÃO nomeado: mistura de fundo contínuo +
    eventos raros grandes (tempestade regional, flare, falha, descoberta).

    Gerado como random walk com saltos ocasionais de grande amplitude —
    análogo ao ciclo de poeira marciano (sazonal ~Ls 200-330) e a falhas
    pontuais da estação.
    """

    shock_prob: float = 0.03        # ~1 evento grande por mês marciano
    shock_scale: float = 3.0        # amplitude do evento (sigma)
    drift: float = 0.15             # fundo contínuo (sazonalidade suave)

    def sample(self, n: int, seed: int = 42) -> List[float]:
        rng = random.Random(seed)
        x, vals = 0.0, []
        for _ in range(n):
            step = rng.gauss(0.0, self.drift)
            if rng.random() < self.shock_prob:          # imprevisto!
                step += rng.gauss(0.0, self.shock_scale)
            x += step
            vals.append(round(x, 5))
        return vals


# ============ Superfície da estação — sinal próprio + resposta ao choque ============

@dataclass
class StationSurface:
    """Uma série temporal da estação/ambiente.

    value[t] = own_signal[t] + shock_loading * latent[t] + noise[t]
    shock_loading alto = superfície sensível a imprevistos
    (ex: energia solar é MUITO sensível a tempestade de poeira).
    """

    name: str
    own_amp: float = 1.0          # amplitude do sinal próprio (ciclo/regras)
    shock_loading: float = 0.0    # sensibilidade ao driver latente
    noise: float = 0.3

    def generate(self, latent: List[float], seed: int = 7) -> List[float]:
        # seed determinística: mesmo nome+seed = mesma série em qualquer processo
        det = seed + sum(ord(ch) * (i + 1) for i, ch in enumerate(self.name))
        rng = random.Random(det)
        n = len(latent)
        import math
        own = [self.own_amp * math.sin(2 * math.pi * t / 668.6)   # sazonalidade anual
               + rng.gauss(0.0, self.noise) for t in range(n)]
        return [round(own[t] + self.shock_loading * latent[t], 5)
                for t in range(n)]


# ============ Acoplamento da estação — mars_base/mars_colossus viram série ============

@dataclass
class StationGrowthModel:
    """Projeta o plano de 60 anos (mars_colossus) como séries por sol.

    Uma janela de n_sols cobre `window_synods` synods a partir de
    `start_synod` — assim o crescimento da camada maquínica entra na
    malha temporal junto ao clima real e aos choques latentes.

    Superfícies emitidas (valores derivados dos modelos, não inventados):
      station_mass_t   — massa acumulada (landers ficam + produção local)
      robot_fleet      — frota humanoide ativa
      labor_net_h      — horas líquidas de trabalho (LaborEconomy)
      power_kwh        — orçamento energético (PowerBudget; sensível a poeira)
      humans_total     — zero até o HabitabilityGate abrir
    """

    start_synod: int = 0
    window_synods: float = 3.0   # ~2340 sols cobrem 3 synods; comprimido se n_sols < isso

    def synod_at(self, t: int, n_sols: int) -> float:
        return self.start_synod + self.window_synods * t / max(n_sols - 1, 1)

    def series(self, n_sols: int, latent: List[float] = None) -> Dict[str, List[float]]:
        try:    # repo: src.agriculture.*; Colab: módulos flat em simulation_modules_v2
            from src.agriculture.mars_base import PowerBudget
            from src.agriculture.mars_colossus import (StationPlan60,
                                                       LaborEconomy, HumanCohorts)
        except ImportError:
            from mars_base import PowerBudget
            from mars_colossus import StationPlan60, LaborEconomy, HumanCohorts
        plan = StationPlan60()
        out = {k: [] for k in ("station_mass_t", "robot_fleet", "labor_net_h",
                               "power_kwh", "humans_total")}
        prev_synod, snap = -1, None
        for t in range(n_sols):
            s = self.synod_at(t, n_sols)
            si = int(s)
            if si != prev_synod:                # reavalia só ao cruzar synod
                snap = plan.synod_snapshot(si)
                prev_synod = si
            out["station_mass_t"].append(snap["station_mass_t"])
            out["robot_fleet"].append(snap["robots_fleet"])
            out["labor_net_h"].append(snap["labor_net_h_sol"])
            # energia: fissão cresce com a era (2 unidades base + 1 por 2 synods)
            pb = PowerBudget(n_fission=2 + si // 2)
            solar_part = 500.0 * 0.77           # fração solar do orçamento
            shock = (latent[t] if latent else 0.0) * 0.15
            out["power_kwh"].append(round(
                pb.generation_kwh_sol() + solar_part * shock, 2))
            out["humans_total"].append(
                HumanCohorts().population(si, gate_open=True)["humanos_importados"]
                if si >= 17 else 0)
        return out



@dataclass
class EnvironmentalMeshBuilder:
    """Monta o dict de séries completo: REMS real + superfícies da
    estação + choque latente compartilhado (a margem não computada)."""

    seed: int = 42

    # loadings realistas — quem responde ao choque ambiental latente
    SURFACE_LOADINGS: Dict[str, float] = field(default_factory=lambda: {
        "rems_climate":      0.0,   # série REAL medida — injetada, não gerada
        "energy":            1.2,   # tempestade -> painel solar CAI forte
        "excavation":        0.9,   # poeira/visibilidade -> escava menos
        "greenhouse_sensors":0.7,   # temperatura/luz do ambiente
        "soil_processing":   0.6,   # throughput cai com excavação menor
        "metallurgy":        0.4,   # forno protegido, responde parcial
        "microbiome":        0.3,   # cultivo abrigado, resposta suave
        "resources":         0.8,   # água/propelente dependem de energia
        "machine_symbiosis": 0.5,
        "circadian_rhythm":  0.0,   # relógio não responde a poeira
    })

    def build(self, n_sols: int = 300,
              rems_series: Dict[str, List[float]] = None,
              include_latent_surface: bool = False,
              include_station: bool = False,
              start_synod: int = 0) -> Dict:
        """Retorna {"series": {...}, "latent": [...], "meta": {...}}.

        rems_series: dict {col: [valores]} já medido — entra como
        superfície real (rems_climate / colunas brutas rems_c*).
        include_latent: se True, expõe o driver latente como superfície
        "latent_margin" (para teste: a malha deve achar as arestas reais).
        include_station: se True, injeta as séries do plano de 60 anos
        (StationGrowthModel — mars_base/mars_colossus projetados por sol).
        """
        # 0) comprimento real: o menor entre o pedido e a série medida
        if rems_series:
            n_sols = min([n_sols] + [len(v) for v in rems_series.values()])
        latent = LatentShockProcess().sample(n_sols, seed=self.seed)
        series: Dict[str, List[float]] = {}

        # 1) séries reais medidas primeiro (REMS consolidated parquet)
        for name, vals in (rems_series or {}).items():
            series[name] = list(vals[:n_sols])

        # 2) superfícies da estação com resposta ao latente
        for name, loading in self.SURFACE_LOADINGS.items():
            if name in series: continue
            surf = StationSurface(name, shock_loading=loading)
            series[name] = surf.generate(latent, seed=self.seed)

        # 3) crescimento real da estação (mars_base/mars_colossus por sol)
        if include_station:
            for name, vals in StationGrowthModel(
                    start_synod=start_synod).series(n_sols, latent).items():
                series[name] = vals

        if include_latent_surface:
            series["latent_margin"] = list(latent)

        return {"series": series, "latent": latent,
                "meta": {"n_sols": n_sols, "n_surfaces": len(series),
                         "margin": "choques latentes incluídos nas séries",
                         "station": "mars_base/colossus projetados" if include_station else "off",
                         "honesty": "corr_diff separa acoplamento real de tendência"}}
