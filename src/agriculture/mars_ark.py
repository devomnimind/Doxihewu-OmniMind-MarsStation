"""Mars Ark — o primeiro cargueiro já leva vida; robôs são os tratadores.

Visão do operador (2026-09-28): "poderíamos levar colônias, insetos,
animais na primeira viagem? A robótica futura desempenha atividades
tutelares — já cuidam de ambiente doméstico hoje — espécies escolhidas
por afinidade ao ambiente, ou mantidas no sistema mínimo de suporte
de vida pelos robôs."

Organização: três níveis de cuidado, ordenados por afinidade — do
organismo que vive QUASE livre (no solo da estufa) até o que depende
100% do MLS (Minimum Life Support) mantido pela frota.

  Tier 1 SOLO VIVO     — vive no regolito emendado: micróbios, nematoides,
                         colêmbolos, ácaros (fazem pedogênese = viram solo)
  Tier 2 VIVÁRIO       — semi-adaptados, baixo cuidado: mealworm (Tenebrio),
                         mosca-soldado (Hermetia), rotíferos, tardígrados,
                         isópodos (recicladores de resíduo + proteína)
  Tier 3 MLS COMPLETO  — vertebrados: peixes (aquaponia), roedores —
                         E SÃO o experimento do HabitabilityGate
                         (gerações de mamíferos em 0.38g)

O fechamento arquitetural: a arca não é só carga — o Tier 3 É o gate
que decide quando humanos embarcam (mars_colossus.HABITABILITY_GATE:
"geracoes_mamiferos_ok_min": 3).

Âncoras reais: mealworm já é cultura proteica estudada p/ Marte;
tardígrados sobreviveram vácuo espacial (FOTON-M3, criptobiose);
rotíferos sobreviveram congelados na ISS; cianobactérias Nostoc são
proposta real de fixação O2/N2; Hermetia illucens recicla resíduo
orgânico -> proteína (literatura ESA MELiSSA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============ Manifesto vivo — ordenado por afinidade ao ambiente ============

LIVING_CARGO: List[Dict] = [
    # ---- Tier 1: praticamente livres no solo da estufa ----
    {"id": "cianobacteria_nostoc", "tier": 1, "classe": "micróbio",
     "afinidade": "fotossintetiza em CO2/pressão baixa; fixa N2",
     "papel": "O2 + fixação de nitrogênio — fertiliza o regolito",
     "mls_h_sol": 0.0, "ancora": "proposta real ISRU biológico"},
    {"id": "microbioma_solo", "tier": 1, "classe": "consórcio microbiano",
     "afinidade": "vive no regolito emendado 70:30 (microbiome_manager)",
     "papel": "pedogênese — transforma regolito em SOLO",
     "mls_h_sol": 0.1, "ancora": "módulo microbiome_manager"},
    {"id": "nematoides_celegans", "tier": 1, "classe": "nematóide",
     "afinidade": "voou ao espaço muitas vezes; solo úmido",
     "papel": "predador-modelo do solo; bioindicador",
     "mls_h_sol": 0.05},
    {"id": "colembolos_acaros", "tier": 1, "classe": "artrópodes do solo",
     "afinidade": "vivem em solo, fragmentam matéria orgânica",
     "papel": "decompositores — fecham o ciclo de nutrientes",
     "mls_h_sol": 0.05},

    # ---- Tier 2: vivário mínimo, alta tolerância ----
    {"id": "mealworm_tenebrio", "tier": 2, "classe": "inseto",
     "afinidade": "substrato seco, sobrevive desidratação parcial",
     "papel": "proteína (mealworm_protein.py) + recicla farelo",
     "mls_h_sol": 0.3, "ancora": "proteína espacial estudada real"},
    {"id": "mosca_soldado", "tier": 2, "classe": "inseto (larva)",
     "afinidade": "larva come resíduo orgânico de qualquer tipo",
     "papel": "resíduo orgânico -> proteína/gordura (MELiSSA-like)",
     "mls_h_sol": 0.3},
    {"id": "tardigrados", "tier": 2, "classe": "extremófilo",
     "afinidade": "CRIPTOSIose — suspensos secos até precisar",
     "papel": "estoque vivo à prova de desastre (backup biológico)",
     "mls_h_sol": 0.0, "ancora": "sobreviveram vácuo espacial (FOTON-M3)"},
    {"id": "rotiferos", "tier": 2, "classe": "extremófilo",
     "afinidade": "congelados/dormência prolongada",
     "papel": "aquário/decomposição aquática",
     "mls_h_sol": 0.05, "ancora": "sobreviveram congelados na ISS"},
    {"id": "isopodos", "tier": 2, "classe": "crustáceo terrestre",
     "afinidade": "solo úmido sombreado, tolerante",
     "papel": "decompositor de resíduo vegetal",
     "mls_h_sol": 0.1},

    # ---- Tier 3: MLS completo — o experimento do gate humano ----
    {"id": "peixes_aquaponia", "tier": 3, "classe": "vertebrado",
     "afinidade": "exige água pressurizada fechada",
     "papel": "proteína + aquaponia (excremento fertiliza planta)",
     "mls_h_sol": 1.5},
    {"id": "roedores_colonia", "tier": 3, "classe": "mamífero",
     "afinidade": "MLS completo — e SÃO o experimento",
     "papel": "gate de habitabilidade: geram dados de gestação 0.38g",
     "mls_h_sol": 2.0, "ancora": "HABITABILITY_GATE['geracoes_mamiferos_ok_min']"},
    # polinizadores intencionalmente AUSENTES do tier livre:
    {"id": "abelhas", "tier": 3, "classe": "inseto voador",
     "afinidade": "voo exige densidade de ar ~terrestre; em domo só",
     "papel": "polinização — ATÉ lá, robôs polinizam",
     "mls_h_sol": 0.8, "nota": "voo em pressão baixa inviável"},
]


# ============ Vivário — o MLS mínimo mantido pelos robôs ============

@dataclass
class VivariumSystem:
    """Sistema mínimo de suporte de vida por tier, mantido pela frota."""

    def robot_hours_sol(self, cargo: List[Dict] = None) -> float:
        """Horas de frota que a arca consome por sol (soma mls_h_sol)."""
        cargo = cargo or LIVING_CARGO
        return round(sum(c["mls_h_sol"] for c in cargo), 2)

    def tiers_summary(self) -> Dict[int, Dict]:
        out = {}
        for c in LIVING_CARGO:
            t = out.setdefault(c["tier"], {"especies": 0, "mls_h_sol": 0.0})
            t["especies"] += 1
            t["mls_h_sol"] = round(t["mls_h_sol"] + c["mls_h_sol"], 2)
        return out

    def survivable_without_robots(self) -> List[str]:
        """O que sobrevive mesmo se a frota parar — criptobiose + solo vivo."""
        return [c["id"] for c in LIVING_CARGO
                if c["mls_h_sol"] <= 0.05]


@dataclass
class ArkCaretaker:
    """Frota de robôs como tratadores: compara demanda da arca com a
    capacidade líquida do LaborEconomy (mars_colossus)."""

    def coverage(self, net_labor_h_sol: float) -> Dict:
        need = VivariumSystem().robot_hours_sol()
        frac = need / max(net_labor_h_sol, 0.001)
        return {"mls_demand_h_sol": need,
                "net_labor_h_sol": net_labor_h_sol,
                "labor_frac_usada": round(frac, 4),
                "viavel": frac < 0.05,   # arca consome <5% do trabalho líquido
                "nota": "carga viva é barata — a maioria vive quase livre"}

    def gate_link(self) -> Dict:
        """O Tier 3 roedor É o experimento do HabitabilityGate."""
        try:
            from mars_colossus import HABITABILITY_GATE
        except ImportError:
            from src.agriculture.mars_colossus import HABITABILITY_GATE
        return {"experimento": "roedores_colonia",
                "produz": "geracoes_mamiferos_ok",
                "gate_exige": HABITABILITY_GATE["geracoes_mamiferos_ok_min"],
                "fechamento": "a arca alimenta o gate que libera humanos"}
