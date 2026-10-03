"""Mars Unified Simulator — O Simulador Unificado e Contínuo da Estação Marciana.

Integração de todas as cadeias autônomas em um único ciclo unificado (sol a sol):
  1. Poeira & Atmosfera (EDS + ESP + desintoxicação de perclorato)
  2. Refinaria Química Estequiométrica (MarsRefinery: redução Fe, Si, geopolímeros, zeólitas)
  3. Mineração & Metalurgia de Larga Escala (Regolito bruto -> aço marciano, tijolos, H2SO4)
  4. Cadeia de Propelente & Sabatier (CO2 + H2 -> CH4 + H2O)
  5. Agricultura, Ecopoiese & Proteína Animal (Spirulina, batatas, trigo, Tenebrio molitor, n-caproato)
  6. Economia Circular & Fechamento ECLSS (UPA/BPA 98.5%, biochar pirólise NPK 95.9%)
  7. Corpo Material da Estação & Robótica (11 camadas StationBody + LaborEconomy humanoide)
  8. Comportamento Produtivo e Pontuação de Prontidão (AMCI, modos defensivos e surtos)

O daemon hospeda este simulador em seu coração: a cada ciclo, um sol é avançado,
todas as cadeias são pontuadas, e o estado vivo completo é persistido em checkpoint.
"""

from __future__ import annotations

import binascii
import math
import pickle
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from src.agriculture.mars_dust_catalyst import DustCatalystStation
from src.agriculture.mars_refinery import MarsRefinery, REACTIONS
from src.agriculture.mars_station_body import StationBody
from src.agriculture.sabatier_reactor import SabatierReactor
from src.agriculture.mealworm_protein import MealwormFarm
from src.agriculture.circular_economy import UrineBrineProcessor, NutrientCycleOptimizer
from src.agriculture.life_support_systems import IceElevatorSupply
from src.agriculture.mars_colossus import LaborEconomy, STATION_TIMELINE
from src.agriculture.mars_metallurgy import SECONDARY_STREAMS

try:
    from src.agriculture.mars_sovereign_regime import SMetaStation
except ImportError:
    try:
        from mars_sovereign_regime import SMetaStation
    except ImportError:
        SMetaStation = None

try:
    from src.agriculture.mars_station_mesh import StationMesh
except ImportError:
    try:
        from mars_station_mesh import StationMesh
    except ImportError:
        StationMesh = None


SOLS_PER_SYNOD = 780


