"""Mars Metallurgy — refino de elementos secundários e geração de novos materiais.

Pergunta do operador (2026-09-28): "com esses elementos secundários criados,
eles passam por processos e refinamento, ou mistura com os componentes
primários ou secundários entre si — o que precisaria e poderia ser gerado
de novo?"

Resposta estruturada (dados APXS/CheMin reais + literatura ISRU):

FLUXOS SECUNDÁRIOS gerados pela estação (subprodutos):
  Fe oxides   — separação magnética (magnetita/hematita/ilmenita FeTiO3)
  Ca + S      — lixiviação seletiva de veios de sulfato (gypsum/anhydrite)
  Cl / ClO4   — perclorato + halita NaCl
  SiO2/Al2O3  — matriz basáltica residual (~45%/~9% APXS)
  TiO2        — ilmenita residual
  MgO, NaCl, apatita-P, Ni/Zn/Br vestígios
  CH4/CO/O2/H2 — Sabatier + eletrólise CO2

PROCESSOS DE REFINO:
  carboredução   — CO reduz FeO->Fe (~800°C), parcial SiO2->Si
  eletrólise     — sais fundidos FFC/MOE: Al, Ti, Ca, Mg, Si; O2 byproduct
  sinterização   — regolito -> cerâmica/tijolo (sem cimento)
  geopolímero    — aluminosilicato + ativador -> cimento marciano (sem cal!)
  sulfurização   — S -> H2SO4 (alimenta a própria lixiviação — LOOP fechado)
  Haber-Bosch    — N2 atmosfera + H2 -> NH3 (fertilizante/refrigerante)

GERADO DE NOVO (materiais que não existem na Terra ou só viáveis lá):
  - aço marciano dopado (Fe + Ni/Cr/S/P residuais do regolito)
  - fibra de basalto (basalt fiber — casca de braços/estufa)
  - geopolímero de sulfato (CaSO4+aluminosilicato — cimento de veio)
  - vidro basáltico (SiO2+FeO — painéis/tubos opacos de proteção)
  - eletrólito de sal-gema (NaCl fundido — baterias térmicas)
  - propelente ClO4 -> NH4ClO4-like (perclorato = oxidante sólido)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============ Inventário de fluxos secundários ============

# frações médias medidas (APXS Gale + CheMin) por kg de regolito
SECONDARY_STREAMS: Dict[str, Dict] = {
    "fe_oxides":   {"frac": 0.19, "source": "separação magnética",
                    "product": "Fe/Ti metal via carboredução ou eletrólise"},
    "cao_s":       {"frac": 0.10, "source": "lixiviação de veios de sulfato",
                    "product": "Ca nutriente + S -> H2SO4 (loop)"},
    "sio2_matrix": {"frac": 0.45, "source": "matriz basáltica residual",
                    "product": "vidro basáltico, geopolímero, Si"},
    "al2o3":       {"frac": 0.09, "source": "matriz basáltica residual",
                    "product": "Al via eletrólise sais fundidos"},
    "tio2":        {"frac": 0.01, "source": "ilmenita residual",
                    "product": "Ti via eletrólise (FFC)"},
    "mgo":         {"frac": 0.07, "source": "matriz residual",
                    "product": "Mg via eletrólise; refratário"},
    "nacl":        {"frac": 0.01, "source": "halita de veios",
                    "product": "eletrólito NaCl fundido; Cl2; NaOH"},
    "apatite_p":   {"frac": 0.009, "source": "apatita (CheMin)",
                    "product": "P -> fertilizante"},
    "nacl_clo4":   {"frac": 0.005, "source": "perclorato",
                    "product": "Cl2, O2 por decomposição; oxidante propelente"},
    "ch4_co_o2":   {"frac": 0.0,  "source": "Sabatier + eletrólise CO2",
                    "product": "redutor (CO), propelente, polímeros C"},
}


@dataclass
class SecondaryStreamInventory:
    """Calcula kg de cada fluxo secundário por tonelada de regolito."""

    streams: Dict[str, Dict] = field(default_factory=lambda: dict(SECONDARY_STREAMS))

    def inventory(self, regolith_kg: float = 1000.0) -> Dict[str, Dict]:
        out = {}
        for name, s in self.streams.items():
            kg = regolith_kg * s["frac"]
            out[name] = {"kg": round(kg, 3), "source": s["source"],
                         "product": s["product"]}
        return out


# ============ Processos de refino ============

@dataclass
class RefineryProcess:
    """Um processo ISRU com entrada -> saída e custo energético estimado."""

    name: str
    input_stream: str
    products: Dict[str, float]     # produto -> yield fracionário da entrada
    energy_kwh_per_kg: float
    temp_c: float = 0.0
    note: str = ""


REFINERY_PROCESSES: List[RefineryProcess] = [
    RefineryProcess("carboreduction", "fe_oxides",
                    {"fe_metal": 0.72, "co2_offgas": 0.28},  # CO redutor
                    energy_kwh_per_kg=1.2, temp_c=800,
                    note="CO da eletrólise CO2 reduz FeO; subproduto = CO2 (loop)"),
    RefineryProcess("molten_salt_electrolysis", "al2o3",
                    {"al_metal": 0.53, "o2": 0.47},
                    energy_kwh_per_kg=13.0, temp_c=960,
                    note="FFC/Hall-Héroult marciano — Al estrutural"),
    RefineryProcess("ffc_titanium", "tio2",
                    {"ti_metal": 0.60, "o2": 0.40},
                    energy_kwh_per_kg=15.0, temp_c=900,
                    note="FFC Cambridge — Ti leve para estruturas"),
    RefineryProcess("sintering", "sio2_matrix",
                    {"ceramic_brick": 0.95},
                    energy_kwh_per_kg=0.4, temp_c=1150,
                    note="regolito sinterizado -> tijolo/cerâmica sem cimento"),
    RefineryProcess("geopolymer", "sio2_matrix",
                    {"geopolymer_cement": 0.9},
                    energy_kwh_per_kg=0.15, temp_c=80,
                    note="aluminosilicato + NaOH (de NaCl) -> cimento sem cal"),
    RefineryProcess("sulfur_cycle", "cao_s",
                    {"h2so4": 1.53},  # S -> H2SO4 (x1.53 em massa)
                    energy_kwh_per_kg=0.5, temp_c=450,
                    note="S do gesso -> H2SO4 que ALIMENTA a lixiviação (loop fechado)"),
    RefineryProcess("haber_bosch", "ch4_co_o2",
                    {"nh3": 0.56},   # N2 + 3H2 -> 2NH3
                    energy_kwh_per_kg=7.5, temp_c=450,
                    note="N2 atmosférico -> amônia -> fertilizante/refrigerante"),
    RefineryProcess("perchlorate_decomp", "nacl_clo4",
                    {"cl2": 0.45, "o2": 0.55},
                    energy_kwh_per_kg=0.8, temp_c=300,
                    note="perclorato -> Cl2 (desinfecção/PVC) + O2"),
]


@dataclass
class Refinery:
    """Aplica um processo a um fluxo secundário e retorna produtos."""

    processes: Dict[str, RefineryProcess] = field(
        default_factory=lambda: {p.name: p for p in REFINERY_PROCESSES})

    def refine(self, process_name: str, input_kg: float) -> Dict:
        p = self.processes[process_name]
        products = {k: round(input_kg * v, 3) for k, v in p.products.items()}
        return {"process": process_name, "input_kg": input_kg,
                "products": products,
                "energy_kwh": round(input_kg * p.energy_kwh_per_kg, 2),
                "temp_c": p.temp_c, "note": p.note}


# ============ Ligas e materiais emergentes (gerado de novo) ============

@dataclass
class EmergentMaterial:
    """Um material marciano novo (não existente ou só viável em Marte)."""

    name: str
    feedstocks: List[str]
    description: str
    emergent: bool = True      # não existe na Terra / só viável lá


EMERGENT_MATERIALS: List[EmergentMaterial] = [
    EmergentMaterial("mars_steel", ["fe_metal", "ni_trace", "cr_trace", "s_trace"],
                     "aço marciano — Fe do regolito + Ni/Cr/S/P naturais "
                     "(dopagem que a Terra separa, Marte oferece grátis)"),
    EmergentMaterial("basalt_fiber", ["sio2_matrix"],
                     "fibra de basalto contínua — casca de braços, reforço de domo"),
    EmergentMaterial("sulfate_geopolymer", ["sio2_matrix", "cao_s", "naoh"],
                     "geopolímero de sulfato — cimento marciano SEM cal "
                     "(só possível porque Marte tem CaSO4 de sobra)"),
    EmergentMaterial("basalt_glass", ["sio2_matrix", "fe_oxides"],
                     "vidro basáltico opaco — painéis/tubos de proteção UV"),
    EmergentMaterial("molten_salt_battery", ["nacl", "mg_metal"],
                     "NaCl/Mg fundido — bateria térmica de alta densidade"),
    EmergentMaterial("perchlorate_propellant", ["nacl_clo4"],
                     "oxidante sólido de perclorato — propelente ISRU"),
]


@dataclass
class MetallurgyLoop:
    """Fecha o ciclo: resíduo de uma etapa = matéria-prima da seguinte.

    Loops identificados:
      sulfur: veio -> lixiviação -> S -> H2SO4 -> alimenta lixiviação
      carbon: CO2 -> eletrólise -> CO -> carboredução -> CO2
      glass:  matriz -> sinterização/geopolímero -> construção
    """

    def loop_report(self) -> Dict[str, str]:
        return {
            "sulfur": "veio -> lixiviação seletiva -> S -> H2SO4 -> nova lixiviação",
            "carbon": "CO2 -> eletrólise -> CO -> carboredução Fe -> CO2",
            "glass":  "matriz residual -> sinterização/geopolímero -> material de construção",
            "nitrogen": "N2 atmosfera -> Haber-Bosch -> NH3 -> fertilizante",
        }
