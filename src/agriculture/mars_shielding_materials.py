"""Mars Shielding Materials + Boundary Organs — seleção de material de
blindagem UV/radiação e superfícies de inalação/airlock na malha.

Duas frentes, uma lei comum: o ambiente só chega ao corpo atravessando
superfícies — e toda superfície é ela mesma um corpo que degrada.

1) ShieldStack / select_shielding — pilha de blindagem por camada material.

   A física honesta do UV marciano: qualquer película opaca de ~mm zera
   UV-ABC; a questão real é (a) superfícies TRANSMISSIVAS (óptica,
   coverglass) e (b) a blindagem como ela mesma — polietilena é a melhor
   atenuação de GCR por massa (H-rich) mas fotodegrada sob UV direto, por
   isso precisa viver SOB uma pele opaca (regolito sinterizado, tecido de
   basalto). Seleção = problema de ordem + orçamento, não de quantidade.

   Âncoras (ordens de grandeza, literatura):
     - REMS UVS: UV-ABC ~ 0,03-0,04 W/m² em Gale (já no env do sim).
     - GCR: meia-atenuação ~10-15 g/cm² para água/PE; ~25-35 g/cm² para
       regolito (Hassel/Zeitlin; alta-Z piora por spalação).
     - PE fotodegrada: perda de tenacidade após ~1-2 anos UV marciano
       desprotegido (UV stabilizer estende; assumido aqui como decaimento).
     - Regolito sinterizado ~1600 kg/m³ (mesmo número do SurfaceOrgan).

2) AirlockOrgan + superfícies de inalação — o ar compartilhado como
   superfície do corpo.

   Cada sorteio EVA: ciclo de pressão (fadiga das vedações — mesma física
   Coffin-Manson das camadas) + ingresso de poeira aderida ao traje
   (análogo Apollo: dezenas de gramas por sorteio). Fração transfere à
   cabine; o filtro do ECLSS remove com eficiência que decai com carga.
   Poeira de Gale ~0,6 wt% ClO4 — a dose inalada de perclorato é o vetor
   de saúde documentado (toxicidade tireoidiana). Saídas:
     - airlock_seal_fatigue   (alimenta wear de seals_joints)
     - cabin_dust_mg_m3       (superfície de inalação — a malha lê)
     - eclss_filter_load      (alimenta wear de eclss_loop)
     - crew_clo4_inhaled_ug   (dose-proxy por sol, tripulação nominal)

   Integração: o órgão NÃO cria MaterialLayer novas — o selo do airlock É
   seals_joints, o filtro É eclss_loop. Acrescenta termos de dano às
   camadas existentes: comparabilidade de body_integrity preservada.

Decisão de calibração (mesmo regime do SurfaceOrgan): ordens de grandeza
ancoradas em literatura, não precisão nominal. O que o módulo entrega é
a CADEIA (sorteio -> ingresso -> carga de filtro -> dose), não a fração
exata de cada elo.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============ 1) Seleção de material de blindagem ============

@dataclass(frozen=True)
class ShieldMaterial:
    """Um material de blindagem — massa vs atenuação vs fabricabilidade.

    uv_opaque: a camada bloqueia UV-ABC se for exterior (películas opacas).
    rad_half_gcm2: espessura de meia-atenuação GCR em g/cm² (None ~ inerte).
    uv_self_decay: taxa de perda de função/sol se EXPOSTA ao UV direto
                 (0 = inerte; PE ~ 1/400 sols nominal desprotegido).
    fabricable: produzível por ISRU/cadeia local (senão: massa da Terra).
    """
    name: str
    density_gcm3: float
    rad_half_gcm2: float
    uv_opaque: bool
    uv_self_decay: float
    fabricable: bool
    notes: str = ""


SHIELD_MATERIALS: Dict[str, ShieldMaterial] = {
    # Película opaca fabricável — a pele que protege o H-rich por baixo.
    # Em módulos de densidade de regolito: 1600 kg/m³ = 1.6 g/cm³.
    "sintered_regolith": ShieldMaterial(
        "sintered_regolith", 1.6, 30.0, uv_opaque=True,
        uv_self_decay=0.0, fabricable=True,
        notes="do SurfaceOrgan/refinaria; também absorve abrasão"),
    # Tecido de basalto: intermediário, fabricável, alguma transmissão.
    "basalt_fabric": ShieldMaterial(
        "basalt_fabric", 1.0, 28.0, uv_opaque=True,
        uv_self_decay=2e-5, fabricable=True,
        notes="fibra de basalto — UV-sombra flexível, degrada lento"),
    # Geopolímero da cadeia de cimento (Si-O-Al), entre tijolo e tecido.
    "geo_polymer": ShieldMaterial(
        "geo_polymer", 1.4, 27.0, uv_opaque=True,
        uv_self_decay=0.0, fabricable=True,
        notes="estoque cement_geopolymer_kg do refinery"),
    # Polietilena: melhor attenuação GCR/kg (H-rich) — MAS fotodegrada;
    # só funciona sob uma pele opaca. Não fabricável in-situ cedo.
    "polyethylene": ShieldMaterial(
        "polyethylene", 0.94, 10.0, uv_opaque=False,
        uv_self_decay=2.5e-3, fabricable=False,
        notes="H-rich; exige pele opaca por cima — ordem importa"),
    # Water jacket: dual-use com o estoque; boa attenuação, auto-selante.
    "water_jacket": ShieldMaterial(
        "water_jacket", 1.0, 12.0, uv_opaque=True,
        uv_self_decay=0.0, fabricable=True,
        notes="estoque water_l do ECLSS — blindagem inventariada"),
}


@dataclass
class ShieldLayer:
    """Uma camada instalada: material + espessura. A ordem conta: a
    camada i=0 é a mais externa (exposta ao UV); as internas vivem sob
    sombra se houver qualquer opaca acima."""
    material: str
    thickness_cm: float
    wear: float = 0.0         # degradação funcional da própria camada
    earth_mass_kg: float = 0.0  # quanto veio da Terra (não fabricável)


@dataclass
class ShieldStack:
    """Pilha de blindagem sobre uma zona (m² de referência).

    attenuation(): transmissão efetiva UV e rad — produto das camadas,
    com a regra de sombra: camadas H-rich sob uma opaca preservam a
    atenuação rad sem pagar fotodegradação."""
    layers: List[ShieldLayer] = field(default_factory=list)

    def mass_kg_m2(self) -> float:
        return sum(SHIELD_MATERIALS[l.material].density_gcm3
                   * l.thickness_cm * 10.0 for l in self.layers)

    def uv_transmission(self) -> float:
        """Fração do UV-ABC que atravessa: 0 se houver qualquer camada
        opaca com wear < 1; senão 1 (nada bloqueia)."""
        for l in self.layers:
            m = SHIELD_MATERIALS[l.material]
            if m.uv_opaque and l.wear < 0.8:
                return 0.0
        return 1.0

    def rad_transmission(self) -> float:
        """Transmissão GCR: produto 2^(-areal/half) sobre as camadas
        vivas. Camada com wear=1 atenua zero."""
        t = 1.0
        for l in self.layers:
            m = SHIELD_MATERIALS[l.material]
            eff_cm = l.thickness_cm * max(0.0, 1.0 - l.wear)
            areal = m.density_gcm3 * eff_cm        # g/cm²
            t *= 2.0 ** (-areal / m.rad_half_gcm2)
        return t

    def _in_shadow(self, idx: int) -> bool:
        """A camada está sob sombra UV? (alguma opaca viva mais externa)"""
        return any(SHIELD_MATERIALS[self.layers[j].material].uv_opaque
                   and self.layers[j].wear < 0.8 for j in range(idx))

    def step_sol(self, env: Dict[str, float]) -> Dict[str, float]:
        """Degradação própria da pilha: fotodegradação só das camadas
        expostas ao UV direto (sem sombra opaca viva acima)."""
        uv = env.get("uv_abc_w_m2", 0.03)
        for i, l in enumerate(self.layers):
            m = SHIELD_MATERIALS[l.material]
            if m.uv_self_decay <= 0 or self._in_shadow(i):
                continue
            l.wear = min(1.0, l.wear + m.uv_self_decay
                         * (uv / 0.03))
        return {"shield_mass_kg_m2": round(self.mass_kg_m2(), 3),
                "shield_uv_trans": round(self.uv_transmission(), 4),
                "shield_rad_trans": round(self.rad_transmission(), 4),
                "shield_wear_mean": round(
                    sum(l.wear for l in self.layers)
                    / max(1, len(self.layers)), 5)}


def select_shielding(rad_target_trans: float,
                     mass_budget_kg_m2: float,
                     earth_mass_budget_kg: float = 0.0,
                     prefer_fabricable: bool = True) -> ShieldStack:
    """Seleção gulosa de pilha: satisfazer a meta de transmissão rad sob
    orçamento de massa — e proteger toda camada fotossensível com uma
    pele opaca por cima (regra de ordem).

    Estratégia: (1) pele opaca fina fabricável primeiro (UV-sombra é
    barata em massa), (2) camadas por melhor attenuação/kg até a meta,
    (3) reordenar: opacas para fora."""
    stack = ShieldStack()
    # passo 1: sombra opaca — 0.5 cm de sintered resolve o problema UV
    stack.layers.append(ShieldLayer("sintered_regolith", 0.5))
    # passo 2: guloso por attenuação/kg efetiva
    budget_left = mass_budget_kg_m2 - stack.mass_kg_m2()
    earth_left = earth_mass_budget_kg
    order = ["polyethylene", "water_jacket", "geo_polymer", "basalt_fabric",
             "sintered_regolith"]
    while stack.rad_transmission() > rad_target_trans and budget_left > 0:
        best, best_gain = None, 0.0
        for name in order:
            m = SHIELD_MATERIALS[name]
            if not m.fabricable and earth_left <= 0:
                continue
            # 1 kg/m² = 0.1 g/cm² areal (1000 g / 10⁴ cm²); o que
            # diferencia é o half-value (PE H-rich vence por massa)
            gain = 1.0 - 2.0 ** (-0.1 / m.rad_half_gcm2)
            if m.fabricable and prefer_fabricable:
                gain *= 1.05
            if gain > best_gain:
                best, best_gain = name, gain
        if best is None:
            break
        m = SHIELD_MATERIALS[best]
        step_cm = 0.1 / m.density_gcm3      # 1 kg/m² em cm
        stack.layers.append(ShieldLayer(best, step_cm,
                                        earth_mass_kg=0.0 if m.fabricable else 1.0))
        budget_left -= 1.0
        if not m.fabricable:
            earth_left -= 1.0
    # passo 3: reordenar — toda camada opaca vai para fora da fotossensível
    stack.layers.sort(key=lambda l: (
        0 if SHIELD_MATERIALS[l.material].uv_opaque else 1))
    # consolidar camadas irmãs do mesmo material (espessura soma)
    merged: List[ShieldLayer] = []
    for l in stack.layers:
        if merged and merged[-1].material == l.material:
            merged[-1].thickness_cm += l.thickness_cm
            merged[-1].earth_mass_kg += l.earth_mass_kg
        else:
            merged.append(ShieldLayer(l.material, l.thickness_cm,
                                      l.wear, l.earth_mass_kg))
    stack.layers = merged
    return stack


# ============ 2) AirlockOrgan — a superfície de respiração ============

@dataclass
class AirlockOrgan:
    """A fronteira pressurizada: ciclos, ingresso de poeira, dose inalada.

    sorties_per_sol: atividade EVA média (0.2 early -> 0.5 madura).
    Cada sorteio: 1 ciclo de pressão nos selos + dust_suit_kg aderido.
    Fração cabin_transfer entra na cabine; filtro remove com eficiência
    que decai com carga; carga excessiva vaza para a malha do corpo."""

    sorties_per_sol: float = 0.3
    dust_suit_kg: float = 0.012         # aderido por traje (~10g, análogo Apollo)
    cabin_transfer_frac: float = 0.15   # do airlock para dentro
    cabin_volume_m3: float = 900.0      # ~3 módulos grandes
    filter_baseline_eff: float = 0.985  # HEPA-análogo
    filter_max_load: float = 1.0        # saturação relativa
    filter_desorb_sol: float = 0.02     # troca/limpeza por sol (consumível)
    crew_size: int = 6
    breathing_m3_sol: float = 11.0      # ar respirado por pessoa-sol
    clo4_wt_frac: float = 0.006         # 0.6 wt% ClO4 no regolito de Gale

    # --- estado ---
    seal_fatigue: float = 0.0           # 0 novo -> 1 falha (Coffin-Manson)
    pressure_cycles: int = 0
    ingress_total_kg: float = 0.0
    cabin_dust_kg: float = 0.0          # estoque suspenso/depositado interno
    filter_load: float = 0.0            # 0 limpo -> 1 saturado
    crew_clo4_total_ug: float = 0.0     # dose acumulada (proxy)
    _sol: int = 0

    def step_sol(self, env: Dict[str, float], latent: float,
                 rng: random.Random,
                 sorties: Optional[int] = None) -> Dict[str, float]:
        self._sol += 1
        wind_ms = env.get("wind_speed_ms", 4.0)
        dust_flux = env.get("dust_flux", 1.0)
        clo4 = env.get("perchlorate_wt", 0.6) * 0.01  # wt% -> fração

        # sorteios do sol — Poisson sobre a taxa de atividade, mais em
        # dias de missão externa (mineração construção) menos em tempestade
        lam = self.sorties_per_sol * (1.0 if dust_flux < 2.5 else 0.3)
        n = sorties if sorties is not None else sum(
            1 for _ in range(8) if rng.random() < lam / 8.0)
        self.pressure_cycles += n

        # fadiga do selo: Coffin-Manson simplificado no ΔP do ciclo
        # (101 kPa cabine -> ~0.6 kPa fora); ~10^4 ciclos vida nominal
        seal_delta = n * 1.2e-4 * (1.0 + 0.3 * max(0.0, latent))
        self.seal_fatigue = min(1.0, self.seal_fatigue + seal_delta)

        # ingresso: poeira aderida por traje, escalada pelo ambiente do dia
        ingress_kg = n * self.dust_suit_kg * min(4.0, 0.5 + dust_flux
                                                 * (1 + wind_ms / 20.0))
        to_cabin = ingress_kg * self.cabin_transfer_frac
        self.ingress_total_kg += ingress_kg
        self.cabin_dust_kg += to_cabin

        # filtro ECLSS: eficiência cai com carga; o que não é retido fica
        eff = self.filter_baseline_eff * max(0.2, 1.0 - self.filter_load)
        retained = self.cabin_dust_kg * eff * 0.5   # turn-over fracional/sol
        self.cabin_dust_kg -= retained
        self.filter_load = min(self.filter_max_load,
                               self.filter_load + retained * 0.02)
        # manutenção consome consumível — devolve capacidade
        self.filter_load = max(0.0, self.filter_load - self.filter_desorb_sol)
        # deposição natural interna (assenta em superfícies)
        self.cabin_dust_kg *= 0.85

        # dose inalada: concentração x ar respirado x fração ClO4
        conc_mg_m3 = self.cabin_dust_kg * 1e6 / self.cabin_volume_m3
        inhaled_ug = (conc_mg_m3 * self.breathing_m3_sol * self.crew_size
                      * clo4 * 1e3)
        self.crew_clo4_total_ug += inhaled_ug

        return {
            "airlock_sorties": n,
            "airlock_cycles_total": self.pressure_cycles,
            "airlock_seal_fatigue": round(self.seal_fatigue, 6),
            "airlock_ingress_kg": round(ingress_kg, 5),
            "airlock_ingress_total_kg": round(self.ingress_total_kg, 4),
            "cabin_dust_mg_m3": round(conc_mg_m3, 4),
            "eclss_filter_load": round(self.filter_load, 5),
            "crew_clo4_inhaled_ug": round(inhaled_ug, 3),
            "crew_clo4_total_ug": round(self.crew_clo4_total_ug, 1),
            # termos de dano para as camadas do corpo (somados fora)
            "_seal_wear_delta": round(seal_delta, 8),
            "_filter_wear_delta": round(self.filter_load * 5e-5, 8),
        }

    def neutrosophic(self) -> Dict[str, float]:
        f = min(1.0, self.seal_fatigue)
        return {"T": round(1.0 - f, 4), "I": 0.05, "F": round(f, 4)}