@dataclass
class ExcavatorFleet:
    """Frota de escavadoras — órgão de colheita E banco de reparo da estação.

    Dupla natureza (voto da estação, auditoria v17 2026-10-03):

    - Produz regolito: capacidade = Σ(saúde × capacidade unitária);
    - É reserva de reparo: unidade esgotada DENTRO da estação é
      canibalizada → chassi vira ``spare_parts_kg`` (peças que viram
      horas-labor de reparo) + fração metálica ao estoque de Fe.
      O chassi só se perde de verdade em MISSÃO EXTERNA (incidente
      latente) — o único write-off real;
    - Era III+: a estação fabrica unidades novas do próprio Fe — a
      frota cresce da própria colheita (lógica Máquina-Árvore);
    - Energia: escavação+haul debita do mesmo ``power_margin × 24``
      que o órgão de superfície — energia é o veto real da expansão.

    O regolito minerado também carrega perclorato (0,6% m/m APXS):
    alimenta o estoque de ``perchlorate_kg`` e destrava a cadeia de
    desintoxicação em massa (antes limitada à deposição atmosférica).
    """
    capacity_kg_sol_per_unit: float = 85.0   # era I/II: rovers pequenos (4×85=340 baseline v17)
    capacity_era_iii_kg: float = 120.0       # era III: haulers médios fabricados localmente
    capacity_era_iv_kg: float = 170.0        # era IV: haulers industriais autônomos
    energy_kwh_per_kg: float = 0.02          # ~20 kWh/t escavação+haul [ENG]
    chassis_kg: float = 400.0                # massa recuperável por unidade
    cannibalize_frac: float = 0.7            # 70% do chassi vira peça útil
    chassis_fe_frac: float = 0.18            # casco metálico residual → fe_metal_kg
    build_cost_fe_kg: float = 350.0          # fabricar 1 unidade do próprio Fe
    max_units: int = 10                      # teto ~850 kg/sol na Era IV
    wear_per_kt: float = 0.015               # ~1 ano marciano de vida útil por unidade
    retire_health: float = 0.25              # abaixo disso a unidade é canibalizada
    mission_loss_prob: float = 0.10          # P(unidade perdida fora | incidente latente)
    parts_to_labor_h: float = 0.004          # 1 kg de peça ≈ 0.004 h-labor de reparo
    parts_labor_draw_kg: float = 30.0        # excedente p/ labor por sol — o banco
                                           # fica reservado p/ refurb/rebuild da frota
    refurb_parts_kg: float = 25.0            # peças p/ recondicionar 1 unidade (+0.2 saúde)
    refurb_health_gain: float = 0.2
    refurb_below: float = 0.9                # só recondiciona quem já desgastou
    rebuild_parts_kg: float = 350.0          # peças p/ remontar um chassi inteiro
    rebuilt_health: float = 0.6              # chassi remontado volta com saúde parcial
    unit_health: List[float] = field(default_factory=lambda: [1.0] * 4)
    spare_parts_kg: float = 0.0
    units_built: int = 0
    units_rebuilt: int = 0
    units_refurbished: int = 0
    units_cannibalized: int = 0
    units_lost_mission: int = 0

    @staticmethod
    def target_units(era: str) -> int:
        """Tamanho nominal da frota por era (capacidade de suporte da estação)."""
        return {"I_ancoragem": 4, "II_primeira_pele": 4,
                "III_tronco": 7, "IV_copa": 10}.get(era, 4)

    def unit_capacity_kg(self, era: str) -> float:
        """Capacidade por unidade cresce com a era — haulers cada vez
        maiores fabricados da própria produção de Fe da estação."""
        return {"III_tronco": self.capacity_era_iii_kg,
                "IV_copa": self.capacity_era_iv_kg}.get(
                    era, self.capacity_kg_sol_per_unit)

    def step_sol(self, era: str, energy_budget_kwh: float,
                 fe_stock_kg: float, latent: float,
                 rng: random.Random) -> Dict[str, float]:
        out = {"mined_kg": 0.0, "energy_kwh": 0.0, "built": 0,
               "rebuilt": 0, "refurbished": 0,
               "fe_spent_kg": 0.0, "cannibalized": 0, "lost": 0,
               "fe_recovered_kg": 0.0, "parts_recovered_kg": 0.0,
               "labor_bonus_h": 0.0}
        # 1) Auto-fabricação era III+: a frota cresce da própria colheita.
        #    Em todas as eras, o banco de peças remonta chassi até o
        #    tamanho nominal da era — a frota se recicla dentro da estação.
        target = self.target_units(era)
        if (era in ("III_tronco", "IV_copa")
                and len(self.unit_health) < self.max_units
                and fe_stock_kg >= self.build_cost_fe_kg * 4.0):
            self.unit_health.append(1.0)
            self.units_built += 1
            out["built"] = 1
            out["fe_spent_kg"] = self.build_cost_fe_kg
        if (len(self.unit_health) < target
                and self.spare_parts_kg >= self.rebuild_parts_kg):
            self.spare_parts_kg -= self.rebuild_parts_kg
            self.unit_health.append(self.rebuilt_health)
            self.units_rebuilt += 1
            out["rebuilt"] = 1
        # 2) Capacidade de colheita: saúde pondera a capacidade unitária;
        #    energia disponível é o veto real (mesmo pool do órgão de superfície)
        cap = sum(h * self.unit_capacity_kg(era) for h in self.unit_health)
        affordable = energy_budget_kwh / max(self.energy_kwh_per_kg, 1e-9)
        mined = max(0.0, min(cap, affordable))
        out["mined_kg"] = mined
        out["energy_kwh"] = mined * self.energy_kwh_per_kg
        # 3) Desgaste proporcional à carga manuseada (jitter por unidade)
        per_unit_kt = (mined / 1000.0) / max(1, len(self.unit_health))
        self.unit_health = [
            max(0.0, h - per_unit_kt * self.wear_per_kt * (0.7 + 0.6 * rng.random()))
            for h in self.unit_health
        ]
        # 4) Canibalização: unidade esgotada dentro da estação recicla —
        #    chassi vira banco de peças + casco metálico (NÃO é perda)
        kept = []
        for h in self.unit_health:
            if h < self.retire_health:
                self.units_cannibalized += 1
                out["cannibalized"] += 1
                parts = self.chassis_kg * self.cannibalize_frac
                self.spare_parts_kg += parts
                out["parts_recovered_kg"] += parts
                out["fe_recovered_kg"] += self.chassis_kg * self.chassis_fe_frac
            else:
                kept.append(h)
        self.unit_health = kept
        # 5) Recondicionamento: peças de unidades aposentadas restauram as
        #    remanescentes — a reciclagem financia a manutenção da frota
        for i, h in enumerate(self.unit_health):
            if (h < self.refurb_below
                    and self.spare_parts_kg >= self.refurb_parts_kg):
                self.unit_health[i] = min(1.0, h + self.refurb_health_gain)
                self.spare_parts_kg -= self.refurb_parts_kg
                self.units_refurbished += 1
                out["refurbished"] += 1
        # 6) Missão externa: incidente latente pode perder uma unidade —
        #    único write-off real de chassi
        if latent > 2.2 and self.unit_health and rng.random() < self.mission_loss_prob:
            self.unit_health.pop(rng.randrange(len(self.unit_health)))
            self.units_lost_mission += 1
            out["lost"] += 1
        # 7) Banco de peças → demanda de reparo: só um draw limitado por
        #    sol vira horas-labor — o resto financia refurbish/rebuild
        draw = min(self.spare_parts_kg, self.parts_labor_draw_kg)
        labor_bonus = draw * self.parts_to_labor_h
        self.spare_parts_kg -= draw
        out["labor_bonus_h"] = labor_bonus
        return out


