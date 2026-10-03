"""RegolithProcessor — geoquímica do regolito marciano (gap_7).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs_critical.gap_7

Composição: sulfatos (MgSO4/CaSO4 — fonte S), óxidos de Fe (hematita/magnetita —
abrasivos), argilas filossilicatos (água antiga, retém nutrientes), pH 4.5-8.5.
Processo: moagem -> separação magnética -> lixiviação ácida H2SO4 0.1M ->
neutralização -> troca iônica (ajuste NPK). Referência APXS/ChemCam/PIXL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

EXTRACTION_EFFICIENCY = {"Mg": 0.85, "Ca": 0.75, "K": 0.70, "P": 0.60, "Fe": 0.90}


@dataclass
class MagneticSeparator:
    """Remove hematita/magnetita abrasivas."""

    fe_removal_rate: float = 0.7

    def separate(self, powdered_kg: float, fe2o3_frac: float) -> Dict[str, float]:
        removed = powdered_kg * fe2o3_frac * self.fe_removal_rate
        return {"fe_removed_kg": removed, "remainder_kg": powdered_kg - removed}


@dataclass
class AcidLeaching:
    """Lixiviação com H2SO4 diluído para extrair nutrientes."""

    h2so4_concentration: float = 0.1
    efficiency: Dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.efficiency = dict(EXTRACTION_EFFICIENCY)

    def extract(self, regolith_kg: float, composition: Dict[str, float]) -> Dict[str, float]:
        """Extrai nutrientes solúveis: Mg/Ca/K/P/Fe conforme eficiência."""
        out: Dict[str, float] = {}
        for elem, frac in composition.items():
            eff = self.efficiency.get(elem, 0.5)
            out[elem] = regolith_kg * frac * eff
        return out


@dataclass
class IonExchange:
    """Ajusta o balanço NPK do fertilizante."""

    def balance(self, nutrients: Dict[str, float], target: Dict[str, float]) -> Dict[str, float]:
        out = dict(nutrients)
        for k, tgt in target.items():
            out[f"{k}_ratio"] = out.get(k, 0.0) / tgt if tgt else 0.0
        return out


@dataclass
class OrganicAmendment:
    """Mistura regolito + emenda orgânica — Caporale et al. 2023 (ReBUS/ASI).

    Verificação 2026-09-28: em simulante MMS-1 (marciano), a razão
    **70:30 regolito:esterco** é a melhor em fertilidade e sustentabilidade
    (esterco = análogo do adubo produzido a bordo via resíduos/feces
    compostados). Acima de 30% esterco sobe demais salinidade (EC 6.7),
    sodicidade (Na 5.3 g/kg), Al solúvel e metais pesados (Pb/Ni/Cr/V).
    MMS-1 > LHS-1 lunar em desempenho agronômico (pH menor, mais nutrientes).
    """

    optimal_regolith_frac: float = 0.70   # 70:30 regolito:adubo
    optimal_amendment_frac: float = 0.30
    max_amendment_frac: float = 0.50      # acima: salinidade/metais sobem
    ec_toxicity_ds_m: float = 6.7         # condutividade do esterco puro

    def mix(self, amendment_frac: float) -> Dict[str, float]:
        """Score de qualidade do substrato vs fração de emenda orgânica."""
        # melhora nutrientes e retenção hídrica ~linear até ~30%; acima, a
        # penalidade de salinidade/metais domina (Caporale et al.)
        nutrient_gain = min(1.0, amendment_frac / self.optimal_amendment_frac)
        salinity_penalty = max(0.0, amendment_frac - self.optimal_amendment_frac) * 2.0
        quality = max(0.0, nutrient_gain - salinity_penalty)
        return {"regolith_frac": 1.0 - amendment_frac,
                "amendment_frac": amendment_frac,
                "quality_score": round(quality, 3),
                "optimal": abs(amendment_frac - self.optimal_amendment_frac) < 0.05,
                "salinity_risk": amendment_frac > self.optimal_amendment_frac}


@dataclass
class SulfateVeinClassifier:
    """Classifica amostras do regolito pela mineralogia real (CheMin Rietveld).

    Dados reais (PDS mslcmn_1xxx, 2026-09-28): o regolito de Gale alterna
    basalto (andesina+olivina+piroxênio) e VEIOS de sulfato — gypsum,
    anidrita, bassanita, jarosita, akaganeita, halite. Jarosita e
    akaganeita são marcadores de água ÁCIDA (pH<4) — não podem ir direto
    para a mistura 70:30.

    Regra: amostra com sulfatos >= threshold ou marcadores ácidos
    (jarosita+akaganeita) exige LIXIVIAÇÃO SELETIVA — dissolve o sulfato
    (solúvel) antes da emenda, recuperando Ca/S como nutriente e evitando
    o pico de acidez no solo cultivável.
    """

    sulfate_warn_pct: float = 5.0        # % soma sulfatos -> veio provável
    acid_marker_min_pct: float = 0.5     # jarosita/akaganeita -> água ácida

    SULFATE_MINERALS = ("GYPSUM", "ANHYDRITE", "BASSANITE", "JAROSITE")
    ACID_MARKERS = ("JAROSITE", "AKAGANEITE")

    def classify(self, mineralogy: Dict[str, float]) -> Dict[str, object]:
        """mineralogy: {MINERAL: wt%} de uma amostra CheMin (ou estimada)."""
        sulf = sum(mineralogy.get(m, 0.0) for m in self.SULFATE_MINERALS)
        acid = sum(mineralogy.get(m, 0.0) for m in self.ACID_MARKERS)
        is_vein = sulf >= self.sulfate_warn_pct
        acid_water = acid >= self.acid_marker_min_pct
        return {
            "sulfate_pct": round(sulf, 2),
            "acid_markers_pct": round(acid, 2),
            "is_sulfate_vein": is_vein,
            "acid_water_marker": acid_water,
            "requires_selective_leach": bool(is_vein or acid_water),
            "leach_recover": {"Ca_kg_per_kg": round(sulf * 0.0023, 4),  # CaSO4 ~23% Ca
                              "S_kg_per_kg": round(sulf * 0.0019, 4)},
        }


class RegolithProcessor:
    """Processa regolito marciano: nutrientes + remoção de tóxicos/abrasivos."""

    def __init__(self) -> None:
        self.magnetic_separator = MagneticSeparator()
        self.acid_leaching = AcidLeaching()
        self.ion_exchange = IonExchange()
        self.vein_classifier = SulfateVeinClassifier()

    def process(self, raw_regolith_kg: float, composition: Dict[str, float],
                fe2o3_frac: float = 0.05,
                mineralogy: Dict[str, float] | None = None) -> Dict[str, object]:
        """Ciclo completo: classifica -> moagem -> magnética -> lixiviação -> NPK.

        Se mineralogy (CheMin-like {MINERAL: wt%}) é fornecida, a amostra é
        classificada ANTES: veios de sulfato / marcadores de água ácida
        recebem lixiviação seletiva (recupera Ca+S) antes do ciclo geral.
        Dados reais: ~2/3 das amostras de Gale são veios (2026-09-28).
        """
        classification = None
        recovered = {"Ca": 0.0, "S": 0.0}
        if mineralogy is not None:
            classification = self.vein_classifier.classify(mineralogy)
            if classification["requires_selective_leach"]:
                # lixiviação seletiva: dissolve sulfato solúvel e recupera Ca/S
                recovered["Ca"] = raw_regolith_kg * classification["leach_recover"]["Ca_kg_per_kg"]
                recovered["S"] = raw_regolith_kg * classification["leach_recover"]["S_kg_per_kg"]
        # 1. moagem (proxy: 100% do material segue)
        powdered = raw_regolith_kg
        # 2. separação magnética
        mag = self.magnetic_separator.separate(powdered, fe2o3_frac)
        # 3. lixiviação ácida
        nutrients = self.acid_leaching.extract(mag["remainder_kg"], composition)
        # 4. troca iônica
        balanced = self.ion_exchange.balance(nutrients, {"N": 1.0, "P": 1.0, "K": 1.0})
        return {
            "fertilizer": balanced,
            "fe_removed_kg": mag["fe_removed_kg"],
            "processed_kg": mag["remainder_kg"],
            "vein_classification": classification,
            "recovered_secondary_kg": recovered if mineralogy is not None else None,
            "notes": ("veio de sulfato: lixiviação seletiva aplicada"
                      if (classification and classification["requires_selective_leach"])
                      else "regolito processado — aguarda gate is_safe (percloratos)"),
        }
