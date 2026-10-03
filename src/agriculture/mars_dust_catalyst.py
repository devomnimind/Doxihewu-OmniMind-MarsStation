"""Mars Dust Catalyst — a estação como catalisadora de poeira.

A poeira marciana não é só desgaste — é insumo eletrostático e magnético.

Dados físicos (NASA/APXS/rovers):
  - diâmetro ~2.7 µm (~4% de um fio de cabelo) — respirável, aderente
  - TODA a poeira aérea é magnética (alvos magnéticos dos rovers capturam
    ~100% — compósitos com maghemita γ-Fe2O3) -> separação magnética da
    poeira é MAIS eficiente que no solo
  - carga triboelétrica em dust devils/tempestades; breakdown do ar marciano
    ~20-30 kV/m (vs ~3 MV/m na Terra) — o campo eletrostático é REAL e forte
  - composição média (wt%): SiO2 ~43, FeO(T) ~18.5, SO3 ~7.5, Al2O3 ~10,
    MgO ~8.5, CaO ~6.5, TiO2 ~1, Cl ~0.6, ClO4 ~0.5-0.7 (tóxico!)
  - tóxico p/ humanos: perclorato (tireoide) + sílica respirável + metais
    -> o que é tóxico a gente transforma: ClO4- vira O2 (dismutase microbiana
    dos genes da arca), sílica vira vidro, sulfato vira gesso/construção

Cadeia (ambiente -> máquina -> recurso -> corpo):
  vento/tempestade (REMS) -> DEPOSIÇÃO + captura ativa
    [EDS]  Electrodynamic Dust Shield — eletrodos pulsados nas superfícies:
           limpa painéis/óptica (reduz o desgaste do StationBody) E recolhe
           a poeira varrida em hopper — o escudo vira coletor
    [ESP]  precipitador eletrostático nas entradas de ar do habitat/estufa:
           protege seals/humanos, concentra PM2.7 marciano
    [MAG]  separador magnético — poeira 100% magnética -> concentrado Fe
    [AQ]   lavagem aquosa -> perclorato dissolvido -> PerchlorateChemistry
           / dismutase microbiana -> Cl- + 2 O2
  saídas: fe_oxide (metalurgia), silica (vidro de regolito), gypsum
          (construção/enxofre), o2_from_clo4 (o tóxico vira ar)

Mobilidade: almofadas eletroadesivas dos robôs — F = eps*V²*A/(2d²); no casco
304L dos ships (metal liso) funciona forte; a própria poeira carregada ajuda
a pré-carregar a interface. Análogo ao operário que escala prédio metálico
de luvas — aqui o ambiente EMPRESTA a carga.

Coupling com StationBody: EDS ativo reduz dust_sensitivity efetiva das
camadas (solar_arrays, optics_windows, radiators) — o perigo vira
mecanismo de reparo. Isso fecha o loop que a malha precisa ver:
dust (REMS) -> collected -> resources -> wear- (corpo).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ============ Especificação física da poeira ============

DUST_SPEC = {
    "diameter_um": 2.7,             # ~4% de fio de cabelo (70 µm)
    "respirable": True,             # inalável -> exige filtragem (toxicidade)
    "all_magnetic": True,           # captura ~100% nos alvos magnéticos dos rovers
    "triboelectric": True,          # carrega em dust devils / tempestades
    "breakdown_kv_m": (20.0, 30.0), # ar rarefeito -> breakdown ~25 kV/m
    "composition_wt": {             # APXS média de solos/poeira de Gale
        "SiO2": 0.43, "FeO_T": 0.185, "SO3": 0.075, "Al2O3": 0.10,
        "MgO": 0.085, "CaO": 0.065, "TiO2": 0.010, "Cl": 0.006,
        "ClO4": 0.006,              # ~0.5-0.7% — o tóxico que vira O2
    },
}

TOXICITY = {
    "perchlorate": "tireoide humana — mas = 2 O2 por ClO4- via dismutase",
    "respirable_silica": "silicose — vira vidro de regolito após captura",
    "fine_metals": "inflamação pulmonar — vira concentrado Fe/metalurgia",
}


# ============ Fluxo de deposição — REMS dirige ============

@dataclass
class DustFluxModel:
    """Deposição de poeira g/m²/sol.

    baseline de Gale ~ baixo; cresce com vento medido (REMS wind_h_speed),
    sazonalidade (Ls periélio = temporada de tempestades) e choques latentes
    (tempestades regionais/globais que a malha já modela)."""

    baseline_g_m2: float = 0.4      # deposição diária típica em Gale
    wind_gain: float = 0.35         # g/m² por m/s de vento acima do baseline

    def deposition(self, wind_m_s: float, latent: float, t: int) -> float:
        season = 1.0 + 0.6 * math.sin(2 * math.pi * t / 669.0)   # ciclo Ls
        storm = 1.0 + min(4.0, abs(latent))                      # choque = tempestade
        w = max(0.0, wind_m_s - 3.0) * self.wind_gain
        return round(self.baseline_g_m2 * season * storm + w, 4)


# ============ Coletores eletrostáticos ============

@dataclass
class ElectrodynamicDustShield:
    """EDS nas superfícies (painéis, óptica, radiadores): eletrodos pulsados
    varrem a poeira carregada para a borda — limpa E recolhe no hopper."""

    cleaning_eff: float = 0.92      # fração da deposição removida/ativada
    hopper_capture: float = 0.85    # da removida, quanto cai no hopper
    area_m2: float = 400.0          # área instrumentada (painéis + hull)

    def collect(self, deposition_g_m2: float) -> Dict[str, float]:
        lifted = deposition_g_m2 * self.area_m2 * self.cleaning_eff
        return {"cleaned_g": lifted,
                "hopper_g": lifted * self.hopper_capture,
                "panel_wear_relief": self.cleaning_eff}   # reduz dust_damage


@dataclass
class ElectrostaticPrecipitator:
    """ESP nas tomadas de ar do habitat/estufa — protege seals e humanos,
    concentra a fração respirável (o tóxico PM2.7)."""

    efficiency: float = 0.97
    intake_m3_sol: float = 12000.0  # renovação de ar da estação
    dust_mg_m3: float = 0.15        # concentração típica pós-válvulas

    def collect(self, flux_g_m2: float) -> float:
        # concentração sobe com tempestade: proxy da deposição
        mg = self.dust_mg_m3 * (1.0 + flux_g_m2) * self.intake_m3_sol
        return mg * self.efficiency / 1000.0    # -> g/sol capturado do ar


@dataclass
class ElectroadhesiveClimber:
    """Robôs escalando casco metálico (304L dos ships) com almofadas
    eletroadesivas — a poeira carregada do ambiente pré-carrega a interface."""

    pad_area_cm2: float = 900.0     # ~30x30 cm de almofada por robô
    voltage_v: float = 3000.0
    gap_um: float = 3.0             # interface (a poeira FICA no gap — ajuda)

    def adhesion_force_n(self, on_metal: bool = True) -> float:
        eps0, epsr = 8.854e-12, (3.5 if on_metal else 1.0)
        a = self.pad_area_cm2 * 1e-4
        d = self.gap_um * 1e-6
        f = 0.5 * eps0 * epsr * (self.voltage_v ** 2) * a / (d ** 2)
        return round(f, 1)          # ~centenas de N no casco — escala tranquila

    def climb_ok(self, robot_mass_kg: float = 60.0, on_metal: bool = True) -> bool:
        g_mars = 3.71
        return self.adhesion_force_n(on_metal) > robot_mass_kg * g_mars * 3  # x3 seg.


# ============ Fracionamento — o tóxico vira recurso ============

@dataclass
class DustFractionator:
    """Separa a poeira capturada em fluxos de recurso.

    A poeira aérea é TODA magnética -> o separador rende mais que no solo.
    A fração não-magnética carrega sílica + sulfatos; lavagem aquosa extrai
    o perclorato (solúvel) antes do restante virar vidro/construção."""

    magnetic_recovery: float = 0.92     # poeira aérea = compósito maghemita
    wash_efficiency: float = 0.90       # extração aquosa de ClO4- solúvel
    clo4_to_o2_yield: float = 0.77      # ClO4- + e- -> Cl- + 2 O2 (massa)

    def fractionate(self, dust_kg: float) -> Dict[str, float]:
        comp = DUST_SPEC["composition_wt"]
        fe_conc = dust_kg * comp["FeO_T"] * self.magnetic_recovery
        clo4 = dust_kg * comp["ClO4"] * self.wash_efficiency
        return {
            "fe_oxide_kg": round(fe_conc, 4),            # -> mars_metallurgy
            "silica_kg": round(dust_kg * comp["SiO2"], 4),  # -> vidro regolito
            "gypsum_kg": round(dust_kg * (comp["SO3"] + comp["CaO"]) * 0.5, 4),
            "perchlorate_kg": round(clo4, 4),
            "o2_from_clo4_kg": round(clo4 * self.clo4_to_o2_yield, 4),
            "bulk_fines_kg": round(dust_kg * 0.35, 4),   # carga p/ sinterização
        }


# ============ A estação catalisadora — integração por sol ============

@dataclass
class DustCatalystStation:
    """Transforma a poeira de ameaça em cadeia de suprimento.

    O output vira série da malha: recursos extraídos + alívio de desgaste
    + mobilidade — as pontes ambiente<->máquina<->corpo que faltavam."""

    flux: DustFluxModel = field(default_factory=DustFluxModel)
    eds: ElectrodynamicDustShield = field(default_factory=ElectrodynamicDustShield)
    esp: ElectrostaticPrecipitator = field(default_factory=ElectrostaticPrecipitator)
    climber: ElectroadhesiveClimber = field(default_factory=ElectroadhesiveClimber)
    frac: DustFractionator = field(default_factory=DustFractionator)

    def step_sol(self, wind_m_s: float, latent: float, t: int,
                 eds_active: bool = True) -> Dict[str, float]:
        dep = self.flux.deposition(wind_m_s, latent, t)
        eds = self.eds.collect(dep) if eds_active else {
            "cleaned_g": 0.0, "hopper_g": 0.0, "panel_wear_relief": 0.0}
        esp_g = self.esp.collect(dep)
        total_kg = (eds["hopper_g"] + esp_g) / 1000.0
        out = {"dust_deposited_g_m2": dep,
               "dust_collected_kg": round(total_kg, 4),
               "eds_panel_relief": eds["panel_wear_relief"],
               "esp_air_g": round(esp_g / 1000.0, 4)}
        out.update(self.frac.fractionate(total_kg))
        out["climb_uptime"] = 1.0 if self.climber.climb_ok() else 0.0
        return out

    def series(self, n_sols: int, wind_series: Optional[List[float]] = None,
               latent: Optional[List[float]] = None,
               eds_active: bool = True, seed: int = 5) -> Dict[str, List[float]]:
        """Roda a catalisação por n_sols. wind_series = REMS real (NaN->4 m/s)."""
        rng = random.Random(seed)
        out: Dict[str, List[float]] = {}
        for t in range(n_sols):
            w = (wind_series[t] if wind_series and t < len(wind_series)
                 and wind_series[t] == wind_series[t] else 4.0)
            lt = (abs(latent[t] - latent[t - 1]) if latent and t > 0
                  else 0.0)
            rec = self.step_sol(w, lt + rng.gauss(0, 0.05), t, eds_active)
            for k, v in rec.items():
                out.setdefault(k, []).append(v)
        return out

    def wear_relief_for(self, layer_name: str) -> float:
        """Quanto de desgaste por poeira a camada deixa de sofrer com EDS —
        multiplicador a aplicar no dust_sensitivity do StationBody."""
        relief = {"solar_arrays": self.eds.cleaning_eff,
                  "optics_windows": self.eds.cleaning_eff * 0.8,
                  "radiators": self.eds.cleaning_eff * 0.7,
                  "robot_joints": 0.15}        # juntas não têm EDS — só ESP do ar
        return relief.get(layer_name, 0.0)
