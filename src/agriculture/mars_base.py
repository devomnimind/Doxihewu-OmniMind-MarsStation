"""Mars Base Engineering — transporte, base e mecânica da estação.

Contexto real (2026-09-28): Starship Flight 14 — primeiro voo ORBITAL
da Starship v3 (Ship 41 + Booster): 33 Raptors no booster, perda de 1
motor na subida compensada por burn de motor único, 26 Starlink v3
deployados, splashdown Pacífico após ~3h. O veículo de ~100t que a
SpaceX projeta para Marte agora é uma máquina orbital real.

Cadeia modelada (conglomera, não escolhe):
  STARSHIP (transporte 100t classe)
    -> BASE (estruturas: pad, habitat, domo, tanques — materiais emergentes
             de mars_metallurgy, não alumínio importado)
    -> MECÂNICA (frota: escavadoras, haulers, rover, printer, braços)
    -> ISRU  (Sabatier+eletrólise = propelente de retorno + O2/água)
    -> BOOTSTRAP autocatalítico (massa local produzida cresce, massa
       importada por synod cai — métrica da Máquina-Árvore)

Todos os números são parâmetros de engenharia estimados — saídas de
modelo, não medições de hardware real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============ O veículo (voo real de hoje) ============

STARSHIP_V3 = {
    "name": "Starship v3 / Super Heavy",
    "payload_mars_surface_t": 100.0,     # classe nominal com refueling orbital
    "payload_leo_t": 100.0,
    "booster_engines": 33,
    "ship_engines": 6,
    "engine_out_tolerance": True,        # Flight 14 provou: subiu com 1 Raptor fora
    "propellant": "CH4 + LOX",           # metano -> Sabatier ISRU é o propelente nativo
    "return_propellant_t": 240.0,        # ordem de grandeza para retorno reduzido
    "note": "Flight 14 (2026-09-28): 1º voo orbital real; deploy 26 Starlink v3",
}


# ============ Fases de implantação ============

DEPLOY_PHASES = [
    {"phase": 0, "name": "cargo_primeiro",
     "ships": 2,
     "cargo": ["fission_units", "solar_field_kit", "isru_propellant_plant",
               "excavator_arm", "comms_relay"],
     "goal": "energia + propelente antes de qualquer tripulação"},
    {"phase": 1, "name": "infraestrutura",
     "ships": 2,
     "cargo": ["habitat_modules", "regolith_printer", "pressurized_rover",
               "greenhouse_frame", "extra_solar"],
     "goal": "estruturas locais começam — pad sinterizado, tanques, estufa"},
    {"phase": 2, "name": "expansao_autocatalitica",
     "ships": 4,
     "cargo": ["second_excavator", "metallurgy_furnace", "electrolysis_bank",
               "spare_parts_seed", "scientific_payload"],
     "goal": "refino local escala; fração importada cai a cada synod"},
]


# ============ Energia (o gargalo real da estação) ============

POWER_SOURCES: Dict[str, Dict] = {
    "fission_10kwe": {
        "kwe": 10.0, "mass_kg": 1500.0, "capacity_factor": 0.95,
        "note": "classe Kilopower NASA — potência noturna/poeirenta garantida"},
    "solar_array_m2": {
        "kwh_per_m2_sol": 1.0, "capacity_factor": 0.25,
        "note": "~400 W/m2 pico limpo, derating poeira+ângulo -> ~1 kWh/m2/sol"},
}


@dataclass
class PowerBudget:
    """Geração vs consumo — decide o throughput real da metalurgia.

    A refineria consome ~1846 kWh/t de regolito (mars_metallurgy).
    A potência disponível *é* o limite da estação — não a logística.
    """

    n_fission: int = 2
    solar_m2: float = 500.0
    sol_hours: float = 24.6

    def generation_kwh_sol(self) -> float:
        fiss = self.n_fission * POWER_SOURCES["fission_10kwe"]["kwe"] \
               * POWER_SOURCES["fission_10kwe"]["capacity_factor"] * self.sol_hours
        sol = self.solar_m2 * POWER_SOURCES["solar_array_m2"]["kwh_per_m2_sol"]
        return round(fiss + sol, 1)

    def refinery_throughput_t_sol(self, kwh_per_t: float = 1846.0) -> float:
        """Toneladas de regolito refinável por sol com a energia livre."""
        # reserva 30% para suporte de vida/estufa/bombas
        free = self.generation_kwh_sol() * 0.70
        return round(free / kwh_per_t, 3)

    def report(self) -> Dict:
        return {"n_fission": self.n_fission, "solar_m2": self.solar_m2,
                "kwh_per_sol": self.generation_kwh_sol(),
                "refinery_t_per_sol": self.refinery_throughput_t_sol()}


# ============ Máquinas — a mecânica da estação ============

MACHINE_FLEET: List[Dict] = [
    {"id": "excavator_arm", "role": "escava + amostra + classifica",
     "feed_surfaces": ["excavation", "soil_processing"],
     "t_per_sol": 20.0,
     "note": "braço de escavação — alimenta o gate do SulfateVeinClassifier"},
    {"id": "regolith_hauler", "role": "transporte escavação->processador",
     "feed_surfaces": ["excavation", "soil_processing"], "t_per_sol": 30.0},
    {"id": "pressurized_rover", "role": "amostragem remota / manutenção",
     "feed_surfaces": ["excavation", "resources"], "range_km_sol": 40.0},
    {"id": "regolith_printer", "role": "sinterização/geopolímero in-situ",
     "feed_surfaces": ["metallurgy"], "m3_per_sol": 4.0,
     "note": "imprime pads, muros e domo com material local"},
    {"id": "isru_prop_plant", "role": "CO2 -> O2 + Sabatier -> CH4",
     "feed_surfaces": ["resources", "energy"], "kg_o2_sol": 50.0,
     "note": "o propelente de retorno nasce do ar marciano"},
    {"id": "manipulator_pair", "role": "montagem estruturas braços/domo",
     "feed_surfaces": ["machine_symbiosis"]},
]


# ============ Estruturas — construídas com o que a estação produz ============

BASE_STRUCTURES: List[Dict] = [
    {"id": "landing_pad", "material": "ceramic_brick / geopolymer_cement",
     "from_metallurgy": ["sintering", "geopolymer"],
     "note": "plume de pouso destrói regolito solto — pad é prioridade 0"},
    {"id": "habitat_shell", "material": "mars_steel + basalt_fiber wrap",
     "from_metallurgy": ["carboreduction", "basalt_fiber"],
     "note": "pressão + blindagem de radiação com regolito empilhado"},
    {"id": "dome_greenhouse", "material": "basalt_glass + geopolymer frame",
     "from_metallurgy": ["basalt_glass", "geopolymer"],
     "note": "vidro basáltico opaco filtra UV; frame geopolímero sem cal"},
    {"id": "propellant_tanks", "material": "al_metal",
     "from_metallurgy": ["molten_salt_electrolysis"],
     "note": "tanques LOX/CH4 feitos do próprio solo"},
    {"id": "utility_trenches", "material": "sintered + regolith cover",
     "from_metallurgy": ["sintering"], "note": "cabos/água protegidos"},
]


# ============ Manifesto de uma Starship (100t bootstrap) ============

@dataclass
class StarshipManifest:
    """Monta o manifesto de 100t de uma nave cargo para a fase dada."""

    payload_t: float = STARSHIP_V3["payload_mars_surface_t"]

    MANIFEST_PHASE0: Dict[str, float] = field(default_factory=lambda: {
        "fission_units_x2": 3.0, "solar_field_kit": 12.0,
        "isru_propellant_plant": 25.0, "excavator_arm": 15.0,
        "comms_relay": 2.0, "rover": 8.0, "tools_spares": 10.0,
        "greenhouse_seed_kit": 5.0, "margin": 20.0})

    def check(self, manifest: Dict[str, float]) -> Dict:
        total = sum(manifest.values())
        return {"total_t": round(total, 2), "payload_t": self.payload_t,
                "fits": total <= self.payload_t,
                "margin_t": round(self.payload_t - total, 2)}

    def phase0(self) -> Dict:
        return self.check(dict(self.MANIFEST_PHASE0))


# ============ Bootstrap autocatalítico — a métrica da Máquina-Árvore ============

@dataclass
class BootstrapCurve:
    """Massa produzida localmente vs importada, por synod (26 meses ~ 780 sols).

    Se a estação refina `t_per_sol` e o throughput útil é `yield_frac`,
    a massa local acumulada por synod cresce; a fração importada cai —
    é a curva de independência: a árvore deixando de depender da raiz Terra.
    """

    t_per_sol: float = 0.34          # saída do PowerBudget.refinery_throughput_t_sol
    yield_frac: float = 0.60          # fração da massa refinada que vira estrutura/máquina
    sols_per_synod: int = 780
    import_t_synod0: float = 400.0    # 4 Starships x 100t iniciais

    def local_mass_synod(self, synod: int, growth: float = 0.5) -> float:
        """Produção local cresce porque máquinas novas nascem da própria massa."""
        t = self.t_per_sol * self.yield_frac * self.sols_per_synod
        return round(t * (1 + growth * synod), 1)

    def import_fraction(self, synod: int) -> float:
        local = self.local_mass_synod(synod)
        imported = self.import_t_synod0 / (synod + 1)
        return round(imported / (imported + local), 3)

    def sovereignty_report(self, n_synods: int = 6) -> List[Dict]:
        return [{"synod": s,
                 "local_produced_t": self.local_mass_synod(s),
                 "import_fraction": self.import_fraction(s)}
                for s in range(n_synods)]