@dataclass
class SoilWashPlant:
    """Usina fixa de lixiviação de perclorato — o complemento industrial da
    frota móvel. O ClO4- é solúvel em água: lavar solo a granel extrai o
    sal (que segue para a refinaria PERC_O2/DETOX) e devolve ``clean_soil``
    — substrato desintoxicado para a estufa, fechando a dupla produção da
    mesma cadeia (O2/fertilizante + solo arável).

    A capacidade é por era (piloto era II, industrial III/IV) — uma
    instalação de correia/contator contínuo, não rovers; sua matéria-prima
    é o solo ao redor da estação, não o regolito contado da frota.

    Água: o lixiviado recircula (``water_recycle_frac``); o débito líquido
    sai do reservatório. Energia: debitada do mesmo pool compartilhado
    ``power_margin × 24 × power_base_kw`` — a usina vota contra a frota,
    o forno e o EDS pelo mesmo orçamento.
    """
    throughput_era_ii_kg: float = 200.0     # piloto: contador de batelada
    throughput_era_iii_kg: float = 800.0    # industrial: correia contínua
    throughput_era_iv_kg: float = 6000.0    # madura: lixivia o entorno da estação
    clo4_wt: float = 0.006                  # 0,6% m/m (APXS)
    extract_eff: float = 0.90               # extração do sal no contator
    water_gross_l_per_kg: float = 0.4       # lixiviado bruto por kg de solo
    water_recycle_frac: float = 0.98        # recirculação do lixiviado
    energy_kwh_per_kg: float = 0.08         # correia+agitação+centrifuga
    soil_washed_total_t: float = 0.0

    def throughput_kg(self, era: str) -> float:
        return {"II_primeira_pele": self.throughput_era_ii_kg,
                "III_tronco": self.throughput_era_iii_kg,
                "IV_copa": self.throughput_era_iv_kg}.get(era, 0.0)

    def step_sol(self, era: str, energy_budget_kwh: float) -> Dict[str, float]:
        out = {"soil_kg": 0.0, "clo4_kg": 0.0, "clean_soil_kg": 0.0,
               "water_net_l": 0.0, "energy_kwh": 0.0}
        soil = self.throughput_kg(era)
        if soil <= 0.0:
            return out
        # energia é o veto real: a usina só processa o que o pool cobre
        soil = min(soil, energy_budget_kwh / self.energy_kwh_per_kg)
        if soil <= 0.0:
            return out
        clo4 = soil * self.clo4_wt * self.extract_eff
        self.soil_washed_total_t += soil / 1000.0
        out.update({
            "soil_kg": soil,
            "clo4_kg": clo4,
            "clean_soil_kg": soil * (1.0 - self.clo4_wt * self.extract_eff),
            "water_net_l": soil * self.water_gross_l_per_kg
                           * (1.0 - self.water_recycle_frac),
            "energy_kwh": soil * self.energy_kwh_per_kg,
        })
        return out


