"""Mars Synthesis Watch — MoE-guide autowatch da estação (Phase56 marciano).

Réplica do mecanismo canônico de scripts/analysis/phase56_gap_autowatch.py
(pressão de gap + tendência + loop autônomo de eventos) aplicado ao ambiente
marciano: monitora LACUNAS de conhecimento por superfície de dados
(astrofísica/radiação, microbiologia, geologia/solo, clima, estrutura...),
cruza topologicamente os elementos e análises (mesh do mars_cross_layer) e
gera SÍNTESES novas — pontes explicativas que nenhum módulo isolado produz.

Como no OmniMind (Qdrant + autowatch), a estação "escava" qualquer dado e
cruza saberes para gerar novas sínteses — mas com os dados EXPERIMENTAIS
do ambiente: REMS/MOLA/SEIS/APXS + sensores + evolução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MarsGapWatch:
    """Monitora gaps por superfície (estilo phase56: h2/m1/m3 + ingest + crossmap).

    Pressão do gap = peso dos sinais de carência:
    - dados ausentes (ingest não-ok)
    - correlações fracas com o restante (crossmap não-ok)
    - síntese pendente (nunca gerou ponte explicativa)
    """

    @staticmethod
    def gap_pressure(dataset_ok: bool, crossmap_ok: bool, synthesis_ok: bool) -> float:
        """0.0 (resolvido) a 1.0 (crítico)."""
        score = 0.0
        if not dataset_ok:
            score += 0.5
        if not crossmap_ok:
            score += 0.3
        if not synthesis_ok:
            score += 0.2
        return round(score, 2)

    def watch(self, surfaces: Dict[str, Dict]) -> Dict:
        """surfaces: {id: {dataset_ok, crossmap_ok, synthesis_ok, label}}."""
        out = {}
        for sid, s in surfaces.items():
            p = self.gap_pressure(s.get("dataset_ok", False),
                                  s.get("crossmap_ok", False),
                                  s.get("synthesis_ok", False))
            out[sid] = {"label": s.get("label", sid), "pressure": p,
                        "status": "crítico" if p >= 0.7 else ("atento" if p >= 0.3 else "ok")}
        return out

    @staticmethod
    def effective_amci(nominal_amci: float, water_buffer_frac: float,
                       energy_level: float,
                       emergent_gain: float = 0.0) -> float:
        """AMCI efetivo = nominal × penalidade_água × penalidade_energia ×
        bônus de eficiência emergente (P3/P4).

        Contrato MARS: nominal × (0.85+0.15·p_água) × (0.85+0.15·p_energia).
        Extensão 2026-09-28: traços emergentes reduzem o custo energético
        real (luz-equivalente 1.84×) — o bônus entra como multiplicador
        limitado a +5% (conservador; o ganho já está na energia medida).
        """
        p_water = 0.85 + 0.15 * min(1.0, max(0.0, water_buffer_frac))
        p_energy = 0.85 + 0.15 * min(1.0, max(0.0, energy_level))
        bonus = 1.0 + min(0.05, max(0.0, emergent_gain))
        return round(nominal_amci * p_water * p_energy * bonus, 4)


@dataclass
class MarsSynthesisEngine:
    """Gera sínteses novas cruzando topologicamente as superfícies correlacionadas."""

    SYNTHESIS_TEMPLATES: Dict[str, str] = field(default_factory=lambda: {
        "excavation_ice_evolution": (
            "A escavação profunda expõe gelo ({ice_corr:.2f}) e perclorato no regolito; "
            "a água do gelo sustenta a pressão seletiva que empurra a tolerância ao "
            "perclorato ({evo_corr:.2f}) — a máquina cria o nicho que a seleciona."),
        "hygiene_evolution": (
            "A higiene aprendida ({hyg_corr:.2f}) reduz contaminação cruzada enquanto a "
            "evolução perclorato avança — biossegurança e mutagênese dirigida operam "
            "em ciclos acoplados, não em conflito."),
        "climate_growth": (
            "O clima real (REMS) modula o crescimento ({clim_corr:.2f}); a estufa "
            "amortece a variabilidade — a máquina é o gradiente entre Marte e Terra."),
        "soil_microbiome": (
            "A geoquímica do solo ({soil_corr:.2f}) determina a diversidade microbiana; "
            "a fertilidade é função do regolito processado + emenda orgânica (70:30) — "
            "o solo marciano não é estéril, é sub-alimentado."),
        "emergent_traits": (
            "Os traços emergentes acoplam-se à máquina: o ritmo circadiano entranha "
            "no sol de 24h39 ({circ_corr:.2f}) e a fotossíntese sincroniza ao ciclo "
            "elétrico ({symb_corr:.2f}) — a estação não hospeda a vida, ela co-evolui "
            "com ela (nicho máquina-planta)."),
        "geochem_sulfate": (
            "Os dados APXS reais ({so3_cao:.2f}) mostram SO3 acoplado a CaO — gesso "
            "(CaSO4) é o sulfato dominante do regolito local; a estratigrafia de "
            "elevação ({so3_elev:.2f}) marca a transição basáltico->sulfatos que o "
            "processador de regolito deve tolerar (lixiviação seletiva)."),
    })

    def synthesize(self, mesh: Dict, watch: Dict) -> List[Dict]:
        """Cruza arestas do mesh com gaps do watch e gera sínteses."""
        edges = {frozenset((e["a"], e["b"])): e["corr"] for e in mesh.get("edges", [])}
        out = []
        for template_id, template in self.SYNTHESIS_TEMPLATES.items():
            # mapeia template -> pares de superfícies necessários
            needs = {
                "excavation_ice_evolution": [("excavation_depth", "excavation_ice"),
                                             ("evolution_perchlorate", "excavation_depth")],
                "hygiene_evolution": [("hygiene", "evolution_perchlorate")],
                "climate_growth": [("rems_climate", "greenhouse_sensors")],
                "soil_microbiome": [("soil_geochem", "microbiome")],
                "emergent_traits": [("circadian_rhythm", "greenhouse_sensors"),
                                    ("machine_symbiosis", "resources")],
                "geochem_sulfate": [("apxs_so3", "apxs_cao"),
                                    ("apxs_so3", "apxs_elevation")],
            }.get(template_id, [])
            corrs = [edges.get(frozenset(p), 0.0) for p in needs]
            if any(abs(c) < 0.25 for c in corrs):
                continue  # sem correlação suficiente, não sintetiza
            kwargs = {}
            if template_id == "excavation_ice_evolution":
                kwargs = {"ice_corr": corrs[0], "evo_corr": corrs[1]}
            elif template_id == "hygiene_evolution":
                kwargs = {"hyg_corr": corrs[0]}
            elif template_id == "climate_growth":
                kwargs = {"clim_corr": corrs[0]}
            elif template_id == "soil_microbiome":
                kwargs = {"soil_corr": corrs[0]}
            elif template_id == "emergent_traits":
                kwargs = {"circ_corr": corrs[0], "symb_corr": corrs[1]}
            elif template_id == "geochem_sulfate":
                kwargs = {"so3_cao": corrs[0], "so3_elev": corrs[1]}
            gaps = {sid: w["status"] for sid, w in watch.items()
                    if w["status"] != "ok"}
            out.append({"synthesis_id": template_id,
                        "synthesis": template.format(**kwargs),
                        "correlations": corrs,
                        "open_gaps": gaps})
        return out
