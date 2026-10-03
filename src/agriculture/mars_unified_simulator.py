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

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from src.agriculture.mars_dust_catalyst import DustCatalystStation
from src.agriculture.mars_refinery import MarsRefinery
from src.agriculture.mars_station_body import StationBody
from src.agriculture.sabatier_reactor import SabatierReactor
from src.agriculture.mealworm_protein import MealwormFarm
from src.agriculture.circular_economy import UrineBrineProcessor, NutrientCycleOptimizer
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
        "regolith_mined_total_t": 0.0,
    })
    
    # Histórico recente para telemetria (janela móvel)
    recent_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_len: int = 100
    
    def __post_init__(self):
        self._rng = random.Random(self.seed)
        # Aplica alívio de poeira EDS no corpo
        self.body.apply_dust_catalyst({
            "solar_arrays": 0.92,
            "optics_windows": 0.74,
            "radiators": 0.64
        })

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
            season = math.sin(2 * math.pi * current_sol / 669.0)
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
        
        wind = env.get("wind_speed_ms", 4.0)
        dust_dep = env.get("dust_flux", 1.0)
        seismic = env.get("seismic_shock", 0.0)

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
            "perchlorate_kg": min(self.stocks["perchlorate_kg"], dust_step["perchlorate_kg"] * 1.5),
            "fe_oxide_kg": min(self.stocks["fe_oxide_kg"], dust_step["fe_oxide_kg"] * 1.5),
            "silica_kg": min(self.stocks["silica_kg"], dust_step["silica_kg"] * 1.5),
            "gypsum_kg": min(self.stocks["gypsum_kg"], dust_step["gypsum_kg"] * 1.5),
            "bulk_fines_kg": dust_step["bulk_fines_kg"]
        }
        plan = self.refinery.scheduler.schedule(ref_inputs, energy_budget)
        ref_run = self.refinery.reactor.run(plan, self._rng)
        prods = ref_run["products"]
        
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
        
        # 4. Cadeia 3: Mineração e Metalurgia de Regolito Bruto (340 kg/sol)
        regolith_sol_kg = 340.0
        self.stocks["regolith_mined_total_t"] += regolith_sol_kg / 1000.0
        
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
        
        # 8. Cadeia 7: Corpo Material da Estação & Robótica
        n_robots = self.active_fleet_robots()
        labor_econ = LaborEconomy(n_robots=n_robots)
        net_labor_h = labor_econ.net_hours_sol()
        
        # Se for marco de provisão de meia-vida (Synod 14, sol ~10920), alívio de revisão
        if current_synod == 14 and (current_sol % SOLS_PER_SYNOD == 0):
            for l in self.body.layers.values():
                l.wear = max(0.02, l.wear * 0.3)
                
        body_res = self.body.step_sol(env, seismic, net_labor_h, self._rng)
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
                "fe_metal_total_kg": round(fe_reduced_ref_kg + fe_metal_smelted_kg, 3),
                "cement_total_kg": round(cement_ref_kg + geopoly_mined_kg, 3),
                "silicon_metal_kg": round(si_metal_kg, 3),
                "sintered_bricks_kg": round(bricks_sintered_kg, 3),
                "sulfuric_acid_kg": round(h2so4_kg, 3),
                "ch4_fuel_kg": round(sab_res["ch4_kg"], 3),
                "water_recovered_l": round(urine_res["water_recovered_l"] + sab_res["h2o_kg"], 3),
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

    def snapshot(self) -> Dict[str, Any]:
        """Foto completa e soberana do estado do simulador para checkpoint."""
        return {
            "sol": self.sol,
            "synod": self.synod,
            "era": self.era,
            "stocks": {k: round(v, 2) for k, v in self.stocks.items()},
            "body_integrity": round(1.0 - sum(l.wear for l in self.body.layers.values()) / len(self.body.layers), 5),
            "active_robots": self.active_fleet_robots(),
            "neutrosophic_body": self.body.neutrosophic_state(),
            "recent_telemetry": list(self.recent_history[-10:])
        }

    def restore_from_snapshot(self, data: Dict[str, Any]) -> None:
        """Restaura o estado exato da estação a partir de um checkpoint salvo."""
        if not data:
            return
        self.sol = data.get("sol", 0)
        st = data.get("stocks", {})
        for k, v in st.items():
            if k in self.stocks:
                self.stocks[k] = v