@dataclass
class StationUnifiedSimulator:
    """Simulador único de toda a estação: estado cumulativo, dinâmico e pontuado."""

    sol: int = 0
    seed: int = 42
    
    # Sub-sistemas acoplados
    dcs: DustCatalystStation = field(default_factory=DustCatalystStation)
    refinery: MarsRefinery = field(default_factory=MarsRefinery)
    body: StationBody = field(default_factory=StationBody)
    sabatier: SabatierReactor = field(default_factory=SabatierReactor)
    mealworm: MealwormFarm = field(default_factory=MealwormFarm)
    urine_proc: UrineBrineProcessor = field(default_factory=UrineBrineProcessor)
    nutrient_opt: NutrientCycleOptimizer = field(default_factory=NutrientCycleOptimizer)
    ice: IceElevatorSupply = field(default_factory=IceElevatorSupply)
    fleet: ExcavatorFleet = field(default_factory=ExcavatorFleet)
    soil_wash: SoilWashPlant = field(default_factory=SoilWashPlant)
    regime: Optional[SMetaStation] = field(
        default_factory=SMetaStation if SMetaStation else lambda: None)
    mesh: Optional[StationMesh] = field(
        default_factory=StationMesh if StationMesh else lambda: None)
    
    # Estoques acumulados (vivos)
    stocks: Dict[str, float] = field(default_factory=lambda: {
        "dust_raw_kg": 0.0,
        "fe_oxide_kg": 0.0,
        "silica_kg": 0.0,
        "gypsum_kg": 0.0,
        "perchlorate_kg": 0.0,
        "fe_metal_kg": 0.0,
        "silicon_metal_kg": 0.0,
        "cement_geopolymer_kg": 0.0,
        "sintered_bricks_kg": 0.0,
        "sulfuric_acid_kg": 0.0,
        "apatite_p_kg": 0.0,
        "fertilizer_npk_kg": 0.0,
        "ch4_fuel_kg": 0.0,
        "water_l": 5000.0,
        "o2_kg": 500.0,
        "spirulina_kg": 0.0,
        "potatoes_kg": 0.0,
        "wheat_kg": 0.0,
        "protein_animal_kg": 0.0,
        "n_caproate_kg": 0.0,
        "clean_soil_kg": 0.0,
        "regolith_mined_total_t": 0.0,
    })
    
    # Potência-base da estação (reator de fissão 100 kWe, per monografia):
    # power_margin [0,1] × 24 × power_base_kw = orçamento energético
    # diário em kWh — pool único disputado por frota, órgão e ECLSS.
    power_base_kw: float = 100.0
    # Histórico recente para telemetria (janela móvel)
    recent_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_len: int = 100
    
    def __post_init__(self):
        self._rng = random.Random(self.seed)
        # fix auditoria 2026-10-03: apply_dust_catalyst REMOVIDO do init —
        # mutação permanente de dust_sensitivity + SurfaceOrgan ativo =
        # dupla mitigação. O órgão é o mecanismo canônico de defesa de poeira.

    @property
    def synod(self) -> int:
        return self.sol // SOLS_PER_SYNOD

    @property
    def era(self) -> str:
        s = self.synod
        if s <= 3:
            return "I_ancoragem"
        elif s <= 8:
            return "II_primeira_pele"
        elif s <= 16:
            return "III_tronco"
        else:
            return "IV_copa"

    def active_fleet_robots(self) -> int:
        """Escalonamento da frota de robôs conforme a era e synod."""
        s = self.synod
        if s <= 3:
            return 40 + s * 10
        elif s <= 8:
            return 80 + (s - 4) * 20
        elif s <= 16:
            base = 200 + (s - 9) * 25
            if s >= 14: # Provisão dos 30 anos
                base += 100
            return base
        else:
            return min(720, 400 + (s - 17) * 32)

    def step(self, env: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Avança exatamente 1 sol na vida e operação da estação."""
        self.sol += 1
        current_sol = self.sol
        current_synod = self.synod
        era_name = self.era
        
        # 1. Ambiente Físico Marciano (REMS/InSight ou Sintético calibrado)
        if env is None:
            # Oscilação sazonal Ls e rajadas
            # round(...,6): quantiza a saída libm de math.sin — builds
            # Clang/GCC divergem no ULP e o erro não-arredondado explodia
            # caoticamente em 21k sols (~2% cross-env; água idêntica,
            # contadores raros divergiam 196↔224).
            season = round(math.sin(2 * math.pi * current_sol / 669.0), 6)
            base_wind = 4.2 + 1.5 * season + self._rng.gauss(0, 1.2)
            base_wind = max(0.5, base_wind)
            gust = base_wind * (1.3 + 0.3 * self._rng.random())
            
            # Tempestade de poeira ocasional (probabilidade maior no periélio)
            is_storm = (season > 0.4) and (self._rng.random() < 0.08)
            dust_dep = self.dcs.flux.deposition(base_wind, 2.5 if is_storm else 0.0, current_sol)
            
            env = {
                "wind_speed_ms": round(base_wind, 2),
                "wind_gust_ms": round(gust, 2),
                "dust_flux": round(dust_dep, 4),
                "air_temp_k": round(210.0 + 20.0 * season + self._rng.gauss(0, 5), 1),
                "ground_temp_delta": round(65.0 + 10.0 * abs(season), 1),
                "uv_abc_w_m2": round(0.035 * max(0.2, 1.0 - 0.5 * min(dust_dep, 4.0)/4.0), 4),
                "rad_msv_day": round(0.67 + 0.1 * self._rng.random(), 3),
                "perchlorate_wt": 0.6,
                "seismic_shock": 1.0 if self._rng.random() < 0.03 else 0.0
            }
        
        env = dict(env)  # não mutar o dict do chamador (power_margin é debitado abaixo)
        env["power_base_kw"] = self.power_base_kw  # pool energético: 100 kWe fissão
        wind = env.get("wind_speed_ms", 4.0)
        dust_dep = env.get("dust_flux", 1.0)
        seismic = env.get("seismic_shock", 0.0)
        # fix auditoria 2026-10-03: seismic (0/1) virava `latent` e nunca
        # cruzava o limiar 2.2 do incidente físico — o mecanismo estava
        # morto. Choque sísmico vira excursão latente real (×3: flag 1.0 ->
        # latent 3.0 > 2.2 com probabilidade 35%, igual ao driver series()).
        latent_shock = seismic * 3.0

        # Determinação do Modo Comportamental — S_meta resolve o regime
        # (metaestabilidade), a oportunidade decide o modo nominal.
        reg = None
        if self.regime is not None:
            reg = self.regime.step({
                "dust_flux": dust_dep,
                "wind_ms": wind,
                "o2_kg": self.stocks["o2_kg"],
                "water_l": self.stocks["water_l"],
                "body_integrity": 1.0 - sum(
                    l.wear for l in self.body.layers.values()
                ) / max(1, len(self.body.layers)),
                "compute_wear": self.body.layers["compute_core"].wear,
                "env_coverage": env.get("env_coverage", 1.0),
            })
        if reg and reg["mode_override"]:
            behavior_mode = reg["mode_override"]
        elif current_synod == 14 and (current_sol % SOLS_PER_SYNOD < 50):
            behavior_mode = "overhaul_refit"
        elif (self.stocks["potatoes_kg"] + self.stocks["wheat_kg"]) < 500.0 and current_sol >= 1500:
            behavior_mode = "agricultural_surge"
        elif self.stocks["fe_metal_kg"] < 1000.0:
            behavior_mode = "mining_surge"
        else:
            behavior_mode = "nominal_ecopoiesis"
            
        # 2. Cadeia 1: Captura de Poeira e Aerossóis (EDS + ESP)
        eds_active = True
        dust_step = self.dcs.step_sol(wind, seismic, current_sol, eds_active=eds_active)
        
        # Alimenta estoques brutos
        self.stocks["dust_raw_kg"] += dust_step["dust_collected_kg"]
        self.stocks["fe_oxide_kg"] += dust_step["fe_oxide_kg"]
        self.stocks["silica_kg"] += dust_step["silica_kg"]
        self.stocks["gypsum_kg"] += dust_step["gypsum_kg"]
        self.stocks["perchlorate_kg"] += dust_step["perchlorate_kg"]
        # Oxigênio liberado na lavagem aquosa / dismutase de perclorato
        self.stocks["o2_kg"] += dust_step["o2_from_clo4_kg"]
        
        # 3. Cadeia 2: Refinaria Química Estequiométrica (MarsRefinery)
        energy_budget = self.refinery.energy_budget(current_sol, dust_dep)
        ref_inputs = {
            # voto da estação 2026-10-03: perclorato minerado a granel
            # (frota, cadeia 3) passa a alimentar a refinaria — antes só o
            # fluxo atmosférico (dust×1.5) alimentava. Cap +60 kg/sol do
            # estoque a granel (frota + usina de lixiviação); o scheduler
            # de energia da refinaria segue sendo o gate real de throughput.
            "perchlorate_kg": min(self.stocks["perchlorate_kg"],
                                  dust_step["perchlorate_kg"] * 1.5
                                  + min(self.stocks["perchlorate_kg"], 60.0)),
            "fe_oxide_kg": min(self.stocks["fe_oxide_kg"], dust_step["fe_oxide_kg"] * 1.5),
            "silica_kg": min(self.stocks["silica_kg"], dust_step["silica_kg"] * 1.5),
            "gypsum_kg": min(self.stocks["gypsum_kg"], dust_step["gypsum_kg"] * 1.5),
            "bulk_fines_kg": dust_step["bulk_fines_kg"]
        }
        plan = self.refinery.scheduler.schedule(ref_inputs, energy_budget)
        ref_run = self.refinery.reactor.run(plan, self._rng)
        prods = ref_run["products"]
        # Conservação: o scheduler debitava só uma cópia local — o estoque
        # real nunca era debitado e crescia sem bound. O plano executado é
        # o consumo real por insumo.
        consumed_inputs: Dict[str, float] = {}
        for _rx_key, _kg in plan.items():
            _in_key = REACTIONS[_rx_key].input_key
            consumed_inputs[_in_key] = consumed_inputs.get(_in_key, 0.0) + _kg
        for _k, _kg in consumed_inputs.items():
            if _k in self.stocks:
                self.stocks[_k] = max(0.0, self.stocks[_k] - _kg)
        
        fe_reduced_ref_kg = prods.get("fe_metal_kg", 0.0)
        si_metal_kg = prods.get("si_metal_kg", 0.0)
        cement_ref_kg = prods.get("cement_kg", 0.0)
        plaster_kg = prods.get("plaster_kg", 0.0)
        zeolite_kg = prods.get("zeolite_kg", 0.0)
        o2_ref_kg = prods.get("o2_kg", 0.0)
        
        self.stocks["fe_metal_kg"] += fe_reduced_ref_kg
        self.stocks["silicon_metal_kg"] += si_metal_kg
        self.stocks["cement_geopolymer_kg"] += cement_ref_kg
        self.stocks["o2_kg"] += o2_ref_kg
        
        # 4. Cadeia 3: Mineração e Metalurgia de Regolito Bruto (frota viva)
        # voto da estação 2026-10-03: a taxa não é constante — ExcavatorFleet
        # é órgão de colheita E banco de reparo. Energia debitada do mesmo
        # pool power_margin×24 que o órgão de superfície usará depois;
        # unidade esgotada é canibalizada (peças→labor, casco→Fe); chassi só
        # se perde em missão externa; era III+ fabrica unidades do próprio Fe.
        fleet_res = self.fleet.step_sol(
            era_name,
            env.get("power_margin", 0.6) * 24.0 * self.power_base_kw,
            self.stocks["fe_metal_kg"], latent_shock, self._rng)
        regolith_sol_kg = fleet_res["mined_kg"]
        env["power_margin"] = max(
            0.0, env.get("power_margin", 0.6)
            - fleet_res["energy_kwh"] / (24.0 * self.power_base_kw))
        self.stocks["fe_metal_kg"] += fleet_res["fe_recovered_kg"]
        self.stocks["fe_metal_kg"] -= fleet_res["fe_spent_kg"]
        # perclorato do regolito minerado (0,6% m/m APXS) → cadeia a granel
        self.stocks["perchlorate_kg"] += regolith_sol_kg * 0.006
        self.stocks["regolith_mined_total_t"] += regolith_sol_kg / 1000.0

        # usina de lixiviação (era II+): solo a granel -> ClO4- p/ refinaria
        # + clean_soil (substrato desintoxicado). Energia do mesmo pool —
        # sobra de energia da frota alimenta a usina no mesmo sol.
        wash_res = self.soil_wash.step_sol(
            era_name,
            env.get("power_margin", 0.6) * 24.0 * self.power_base_kw)
        env["power_margin"] = max(
            0.0, env.get("power_margin", 0.6)
            - wash_res["energy_kwh"] / (24.0 * self.power_base_kw))
        self.stocks["perchlorate_kg"] += wash_res["clo4_kg"]
        self.stocks["clean_soil_kg"] += wash_res["clean_soil_kg"]
        self.stocks["water_l"] -= wash_res["water_net_l"]
        
        fe_raw_mined_kg = regolith_sol_kg * 0.19
        fe_metal_smelted_kg = fe_raw_mined_kg * 0.72 # Carboredução com CO
        sio2_mined_kg = regolith_sol_kg * 0.45
        bricks_sintered_kg = (sio2_mined_kg * 0.5) * 0.95
        geopoly_mined_kg = (sio2_mined_kg * 0.5) * 0.90
        h2so4_kg = (regolith_sol_kg * 0.10) * 0.4 * 1.53 # Ciclo Claus
        apatite_p_sol_kg = regolith_sol_kg * 0.009
        
        self.stocks["fe_metal_kg"] += fe_metal_smelted_kg
        self.stocks["sintered_bricks_kg"] += bricks_sintered_kg
        self.stocks["cement_geopolymer_kg"] += geopoly_mined_kg
        self.stocks["sulfuric_acid_kg"] += h2so4_kg
        self.stocks["apatite_p_kg"] += apatite_p_sol_kg
        
        # 5. Cadeia 4: Propelente & Reator Sabatier (CO2 + 4H2 -> CH4 + 2H2O)
        co2_feed_kg = 27.5 # Consumo atmosférico diário
        h2_feed_kg = 5.0   # Da eletrólise de água reciclada
        # fix auditoria 2026-10-03: a eletrólise do H2 é modelada — 2 H2O ->
        # 2 H2 + O2: 9 L de água e 8 kg O2 por kg de H2. Sem isso o Sabatier
        # criava água do nada (devolve ~22.5 L mas nunca debitava os 45 L).
        h2o_electrolyzed_l = h2_feed_kg * 9.0
        o2_electrolysis_kg = h2_feed_kg * 8.0
        self.stocks["water_l"] -= h2o_electrolyzed_l
        self.stocks["o2_kg"] += o2_electrolysis_kg
        sab_res = self.sabatier.process(co2_feed_kg, h2_feed_kg)
        
        self.stocks["ch4_fuel_kg"] += sab_res["ch4_kg"]
        self.stocks["water_l"] += sab_res["h2o_kg"]
        
        # 6. Cadeia 5: Agricultura, Ecopoiese e Proteína Animal
        # Spirulina: 20 kg/sol contínuo (fotossíntese primária)
        spirulina_sol_kg = 20.0
        self.stocks["spirulina_kg"] += spirulina_sol_kg
        self.stocks["water_l"] -= 16.0 # Consumo hídrico líquido da estufa
        self.stocks["o2_kg"] += 26.0   # Fotossíntese O2 líquido
        
        # Cultivos de estufa (após estabilização no sol 1500)
        potatoes_sol_kg = 0.0
        wheat_sol_kg = 0.0
        n_caproate_sol_kg = 0.0
        if current_sol >= 1500:
            potatoes_sol_kg = 45.0
            wheat_sol_kg = 30.0
            n_caproate_sol_kg = 0.024 * 0.95 * 1000.0 # ~22.8 kg/sol
            self.stocks["potatoes_kg"] += potatoes_sol_kg
            self.stocks["wheat_kg"] += wheat_sol_kg
            self.stocks["n_caproate_kg"] += n_caproate_sol_kg
            self.stocks["water_l"] -= 35.0
            self.stocks["o2_kg"] += 40.0
            
        # Proteína animal: Tenebrio molitor consumindo resíduos vegetais (15 kg casca/farelo)
        plant_residue_kg = 15.0 if current_sol >= 1500 else 5.0
        protein_animal_sol_kg = self.mealworm.protein_per_day(residue_kg_day=plant_residue_kg)
        self.stocks["protein_animal_kg"] += protein_animal_sol_kg
        
        # 7. Cadeia 6: Economia Circular & Fechamento ECLSS
        urine_l = 35.0 # Fluxo diário proporcional à biomassa/habitantes equivalentes
        urine_res = self.urine_proc.process(urine_l)
        self.stocks["water_l"] += urine_res["water_recovered_l"]
        
        # Otimizador de ciclo de nutrientes (pirólise biochar + digestão)
        nut_res = self.nutrient_opt.step(biomass_residual_kg=plant_residue_kg)
        self.stocks["fertilizer_npk_kg"] += nut_res["recovered_kg"]

        # Cadeia de gelo ISRU (auditoria v17): sem ela a estação é consumidora
        # líquida ~37 L/sol (-791 kL em 21.060 sols). Escala por era:
        # I elevador habitat 2.5 L/sol -> II ISRU inicial 25 -> III/IV
        # industrial 90/120 L/sol (DRA: gelo subsuperficial ~100 kg/sol).
        self.ice.flow_l_per_sol = {
            "I_ancoragem": 2.5, "II_primeira_pele": 25.0,
            "III_tronco": 90.0, "IV_copa": 120.0}[era_name]
        ice_water_l = self.ice.step(self.stocks["water_l"])
        self.stocks["water_l"] += ice_water_l
        
        # 8. Cadeia 7: Corpo Material da Estação & Robótica
        n_robots = self.active_fleet_robots()
        labor_econ = LaborEconomy(n_robots=n_robots)
        # Demanda de reparo (voto da estação): chassi canibalizado dentro
        # da estação vira banco de peças → horas-labor efetivas extras.
        net_labor_h = labor_econ.net_hours_sol() + fleet_res["labor_bonus_h"]
        
        # Se for marco de provisão de meia-vida (Synod 14, sol ~10920), alívio de revisão
        if current_synod == 14 and (current_sol % SOLS_PER_SYNOD == 0):
            for l in self.body.layers.values():
                l.wear = max(0.02, l.wear * 0.3)
                
        body_res = self.body.step_sol(env, latent_shock, net_labor_h, self._rng)
        mesh_res = self.mesh.step(body_res) if self.mesh is not None else {}
        
        # 9. Pontuação Composta de Prontidão (AMCI & Saúde Geral)
        water_closure = urine_res["water_recovered_pct"]
        nutrient_closure = nut_res["closure"]
        body_integrity = body_res["body_integrity"]
        amci = round((water_closure * 0.3 + nutrient_closure * 0.3 + body_integrity * 0.4), 4)
        
        step_summary = {
            "sol": current_sol,
            "synod": current_synod,
            "era": era_name,
            "behavior_mode": behavior_mode,
            "amci_closure": amci,
            "body_integrity": body_integrity,
            "active_robots": n_robots,
            "net_labor_hours": net_labor_h,
            "env": env,
            "production_sol": {
                "dust_collected_kg": round(dust_step["dust_collected_kg"], 3),
                "regolith_mined_kg": round(regolith_sol_kg, 2),
                "mining_energy_kwh": round(fleet_res["energy_kwh"], 2),
                "refinery_energy_kwh": ref_run["energy_kwh"],
                "fe_metal_total_kg": round(fe_reduced_ref_kg + fe_metal_smelted_kg, 3),
                "cement_total_kg": round(cement_ref_kg + geopoly_mined_kg, 3),
                "silicon_metal_kg": round(si_metal_kg, 3),
                "sintered_bricks_kg": round(bricks_sintered_kg, 3),
                "sulfuric_acid_kg": round(h2so4_kg, 3),
                "ch4_fuel_kg": round(sab_res["ch4_kg"], 3),
                "water_recovered_l": round(urine_res["water_recovered_l"] + sab_res["h2o_kg"], 3),
                "ice_water_l": round(ice_water_l, 2),
                "o2_net_kg": round(dust_step["o2_from_clo4_kg"] + o2_ref_kg + 26.0 + (40.0 if current_sol >= 1500 else 0.0), 3),
                "spirulina_kg": spirulina_sol_kg,
                "potatoes_kg": potatoes_sol_kg,
                "wheat_kg": wheat_sol_kg,
                "protein_animal_kg": round(protein_animal_sol_kg, 3),
                "n_caproate_kg": round(n_caproate_sol_kg, 3),
            },
            "stocks_level": {k: round(v, 2) for k, v in self.stocks.items()},
            "layer_wears": {k: round(v, 5) for k, v in body_res.items() if k.startswith("wear_") and not k.startswith("wear_rate_")},
            "layer_wear_rates": {k: round(v, 8) for k, v in body_res.items() if k.startswith("wear_rate_")},
            "boundary_surfaces": {k: v for k, v in body_res.items()
                                  if k.startswith(("airlock_", "cabin_",
                                                   "eclss_filter",
                                                   "crew_clo4", "shield_"))},
            "organ_surfaces": {k: v for k, v in body_res.items()
                               if k.startswith(("organ_", "berm_"))},
            "fleet_state": {
                "units": len(self.fleet.unit_health),
                "unit_health": [round(h, 4) for h in self.fleet.unit_health],
                "spare_parts_kg": round(self.fleet.spare_parts_kg, 2),
                "units_built": self.fleet.units_built,
                "units_rebuilt": self.fleet.units_rebuilt,
                "units_refurbished": self.fleet.units_refurbished,
                "units_cannibalized": self.fleet.units_cannibalized,
                "units_lost_mission": self.fleet.units_lost_mission,
                "fleet_events_sol": {k: fleet_res[k] for k in
                                     ("built", "rebuilt", "refurbished",
                                      "cannibalized", "lost",
                                      "labor_bonus_h")},
            },
            "soil_wash_sol": {k: round(v, 4) for k, v in wash_res.items()},
            "soil_washed_total_t": round(self.soil_wash.soil_washed_total_t, 2),
            "mesh_surfaces": mesh_res,
            "repair_load_h": body_res["repair_load_h"],
            "incident": body_res["incident"],
        }
        if reg:
            step_summary.update({
                "s_meta": reg["s_meta"],
                "regime": reg["regime"],
                "regime_pending": reg["pending"],
                "s_meta_components": reg["components"],
                "defense_active": reg["defense_active"],
                "homeostatic_refusal": reg["homeostatic_refusal"],
                "heightened_monitoring": reg["heightened_monitoring"],
            })
        
        self.recent_history.append({
            "sol": current_sol,
            "synod": current_synod,
            "amci": amci,
            "integrity": body_integrity,
            "behavior": behavior_mode,
            "ch4_kg": round(self.stocks["ch4_fuel_kg"], 1),
            "fe_metal_kg": round(self.stocks["fe_metal_kg"], 1),
            "water_l": round(self.stocks["water_l"], 1),
            "food_total_kg": round(self.stocks["spirulina_kg"] + self.stocks["potatoes_kg"] + self.stocks["wheat_kg"], 1)
        })
        if len(self.recent_history) > self.max_history_len:
            self.recent_history.pop(0)
            
        return step_summary

    @staticmethod
    def _scalar_state(obj: Any) -> Dict[str, float]:
        """Campos escalares de um subsistema — estado restaurável mínimo."""
        return {k: v for k, v in vars(obj).items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)}

    @staticmethod
    def _restore_scalars(obj: Any, state: Dict[str, float]) -> None:
        for k, v in state.items():
            if hasattr(obj, k):
                setattr(obj, k, v)

    def snapshot(self) -> Dict[str, Any]:
        """Foto completa e soberana do estado do simulador para checkpoint.

        fix auditoria 2026-10-03: agora inclui wear/anneal das camadas,
        estado escalar do SurfaceOrgan (+berm), AirlockOrgan, ShieldStack,
        estado do RNG e o histórico — restaurar não volta "pela metade"."""
        return {
            "sol": self.sol,
            "synod": self.synod,
            "era": self.era,
            # SEM arredondar: stocks é fonte de restore — round() aqui
            # quebrava a continuação exata da trajetória (bug pego pelo
            # teste de reprodutibilidade RNG da auditoria).
            "stocks": dict(self.stocks),
            "body_integrity": round(1.0 - sum(l.wear for l in self.body.layers.values()) / len(self.body.layers), 5),
            "active_robots": self.active_fleet_robots(),
            "neutrosophic_body": self.body.neutrosophic_state(),
            "recent_telemetry": list(self.recent_history[-10:]),
            "recent_history": list(self.recent_history),
            "body_state": {
                "layers": {n: {"wear": l.wear, "anneal": l.anneal}
                           for n, l in self.body.layers.items()},
                "organ": (self._scalar_state(self.body.organ)
                          if self.body.organ is not None else None),
                "organ_berm": (self._scalar_state(self.body.organ.berm)
                               if (self.body.organ is not None
                                   and getattr(self.body.organ, "berm", None)
                                   is not None) else None),
                "boundary": (self._scalar_state(self.body.boundary)
                             if self.body.boundary is not None else None),
                "shield": (self._scalar_state(self.body.shield)
                           if self.body.shield is not None else None),
            },
            "fleet_state": {
                "unit_health": list(self.fleet.unit_health),
                "spare_parts_kg": self.fleet.spare_parts_kg,
                "units_built": self.fleet.units_built,
                "units_rebuilt": self.fleet.units_rebuilt,
                "units_refurbished": self.fleet.units_refurbished,
                "units_cannibalized": self.fleet.units_cannibalized,
                "units_lost_mission": self.fleet.units_lost_mission,
            },
            "rng_state_hex": binascii.hexlify(
                pickle.dumps(self._rng.getstate())).decode("ascii"),
            "subsystem_state": {
                "regime": (({
                    **self._scalar_state(self.regime),
                    "_pending": list(self.regime._pending)
                    if getattr(self.regime, "_pending", None) is not None
                    else None,
                    "_integrity_hist": list(self.regime._integrity_hist)
                    if getattr(self.regime, "_integrity_hist", None) is not None
                    else None})
                    if self.regime is not None else None),
                "mesh": (({
                    **self._scalar_state(self.mesh),
                    "vbkf": (self._scalar_state(self.mesh.vbkf)
                             if getattr(self.mesh, "vbkf", None) is not None
                             else None),
                    "afex": (self._scalar_state(self.mesh.afex)
                             if getattr(self.mesh, "afex", None) is not None
                             else None),
                    "glia": (self._scalar_state(self.mesh.glia)
                             if getattr(self.mesh, "glia", None) is not None
                             else None)})
                    if self.mesh is not None else None),
                "dcs": {sub: self._scalar_state(getattr(self.dcs, sub))
                        for sub in ("flux", "eds", "esp", "climber", "frac")
                        if getattr(self.dcs, sub, None) is not None},
                "soil_wash": self._scalar_state(self.soil_wash),
                "refinery": ({sub: self._scalar_state(getattr(self.refinery, sub))
                              for sub in ("scheduler", "reactor")
                              if getattr(self.refinery, sub, None) is not None}
                             if self.refinery is not None else None),
            },
        }

    def restore_from_snapshot(self, data: Dict[str, Any]) -> None:
        """Restaura o estado exato da estação a partir de um checkpoint salvo.

        Campos novos são opcionais — checkpoints antigos (só sol+stocks)
        continuam restauráveis."""
        if not data:
            return
        self.sol = data.get("sol", 0)
        st = data.get("stocks", {})
        for k, v in st.items():
            if k in self.stocks:
                self.stocks[k] = v

        bs = data.get("body_state") or {}
        for name, lay in (bs.get("layers") or {}).items():
            if name in self.body.layers:
                self.body.layers[name].wear = lay["wear"]
                self.body.layers[name].anneal = lay["anneal"]
        if bs.get("organ") is not None and self.body.organ is not None:
            self._restore_scalars(self.body.organ, bs["organ"])
        if (bs.get("organ_berm") is not None and self.body.organ is not None
                and getattr(self.body.organ, "berm", None) is not None):
            self._restore_scalars(self.body.organ.berm, bs["organ_berm"])
        if bs.get("boundary") is not None and self.body.boundary is not None:
            self._restore_scalars(self.body.boundary, bs["boundary"])
        if bs.get("shield") is not None and self.body.shield is not None:
            self._restore_scalars(self.body.shield, bs["shield"])

        fs = data.get("fleet_state") or {}
        if fs.get("unit_health") is not None:
            self.fleet.unit_health = [float(h) for h in fs["unit_health"]]
        for _k in ("spare_parts_kg", "units_built", "units_rebuilt",
                   "units_refurbished", "units_cannibalized",
                   "units_lost_mission"):
            if fs.get(_k) is not None:
                setattr(self.fleet, _k, fs[_k])

        if data.get("recent_history"):
            self.recent_history = list(data["recent_history"])
        if data.get("rng_state_hex"):
            self._rng.setstate(pickle.loads(
                binascii.unhexlify(data["rng_state_hex"])))

        ss = data.get("subsystem_state") or {}
        rs = ss.get("regime")
        if rs is not None and self.regime is not None:
            self._restore_scalars(
                self.regime,
                {k: v for k, v in rs.items()
                 if isinstance(v, (int, float)) and not isinstance(v, bool)})
            if rs.get("_pending") is not None:
                self.regime._pending = tuple(rs["_pending"])
            if rs.get("_integrity_hist") is not None:
                from collections import deque
                self.regime._integrity_hist = deque(
                    rs["_integrity_hist"],
                    maxlen=self.regime._integrity_hist.maxlen)
        ms = ss.get("mesh")
        if ms is not None and self.mesh is not None:
            self._restore_scalars(
                self.mesh,
                {k: v for k, v in ms.items()
                 if isinstance(v, (int, float)) and not isinstance(v, bool)})
            for sub in ("vbkf", "afex", "glia"):
                if ms.get(sub) is not None and getattr(self.mesh, sub, None) is not None:
                    self._restore_scalars(getattr(self.mesh, sub), ms[sub])
        ds = ss.get("dcs")
        if ds is not None:
            for sub, state in ds.items():
                if getattr(self.dcs, sub, None) is not None:
                    self._restore_scalars(getattr(self.dcs, sub), state)
        if ss.get("soil_wash") is not None:
            self._restore_scalars(self.soil_wash, ss["soil_wash"])
        fs2 = ss.get("refinery")
        if fs2 is not None and self.refinery is not None:
            for sub, state in fs2.items():
                if getattr(self.refinery, sub, None) is not None:
                    self._restore_scalars(getattr(self.refinery, sub), state)
