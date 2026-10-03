"""Mars ECLSS Cascade, Extremophile HGT & Autonomous Veto Engine.
================================================================
Implementa os modelos físicos, biológicos e decisórios para o programa
de especialização da Estação Marciana Árvore:
  1. ECLSSCascadeSimulator: Falha em cascata em circuitos hídricos e de nutrientes.
  2. ExtremophileHGTModel: Cinética de transferência horizontal de genes em biofilmes.
  3. ISRUPowerBudgetEngine: Balanço detalhado de kWe e térmico sob modos climáticos.
  4. RoboticVetoGovernor: Despacho decisório sob latência (3-22 min) e regras de veto.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# 1. ECLSS CASCADE SIMULATOR
# =====================================================================

@dataclass
class ECLSSComponentState:
    name: str
    operational: bool = True
    efficiency: float = 1.0  # 0.0 a 1.0
    degradation_rate: float = 0.0001
    failure_probability: float = 0.001


class ECLSSCascadeSimulator:
    """Simula a dinâmica de propagação de falha em cascata no suporte de vida.

    Cenário: Bomba de recirculação de nutrientes quebra -> concentração nos leitos
    cai exponencialmente -> fotossíntese de Spirulina e batata decresce ->
    produção de O2 despenca e CO2 acumula -> buffer de eletrólise OGS aciona
    e demanda energia adicional.
    """

    def __init__(self) -> None:
        self.components: Dict[str, ECLSSComponentState] = {
            "nutrient_pump_alpha": ECLSSComponentState("nutrient_pump_alpha"),
            "nutrient_pump_beta": ECLSSComponentState("nutrient_pump_beta"),
            "water_reverse_osmosis": ECLSSComponentState("water_reverse_osmosis"),
            "bioreactor_algae": ECLSSComponentState("bioreactor_algae"),
            "electrolysis_ogs": ECLSSComponentState("electrolysis_ogs"),
            "sabatier_catalyst": ECLSSComponentState("sabatier_catalyst"),
            "co2_scrubber_cdra": ECLSSComponentState("co2_scrubber_cdra"),
        }
        # Parâmetros de reservatório da estação (base 10 ocupantes)
        self.water_reservoir_l: float = 20000.0
        self.oxygen_buffer_kg: float = 350.0  # ~35 dias para 10 pessoas a 0.84 kg/sol-hab
        self.co2_level_ppm: float = 800.0     # nominal seguro < 1200 ppm
        self.nutrient_concentration_ppm: float = 1200.0  # NPK em hidroponia
        self.biomass_yield_ratio: float = 1.0

    def trigger_component_failure(self, component_name: str) -> bool:
        if component_name in self.components:
            self.components[component_name].operational = False
            self.components[component_name].efficiency = 0.0
            return True
        return False

    def step(self, dt_hours: float = 1.0, human_count: int = 10) -> Dict[str, Any]:
        """Executa um passo temporal e calcula a cascata estequiométrica."""
        # 1. Bomba de nutrientes: se ambas falharem, o fluxo cessa. Se uma falhar, 50% de capacidade
        pump_eff = 0.0
        if self.components["nutrient_pump_alpha"].operational:
            pump_eff += 0.5 * self.components["nutrient_pump_alpha"].efficiency
        if self.components["nutrient_pump_beta"].operational:
            pump_eff += 0.5 * self.components["nutrient_pump_beta"].efficiency

        # Decaimento de nutrientes disponíveis para raízes/Spirulina
        if pump_eff < 0.2:
            # Sem circulação, estagnação e decantação (decaimento rápido)
            decay = math.exp(-0.08 * dt_hours)
            self.nutrient_concentration_ppm *= decay
        elif pump_eff < 0.8:
            decay = math.exp(-0.02 * dt_hours)
            self.nutrient_concentration_ppm *= decay
        else:
            # Nominal: reposição mantém equilíbrio em 1200 ppm
            self.nutrient_concentration_ppm += (1200.0 - self.nutrient_concentration_ppm) * 0.1 * dt_hours

        # 2. Resposta de biomassa fotossintética
        nutrient_factor = min(1.0, max(0.05, self.nutrient_concentration_ppm / 1200.0))
        self.biomass_yield_ratio = nutrient_factor * (1.0 if self.components["bioreactor_algae"].operational else 0.0)

        # 3. Balanço de O2 e CO2
        # Consumo humano: ~0.84 kg O2 / pessoa-sol -> 0.035 kg/h por pessoa
        human_o2_req_per_h = 0.035 * human_count
        human_co2_prod_per_h = 0.042 * human_count

        # Produção biológica de O2: nominal 0.40 kg/h para 10 pessoas
        bio_o2_prod_per_h = 0.40 * self.biomass_yield_ratio
        bio_co2_uptake_per_h = 0.45 * self.biomass_yield_ratio

        # Déficit biológico
        delta_o2 = (bio_o2_prod_per_h - human_o2_req_per_h) * dt_hours
        delta_co2 = (human_co2_prod_per_h - bio_co2_uptake_per_h) * dt_hours

        # Se O2 está em déficit, OGS tenta compensar
        ogs_backup_active = False
        ogs_power_kw = 0.0
        if delta_o2 < 0.0 and self.components["electrolysis_ogs"].operational:
            needed_o2 = abs(delta_o2)
            # OGS consome ~4.3 kWh por kg de O2
            ogs_backup_active = True
            ogs_power_kw = (needed_o2 / dt_hours) * 4.3
            self.oxygen_buffer_kg += 0.0  # mantido estável pela eletrólise
            # Consome água: 1 kg O2 requer ~1.12 L H2O
            water_spent = needed_o2 * 1.124
            self.water_reservoir_l = max(0.0, self.water_reservoir_l - water_spent)
        else:
            self.oxygen_buffer_kg = max(0.0, self.oxygen_buffer_kg + delta_o2)

        # Scrubber CDRA para absorver excesso de CO2
        if self.components["co2_scrubber_cdra"].operational:
            cdra_capacity_kg_h = 0.50
            absorbed_co2 = min(delta_co2, cdra_capacity_kg_h * dt_hours)
            delta_co2 -= absorbed_co2

        # Variação no ppm de CO2 no habitat (volume de ~2500 m3 de ar)
        # 1 kg de CO2 em 2500 m3 (~3000 kg ar) equivale a ~330 ppm
        self.co2_level_ppm = max(400.0, self.co2_level_ppm + (delta_co2 * 330.0))

        # Classificação de alarme
        critical_alert = False
        alert_reason = []
        if self.oxygen_buffer_kg < 100.0:
            critical_alert = True
            alert_reason.append("CRITICAL: O2 buffer abaixo de 100 kg")
        if self.co2_level_ppm > 2500.0:
            critical_alert = True
            alert_reason.append("CRITICAL: Nível de CO2 tóxico (> 2500 ppm)")
        if self.water_reservoir_l < 2000.0:
            critical_alert = True
            alert_reason.append("CRITICAL: Tanque hídrico na reserva de emergência")

        return {
            "pump_eff": round(pump_eff, 3),
            "nutrient_ppm": round(self.nutrient_concentration_ppm, 1),
            "biomass_yield_ratio": round(self.biomass_yield_ratio, 3),
            "oxygen_buffer_kg": round(self.oxygen_buffer_kg, 2),
            "co2_level_ppm": round(self.co2_level_ppm, 1),
            "water_reservoir_l": round(self.water_reservoir_l, 1),
            "ogs_backup_active": ogs_backup_active,
            "ogs_power_kw": round(ogs_power_kw, 2),
            "critical_alert": critical_alert,
            "alert_reason": "; ".join(alert_reason) if alert_reason else "NOMINAL"
        }


# =====================================================================
# 2. EXTREMOPHILE HGT KINETIC MODEL
# =====================================================================

@dataclass
class MicrobialGuildGeneProfile:
    species_name: str
    target_genes: List[str]  # e.g., ["pcrA", "cld", "nifH", "recA"]
    resistance_factor: float  # 0.0 a 1.0 contra dessecação/radiação
    conjugation_competence: float  # frequência basal de conjugação / célula-geração


class ExtremophileHGTModel:
    """Modela a taxa de transferência horizontal de genes (HGT) em biofilme marciano.

    Sob estresse moderado de radiação ionizante e perclorato, a via SOS bacteriana
    (recA dependente) é ativada, elevando transitoriamente a taxa de conjugação e
    competência natural para absorção de DNA exógeno, estabilizando-se antes de limites letais.
    """

    def __init__(self) -> None:
        self.guilds: Dict[str, MicrobialGuildGeneProfile] = {
            "dechloromonas": MicrobialGuildGeneProfile(
                "Dechloromonas agitata", ["pcrA", "pcrB", "pcrC", "cld"], 0.75, 1.2e-5
            ),
            "deinococcus": MicrobialGuildGeneProfile(
                "Deinococcus radiodurans", ["recA", "pprA", "katA", "drpA"], 0.98, 3.5e-6
            ),
            "chroococcidiopsis": MicrobialGuildGeneProfile(
                "Chroococcidiopsis sp.", ["scyA", "wcyA", "nifH", "nifD", "nifK"], 0.92, 8.0e-7
            ),
            "rhizobium_mars": MicrobialGuildGeneProfile(
                "Rhizobium leguminosarum-M", ["nifHDK", "nodABC", "phoA", "phoB"], 0.65, 5.0e-5
            )
        }

    def compute_hgt_rate(
        self,
        donor_key: str,
        recipient_key: str,
        ionizing_dose_msv_day: float = 0.67,
        perchlorate_wt_pct: float = 0.5,
        biofilm_density_cm2: float = 1e8
    ) -> Dict[str, Any]:
        """Calcula a taxa e eventos previstos de HGT por cm2-sol."""
        if donor_key not in self.guilds or recipient_key not in self.guilds:
            raise ValueError("Guilda desconhecida no consórcio.")

        donor = self.guilds[donor_key]
        recipient = self.guilds[recipient_key]

        # 1. Taxa basal combinada (média geométrica)
        base_rate = math.sqrt(donor.conjugation_competence * recipient.conjugation_competence)

        # 2. Fator de ativação SOS por radiação cósmica/solar
        # Doses de 0.2 a 2.0 mSv/dia aumentam a transcrição de recA e tra (indução até 4x)
        # Doses > 15 mSv/dia causam quebra excessiva de fita dupla e letalidade celular
        if ionizing_dose_msv_day <= 5.0:
            sos_factor = 1.0 + 1.8 * math.log1p(ionizing_dose_msv_day)
        else:
            sos_factor = max(0.1, 4.0 * math.exp(-0.15 * (ionizing_dose_msv_day - 5.0)))

        # 3. Fator osmótico/estresse oxidativo por perclorato
        # Perclorato atua como agente caotrópico; acima de 1.0% inibe se não houver pcrA
        has_pcr = "pcrA" in donor.target_genes or "pcrA" in recipient.target_genes
        if perchlorate_wt_pct <= 0.6:
            perchlorate_stress_boost = 1.0 + 0.5 * perchlorate_wt_pct
        else:
            decay_rate = 0.5 if has_pcr else 2.5
            perchlorate_stress_boost = max(0.01, (1.0 + 0.3) * math.exp(-decay_rate * (perchlorate_wt_pct - 0.6)))

        effective_hgt_rate = base_rate * sos_factor * perchlorate_stress_boost

        # Eventos diários esperados por cm2 de biofilme
        # Proporcional aos contatos celulares no biofilme: ~ density * density * cross_section
        effective_encounters = biofilm_density_cm2 * 1e-4  # fração de vizinhança direta
        expected_events_per_sol = effective_encounters * effective_hgt_rate

        # Verificação do gate biológico: transferência de genes perigosos / novidades
        novelty_index = min(1.0, (sos_factor * perchlorate_stress_boost) / 5.0)

        return {
            "donor": donor.species_name,
            "recipient": recipient.species_name,
            "transferred_candidates": donor.target_genes,
            "effective_hgt_rate_per_cell": effective_hgt_rate,
            "sos_induction_factor": round(sos_factor, 3),
            "perchlorate_stress_factor": round(perchlorate_stress_boost, 3),
            "expected_events_per_cm2_sol": round(expected_events_per_sol, 4),
            "novelty_index": round(novelty_index, 3),
            "containment_risk": "HIGH" if novelty_index > 0.8 else ("MODERATE" if novelty_index > 0.4 else "LOW")
        }


# =====================================================================
# 3. ISRU POWER BUDGET ENGINE
# =====================================================================

@dataclass
class ISRUProcessBudget:
    process_name: str
    specific_energy_kwh_per_unit: float
    unit_name: str
    thermal_power_kw: float = 0.0


class ISRUPowerBudgetEngine:
    """Calcula a demanda elétrica (kWe) e térmica (kWt) de cada processo ISRU

    Processos modelados:
      - SOXE CO2 Electrolysis (O2)
      - Sabatier CH4 Reactor (Propelente)
      - Subsurface Ice Extractor (H2O)
      - Regolith Smelting / Carbothermal (Fe & Si)
      - Basalt Sulfate Sulfonation (H2SO4)
    """

    def __init__(self) -> None:
        self.processes: Dict[str, ISRUProcessBudget] = {
            "soxe_oxygen": ISRUProcessBudget("SOXE O2", 4.8, "kg_O2", thermal_power_kw=1.2),
            "sabatier_propellant": ISRUProcessBudget("Sabatier CH4", 5.2, "kg_CH4", thermal_power_kw=0.8),
            "ice_melting_sublimation": ISRUProcessBudget("Ice H2O", 0.15, "L_H2O", thermal_power_kw=2.5),
            "regolith_iron_smelting": ISRUProcessBudget("Iron Smelting", 3.4, "kg_Fe", thermal_power_kw=4.0),
            "silicon_reduction": ISRUProcessBudget("Silicon Reduction", 6.8, "kg_Si", thermal_power_kw=5.5),
            "sulfuric_acid_synthesis": ISRUProcessBudget("H2SO4 Synthesis", 1.8, "kg_H2SO4", thermal_power_kw=1.0)
        }

    def compute_daily_demand(
        self,
        o2_kg: float = 8.4,
        ch4_kg: float = 10.0,
        water_l: float = 25.0,
        iron_kg: float = 30.0,
        silicon_kg: float = 10.0,
        h2so4_kg: float = 5.0
    ) -> Dict[str, Any]:
        """Calcula o total de energia elétrica (kWh/sol) e potência média (kWe)."""
        demands = {
            "soxe_oxygen": (o2_kg, self.processes["soxe_oxygen"]),
            "sabatier_propellant": (ch4_kg, self.processes["sabatier_propellant"]),
            "ice_melting_sublimation": (water_l, self.processes["ice_melting_sublimation"]),
            "regolith_iron_smelting": (iron_kg, self.processes["regolith_iron_smelting"]),
            "silicon_reduction": (silicon_kg, self.processes["silicon_reduction"]),
            "sulfuric_acid_synthesis": (h2so4_kg, self.processes["sulfuric_acid_synthesis"]),
        }

        total_kwh_sol = 0.0
        process_breakdown_kwh = {}
        total_thermal_kw = 0.0

        for key, (qty, proc) in demands.items():
            kwh = qty * proc.specific_energy_kwh_per_unit
            process_breakdown_kwh[key] = round(kwh, 2)
            total_kwh_sol += kwh
            if qty > 0:
                total_thermal_kw += proc.thermal_power_kw

        # 1 sol marciano = 24.66 horas
        average_power_kwe = total_kwh_sol / 24.66

        return {
            "total_kwh_per_sol": round(total_kwh_sol, 2),
            "average_power_kwe": round(average_power_kwe, 2),
            "total_thermal_power_kwt": round(total_thermal_kw, 2),
            "breakdown_kwh": process_breakdown_kwh,
            "station_basal_heating_kw": 2.5,
            "total_continuous_load_kwe": round(average_power_kwe + 2.5, 2)
        }

    def evaluate_grid_security(
        self,
        load_kwe: float,
        solar_capacity_kwe: float = 60.0,
        fsp_nuclear_capacity_kwe: float = 40.0,
        fuel_cell_backup_kwe: float = 15.0,
        tau_dust_optical_depth: float = 0.5
    ) -> Dict[str, Any]:
        """Avalia a estabilidade da microrrede híbrida sob diferentes opacidades de poeira (tau)."""
        # Atenuação de Beer-Lambert para radiação solar incidente: P_solar = P_0 * exp(-0.85 * tau)
        solar_available_kwe = solar_capacity_kwe * math.exp(-0.85 * tau_dust_optical_depth)
        firm_nuclear_kwe = fsp_nuclear_capacity_kwe  # FSP não depende de poeira
        base_available_kwe = solar_available_kwe + firm_nuclear_kwe

        deficit_kwe = max(0.0, load_kwe - base_available_kwe)
        backup_engaged = False
        blackout = False

        if deficit_kwe > 0.0:
            if deficit_kwe <= fuel_cell_backup_kwe:
                backup_engaged = True
            else:
                blackout = True

        return {
            "tau_dust": tau_dust_optical_depth,
            "solar_generated_kwe": round(solar_available_kwe, 2),
            "nuclear_generated_kwe": round(firm_nuclear_kwe, 2),
            "total_available_kwe": round(base_available_kwe, 2),
            "required_load_kwe": round(load_kwe, 2),
            "grid_status": "BLACKOUT" if blackout else ("BACKUP_ONLINE" if backup_engaged else "NOMINAL_STABLE"),
            "margin_kwe": round(base_available_kwe - load_kwe, 2)
        }


# =====================================================================
# 4. ROBOTIC VETO & LATENCY GOVERNOR
# =====================================================================

@dataclass
class InterplanetaryDecision:
    action_id: str
    decision_type: str  # "routine", "mutation_experiment", "crop_transition", "abort"
    sol: int
    requested_by: str   # "mars_robotic_core" | "earth_ground_control"
    status: str = "PENDING"  # "EXECUTED", "VETOED", "ESCALATED"
    earth_veto_received: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class RoboticVetoGovernor:
    """Governança em 3 níveis com histerese e latência orbital (3 a 22 minutos luz)."""

    def __init__(self) -> None:
        # Níveis de decisão:
        # Nível 1 (Autonomia Total): ações imediatas sem espera da Terra
        self.level_1_actions = {
            "light_cycle_adjustment", "nutrient_ph_balance", "quarantine_local_chamber",
            "dust_wiper_sweep", "emergency_heater_boost"
        }
        # Nível 2 (Consultivo): a estação inicia um timer; se Terra não vetar em 45 min, executa
        self.level_2_actions = {
            "mutation_experiment_expansion", "adjust_hgt_perchlorate_barrier",
            "robot_maintenance_overhaul"
        }
        # Nível 3 (Veto Obrigatório): requer confirmação explícita da Terra
        self.level_3_actions = {
            "dominant_crop_transition", "open_quarantine_to_ecosystem",
            "nuclear_fsp_shutoff", "sample_earth_return_packaging"
        }

    def evaluate_decision(
        self,
        decision: InterplanetaryDecision,
        one_way_latency_minutes: float = 12.0,
        earth_veto_flag: bool = False
    ) -> Dict[str, Any]:
        """Avalia e processa o despacho decisório."""
        action = decision.decision_type

        # Nível 1: Execução autônoma imediata
        if action in self.level_1_actions:
            decision.status = "EXECUTED"
            return {
                "level": 1,
                "classification": "AUTONOMY_TOTAL",
                "execution_delay_min": 0.0,
                "status": "EXECUTED",
                "reason": "Ação de regulação crítica e rotina. Latência orbital não pode bloquear."
            }

        # Nível 2: Consultivo com timer
        if action in self.level_2_actions:
            round_trip = one_way_latency_minutes * 2.0
            if earth_veto_flag:
                decision.status = "VETOED"
                return {
                    "level": 2,
                    "classification": "VETO_CONSULTATIVE",
                    "execution_delay_min": round_trip,
                    "status": "VETOED_BY_EARTH",
                    "reason": "Terra enviou sinal de veto dentro da janela consultiva."
                }
            else:
                decision.status = "EXECUTED"
                return {
                    "level": 2,
                    "classification": "VETO_CONSULTATIVE",
                    "execution_delay_min": round_trip,
                    "status": "EXECUTED_AUTO_TIMER",
                    "reason": "Janela consultiva expirou sem veto. Estação prosseguiu com segurança."
                }

        # Nível 3: Veto Obrigatório (Trava de Segurança Estrita)
        if action in self.level_3_actions:
            round_trip = one_way_latency_minutes * 2.0
            if earth_veto_flag:
                decision.status = "VETOED"
                return {
                    "level": 3,
                    "classification": "VETO_MANDATORY",
                    "execution_delay_min": round_trip,
                    "status": "VETOED_MANDATORY",
                    "reason": "Terra exerceu veto soberano obrigatório. Transição abortada."
                }
            else:
                decision.status = "EXECUTED"
                return {
                    "level": 3,
                    "classification": "VETO_MANDATORY",
                    "execution_delay_min": round_trip,
                    "status": "EXECUTED_AUTHORIZED",
                    "reason": "Autorização explícita recebida da Terra após latência de ida e volta."
                }

        # Desconhecido cai em quarentena conservadora
        decision.status = "ESCALATED"
        return {
            "level": 3,
            "classification": "UNKNOWN_FAILSAFE",
            "execution_delay_min": one_way_latency_minutes * 2.0,
            "status": "HELD_IN_QUARANTINE",
            "reason": "Ação não catalogada; retida até intervenção explícita de supervisores."
        }
