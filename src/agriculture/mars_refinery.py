"""Mars Refinery — a cadeia química completa da poeira catalisada.

Registry executável das reações (estequiometria real + eficiência + energia +
risco). O que o DustCatalystStation entrega (fe_oxide, silica, gypsum,
perchlorate, bulk_fines) vira PRODUTO aqui — e os riscos químicos viram
superfície de incidente para a malha.

Reações (balanço real, fontes marcianas ISRU):
  PERC_O2    Ca(ClO4)2 -> CaCl2 + 4 O2            400-500C, eff .90
             (Fe2O3/Fe3O4 catalisa e baixa p/ 300-400C)
  FE_REDUCE  Fe2O3 + 3 CO -> 2 Fe + 3 CO2         1500C alto-forno / DRI H2, eff .85
  SI_ELEC    SiO2 + 4e- -> Si + 2 O2-             CaCl2 fundido 1600C, eff .75
             (ânode libera O2 — subproduto respirável)
  GYP_CAL    CaSO4·2H2O -> CaSO4·0.5H2O + 1.5H2O  150-200C, eff .95
  S_CLAUS    CaSO4 + 2CH4 -> CaS -> H2S -> S      800-1000C Claus, eff .70
  GEOPOLY    SiO2+Al2O3+CaO+H2O -> cimento        20-80C (calor residual), eff .95
  FE_CLO4    Fe + Ca(ClO4)2 -> Fe(ClO4)2 + Ca     eletrólise — bateria redox
             de fluxo: líquido a -70C, 20-50 Wh/L — backup de noite/tempestade
  DETOX_FE0  ClO4- + 4Fe0 + 8H+ -> Cl- + 4Fe2+    nanopartículas Fe0: detox +
             Fe2+ quelato (fertilizante) + Cl- (sal)
  ZEOLITE    SiO2+Al2O3+NaOH -> zeólita           150-200C hidrotermal:
             adsorvente CO2/NH3/H2O + catalisador + troca iônica

Energia (por kg produto): Si 13-16 kWh, Fe 3-5, S 8-12, vidro 5-8,
gesso 0.5-1, O2 2-3, cimento 0.2-0.5. Orçamento: solar 1.2 kWh/painel/sol,
fissão Kilopower 10 kWe contínuo, biogás backup ~21 MWh.

Riscos (superfície de incidente): explosão ClO4+orgânico, incêndio O2,
Cl2 tóxico, silicose, H2S, CO — cada reação emite exposição; a malha
cruza risk_exposure com wear_/incident/latent_margin.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============ Reações — registry estequiométrico ============

@dataclass(frozen=True)
class Reaction:
    """Uma reação da refinaria — contrato completo."""
    key: str
    equation: str
    input_key: str               # fração da poeira que alimenta
    temp_c: float
    eff: float                   # rendimento real (com perdas)
    kwh_per_kg: float            # energia específica
    product_key: str
    product_yield_frac: float    # kg produto / kg insumo puro (teórico)
    hazard: str = ""             # risco dominante
    hazard_rate: float = 0.0     # prob. de evento por kg processado
    input_share: float = 1.0     # fração do estoque destinada a esta reação


REACTIONS: Dict[str, Reaction] = {
    "PERC_O2": Reaction(
        "PERC_O2", "Ca(ClO4)2 -> CaCl2 + 4 O2", "perchlorate_kg",
        450.0, 0.90, 2.5, "o2_kg", 128.0 / 239.0,
        hazard="explosão ClO4+orgânico / incêndio O2", hazard_rate=0.02,
        input_share=0.5),          # perclorato: metade p/ O2
    "FE_REDUCE": Reaction(
        "FE_REDUCE", "Fe2O3 + 3CO -> 2Fe + 3CO2", "fe_oxide_kg",
        1400.0, 0.85, 4.0, "fe_metal_kg", (2 * 55.85) / 159.7,
        hazard="CO tóxico / alto-forno", hazard_rate=0.01),
    "SI_ELEC": Reaction(
        "SI_ELEC", "SiO2 + 4e- -> Si + O2(ânode)", "silica_kg",
        1600.0, 0.75, 14.5, "si_metal_kg", 28.09 / 60.08,
        hazard="sal fundido 1600C", hazard_rate=0.008,
        input_share=0.6),          # sílica: 60% p/ Si, 40% p/ zeólita
    "GYP_CAL": Reaction(
        "GYP_CAL", "CaSO4.2H2O -> CaSO4.0.5H2O + 1.5H2O", "gypsum_kg",
        175.0, 0.95, 0.75, "plaster_kg", 145.0 / 172.0,
        hazard="vapor H2O", hazard_rate=0.001, input_share=0.6),
    "S_CLAUS": Reaction(
        "S_CLAUS", "CaSO4 -> CaS -> H2S -> S (Claus)", "gypsum_kg",
        900.0, 0.70, 10.0, "sulfur_kg", 32.0 / 136.0,
        hazard="H2S tóxico (LD50 713ppm)", hazard_rate=0.02,
        input_share=0.4),          # gesso: 40% p/ enxofre
    "GEOPOLY": Reaction(
        "GEOPOLY", "SiO2+Al2O3+CaO+H2O -> cimento", "bulk_fines_kg",
        50.0, 0.95, 0.35, "cement_kg", 1.8,
        hazard="baixo — calor residual", hazard_rate=0.0005),
    "FE_CLO4": Reaction(
        "FE_CLO4", "Fe + Ca(ClO4)2 -> Fe(ClO4)2 bateria fluxo", "perchlorate_kg",
        25.0, 0.85, 1.0, "flow_battery_kg", 254.0 / 239.0,
        hazard="eletrólise ClO4", hazard_rate=0.01, input_share=0.2),
    "DETOX_FE0": Reaction(
        "DETOX_FE0", "ClO4- + 4Fe0 + 8H+ -> Cl- + 4Fe2+ + 4H2O", "perchlorate_kg",
        25.0, 0.95, 0.5, "fe2_fertilizer_kg", (4 * 55.85) / 99.0,
        hazard="baixo — detox", hazard_rate=0.001, input_share=0.3),
    "ZEOLITE": Reaction(
        "ZEOLITE", "SiO2+Al2O3+NaOH -> zeólita", "silica_kg",
        175.0, 0.80, 2.0, "zeolite_kg", 1.3,
        hazard="autoclave NaOH", hazard_rate=0.005, input_share=0.4),
}

ENERGY_SOURCES = {
    "solar_kwh_sol": 1.2,        # por painel 2m² (400Wp, irradiância Marte 590 W/m²)
    "kilopower_kwh_sol": 240.0,  # 10 kWe contínuo
    "fsp_kwh_sol": 960.0,        # 40 kWe contínuo
    "biogas_kwh_total": 21105.0, # estoque renovável (5 kWh/kg biomassa)
}


# ============ Reator — processa frações dentro do orçamento ============

@dataclass
class RefineryScheduler:
    """Decide o que processar por sol dentro do orçamento energético.

    Prioridade física: 1) O2/suporte-vida, 2) detox (segurança), 3) bateria,
    4) construção (geopolímero/gesso), 5) S/zeólita, 6) Si/Fe (caros)."""

    priority: tuple = ("PERC_O2", "DETOX_FE0", "FE_CLO4", "GEOPOLY",
                       "GYP_CAL", "S_CLAUS", "ZEOLITE", "FE_REDUCE", "SI_ELEC")

    def schedule(self, stocks_kg: Dict[str, float],
                 energy_budget_kwh: float) -> Dict[str, float]:
        """Retorna kg de insumo processado por reação neste sol."""
        plan = {}
        remaining = energy_budget_kwh
        local_stock = dict(stocks_kg)        # insumos disputados no mesmo sol
        for key in self.priority:
            rx = REACTIONS[key]
            avail = local_stock.get(rx.input_key, 0.0) * rx.input_share \
                if rx.input_share < 1.0 else local_stock.get(rx.input_key, 0.0)
            if avail <= 0 or remaining <= 0:
                continue
            max_by_energy = remaining / rx.kwh_per_kg
            kg = min(avail, max_by_energy)
            if kg >= 0.05:                     # batelada mínima física
                plan[key] = kg
                local_stock[rx.input_key] -= kg
                remaining -= kg * rx.kwh_per_kg
        return plan


@dataclass
class RefineryReactor:
    """Executa o plano: aplica estequiometria + eficiência + risco."""

    def run(self, plan: Dict[str, float], rng: random.Random) -> Dict[str, float]:
        out = {"products": {}, "byproducts": {}, "energy_kwh": 0.0,
               "risk_events": 0, "haz_exposure": 0.0}
        for key, kg in plan.items():
            rx = REACTIONS[key]
            out["products"][rx.product_key] = round(
                kg * rx.product_yield_frac * rx.eff, 4)
            out["byproducts"][f"{key}_loss"] = round(
                kg * (1 - rx.eff), 4)
            out["energy_kwh"] += kg * rx.kwh_per_kg
            if rng.random() < rx.hazard_rate * kg * 0.01:
                out["risk_events"] += 1
            out["haz_exposure"] += rx.hazard_rate * kg
        out["energy_kwh"] = round(out["energy_kwh"], 2)
        out["haz_exposure"] = round(out["haz_exposure"], 4)
        return out


# ============ A refinaria como superfície de sol ============

@dataclass
class MarsRefinery:
    """Consome a saída do DustCatalystStation, respeita o orçamento de
    energia do sol, produz e emite riscos — série completa p/ a malha."""

    scheduler: RefineryScheduler = field(default_factory=RefineryScheduler)
    reactor: RefineryReactor = field(default_factory=RefineryReactor)
    n_panels: int = 50              # 50 × 1.2 kWh/sol
    fission_kw: float = 10.0        # Kilopower

    def energy_budget(self, t: int, dust_flux: float) -> float:
        solar = self.n_panels * ENERGY_SOURCES["solar_kwh_sol"] * \
            max(0.2, 1.0 - 0.6 * min(dust_flux, 3.0) / 3.0)   # poeira corta solar
        return solar + self.fission_kw * 24.0

    def series(self, n_sols: int,
               dust_outputs: Optional[Dict[str, List[float]]] = None,
               latent: Optional[List[float]] = None,
               seed: int = 21) -> Dict[str, List[float]]:
        """Processa por sol. dust_outputs = saída do DustCatalystStation.series().
        Estoques acumulam — o que não processa hoje fica pro amanhã."""
        rng = random.Random(seed)
        stocks: Dict[str, float] = {}
        out: Dict[str, List[float]] = {}
        inc = [0.0] if not latent else [0.0] + [
            abs(latent[i] - latent[i - 1]) for i in range(1, len(latent))]
        for t in range(n_sols):
            # entrega do dia
            if dust_outputs:
                for k, v in dust_outputs.items():
                    if k.endswith("_kg") and t < len(v):
                        stocks[k] = stocks.get(k, 0.0) + max(0.0, v[t])
            dep = (dust_outputs or {}).get("dust_deposited_g_m2", [1.0])
            dflux = dep[t] if t < len(dep) else 1.0
            plan = self.scheduler.schedule(stocks, self.energy_budget(t, dflux))
            for key, kg in plan.items():           # consome estoque
                stocks[REACTIONS[key].input_key] -= kg
            rec = self.reactor.run(plan, rng)
            rec["energy_budget"] = round(self.energy_budget(t, dflux), 1)
            rec["stockpile_kg"] = round(sum(stocks.values()), 2)
            rec["latent_shock"] = inc[t] if t < len(inc) else 0.0
            for k, v in rec.items():
                if isinstance(v, dict):
                    for pk, pv in v.items():
                        out.setdefault(f"ref_{pk}", []).append(pv)
                else:
                    out.setdefault(f"ref_{k}", []).append(v)
        return out

    def full_balance(self, dust_kg: float) -> Dict:
        """Balanço de massa estático (o relatório do usuário, verificado):
        para uma batelada de poeira, produtos teóricos vs reais."""
        comp_in = {"perchlorate_kg": dust_kg * 0.006,
                   "fe_oxide_kg": dust_kg * 0.185 * 0.92,
                   "silica_kg": dust_kg * 0.43,
                   "gypsum_kg": dust_kg * 0.07,
                   "bulk_fines_kg": dust_kg * 0.35}
        rng = random.Random(0)
        plan = {k: comp_in[r.input_key] * r.input_share
                for k, r in REACTIONS.items()
                if comp_in.get(r.input_key, 0) > 0}
        rec = self.reactor.run(plan, rng)
        # eficiência da cadeia de POEIRA: só produtos cujo insumo é a fração
        # coletada (yield<=1). Cimento/Fe2+/bateria trazem reagentes de fora.
        dust_chain = sum(v for k, v in rec["products"].items()
                         if any(r.product_key == k and r.product_yield_frac <= 1.0
                                for r in REACTIONS.values()))
        rec["dust_chain_efficiency"] = round(
            dust_chain / max(sum(plan.values()), 1e-9), 3)
        rec["plan_kg"] = {k: round(v, 2) for k, v in plan.items()}
        return {"input": comp_in, **rec}
