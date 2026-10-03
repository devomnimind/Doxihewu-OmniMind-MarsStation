"""Mars Cross-Layer — malha de correlação topológica da estação (Phase14/56 marciano).

Réplica do padrão SHG runtime theory mesh (src/analysis/shg_runtime_theory_mesh.py)
para a Máquina-Árvore: define SUPERFÍCIES de dados (clima REMS, sismicidade SEIS,
terreno MOLA, geoquímica de solo, sensores da estufa, microbioma, evolução,
água/energia, escavações) e cruza TODAS entre si, topologicamente, achando
CORRELATOS, ARESTAS e PONTES temáticas — a máquina escava qualquer dado e
descobre relações que nenhum módulo isolado veria.

Diferença vs Phase14/56 (6144/2078 canais): aqui as fontes são as superfícies
reais da estação (parquet REMS/MOLA/SEIS + sensores) e a saída é um GRAFO de
correlações com pontes explicativas (ex: perclorato ↔ microbioma ↔ evolução;
sismicidade ↔ estabilidade estrutural ↔ túneis).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class MarsSurfaceSpec:
    """Uma superfície de dados da estação (analogia RuntimeSurfaceSpec)."""

    surface_id: str
    label: str
    kind: str            # climate | seismic | terrain | soil | sensor | microbiome | evolution | resource | excavation
    source: str          # de onde vêm os dados (parquet/sensor/simulação)
    rationale: str


MARS_SURFACES: Tuple[MarsSurfaceSpec, ...] = (
    MarsSurfaceSpec("rems_climate", "Clima REMS (T, vento, poeira, umidade)", "climate",
                    "parquet/rems_dodeca.parquet", "forçamento ambiental real (Curiosity)"),
    MarsSurfaceSpec("seis_seismic", "Sismicidade InSight (Mw)", "seismic",
                    "parquet/seis_meta.json", "eventos sísmicos reais (2.716 no catálogo)"),
    MarsSurfaceSpec("mola_terrain", "Terreno MOLA (altitude/declividade)", "terrain",
                    "parquet/mola_tiles.parquet", "topografia real do sítio"),
    MarsSurfaceSpec("soil_geochem", "Geoquímica do solo (APXS/MMS-1)", "soil",
                    "PDS APXS + literatura MMS-1", "percloratos, Ca/Mg/K/Fe, pH"),
    MarsSurfaceSpec("greenhouse_sensors", "Sensores da estufa (pH/O2/CO2/T)", "sensor",
                    "sensores por braço", "estado interno do cultivo"),
    MarsSurfaceSpec("microbiome", "Microbioma (Shannon, contaminação)", "microbiome",
                    "MicrobiomeManager", "diversidade + higiene aprendida"),
    MarsSurfaceSpec("evolution", "Evolução (traços mutagênicos)", "evolution",
                    "MarcianMutagenesis/EvolutionGate", "ganhos de perclorato/frio/radiação"),
    MarsSurfaceSpec("resources", "Recursos (água, energia, nutrientes)", "resource",
                    "LifeSupport/CircularEconomy", "fechamento dos ciclos"),
    MarsSurfaceSpec("excavation", "Escavações (túneis, elevadores, gelo)", "excavation",
                    "IceElevator + túneis Voronoi", "profundidade, fluxo de gelo, amostras"),
    MarsSurfaceSpec("circadian_rhythm", "Ritmo circadiano P3 (período livre)", "evolution",
                    "MartianCircadian", "entranhamento no sol 24h39 — traço emergente"),
    MarsSurfaceSpec("machine_symbiosis", "Simbiose máquina-planta P4", "evolution",
                    "MachinePlantSymbiosis", "fotossíntese sincronizada ao ciclo elétrico"),
    MarsSurfaceSpec("metallurgy", "Metalurgia ISRU (Fe/Al/Ti, geopolímero)", "resource",
                    "mars_metallurgy", "fluxos secundários -> novos materiais (gerado de novo)"),
    MarsSurfaceSpec("soil_processing", "Processamento do regolito (veios, lixiviação)", "soil",
                    "RegolithProcessor+SulfateVeinClassifier", "amostra -> classifica -> lixivia"),
)


@dataclass
class MarsCrossLayer:
    """Cruza todas as superfícies e produz correlatos/arestas/pontes.

    Correlação com atraso temporal (lag 0-5 sols) entre pares de séries.
    Pontes temáticas: triplas pré-definidas que explicam cadeias causais.
    """

    min_corr: float = 0.30
    max_lag: int = 5
    rng_seed: int = 7

    def correlate(self, series_a: List[float], series_b: List[float],
                  lag_max: int | None = None) -> Dict:
        """Pearson com atraso; retorna melhor lag e correlação."""
        import math
        n = min(len(series_a), len(series_b))
        if n < 8:
            return {"corr": 0.0, "lag": 0, "n": n}
        lag_max = lag_max or self.max_lag
        best = (0.0, 0)
        for lag in range(0, min(lag_max + 1, n - 4)):
            a, b = series_a[:n - lag], series_b[lag:n]
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
            da = math.sqrt(sum((x - ma) ** 2 for x in a))
            db = math.sqrt(sum((y - mb) ** 2 for y in b))
            corr = num / (da * db) if da * db > 0 else 0.0
            if abs(corr) > abs(best[0]):
                best = (corr, lag)
        return {"corr": round(best[0], 4), "lag_sols": best[1], "n": n}

    def correlate_detrended(self, series_a: List[float],
                            series_b: List[float]) -> Dict:
        """Correlação sobre a série DIFERENCIADA (lição 2026-09-28).

        Séries cumulativas (escavação, higiene, evolução) têm raw≈1.0 por
        tendência compartilhada — artefato, não causalidade. O detrend por
        diferença de primeira ordem mede correlação entre INCREMENTOS.
        """
        da = [series_a[i + 1] - series_a[i] for i in range(len(series_a) - 1)]
        db = [series_b[i + 1] - series_b[i] for i in range(len(series_b) - 1)]
        return self.correlate(da, db)

    def build_mesh(self, series: Dict[str, List[float]],
                   bridges: List[Tuple[str, str, str]] | None = None,
                   detrend: bool = True) -> Dict:
        """Malha completa: arestas (pares correlacionados) + pontes temáticas.

        detrend=True adiciona corr_diff a cada aresta — a correlação honesta
        entre incrementos. Se |raw|>=min_corr mas |diff|<min_corr, a aresta é
        marcada trend_artifact=True (tendência compartilhada, não causal)."""
        edges = []
        ids = list(series.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                r = self.correlate(series[ids[i]], series[ids[j]])
                if abs(r["corr"]) >= self.min_corr:
                    edge = {"a": ids[i], "b": ids[j], **r,
                            "strength": "forte" if abs(r["corr"]) >= 0.6 else "moderada",
                            "sign": "positiva" if r["corr"] > 0 else "negativa"}
                    if detrend:
                        rd = self.correlate_detrended(series[ids[i]], series[ids[j]])
                        edge["corr_diff"] = rd["corr"]
                        edge["trend_artifact"] = abs(rd["corr"]) < self.min_corr
                    edges.append(edge)
        edges.sort(key=lambda e: -abs(e["corr"]))
        bridge_out = []
        for (a, b, c) in (bridges or []):
            r_ab = self.correlate(series.get(a, []), series.get(b, []))
            r_bc = self.correlate(series.get(b, []), series.get(c, []))
            bridge_out.append({"bridge": f"{a} → {b} → {c}",
                               "corr_ab": r_ab["corr"], "corr_bc": r_bc["corr"],
                               "plausible": abs(r_ab["corr"]) >= self.min_corr
                                            and abs(r_bc["corr"]) >= self.min_corr})
        return {"n_surfaces": len(ids), "edges": edges, "bridges": bridge_out,
                "top_edge": edges[0] if edges else None}

    # ---- pontes temáticas padrão da estação ----
    STANDARD_BRIDGES = [
        ("rems_climate", "greenhouse_sensors", "evolution"),   # clima -> estufa -> evolução
        ("soil_geochem", "microbiome", "evolution"),           # perclorato -> microbioma -> evolução
        ("seis_seismic", "excavation", "resources"),           # sísmico -> túneis -> recursos
        ("mola_terrain", "excavation", "resources"),           # terreno -> escavação -> água/gelo
        ("greenhouse_sensors", "microbiome", "resources"),     # estufa -> microbioma -> ciclos
        ("rems_climate", "seis_seismic", "excavation"),        # clima+sísmico -> risco estrutural
        ("circadian_rhythm", "greenhouse_sensors", "resources"),  # P3 -> fotossíntese -> recursos
        ("machine_symbiosis", "resources", "evolution"),       # P4 -> eficiência -> evolução
        ("excavation", "soil_processing", "metallurgy"),       # amostra -> classifica -> refina
        ("metallurgy", "resources", "excavation"),             # materiais novos -> escava mais
        ("soil_geochem", "soil_processing", "microbiome"),     # geoquímica -> veio -> solo cultivável
    ]
