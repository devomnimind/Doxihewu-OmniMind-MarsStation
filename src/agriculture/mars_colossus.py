"""Mars Colossus — o veículo É a estação; robôs humanoides são a força.

Visão do operador (2026-09-28): "o nosso seria esse mesmo colosso
desenvolvido para comportar a estação — nada dele seria perdido, mas
aproveitado como base. Plano de 50-60 anos; no colosso vão robôs
humanoides para indústria, trabalho manual e manutenção."

COLOSSO = Starship v3 (Flight 14, primeiro orbital hoje, 2026-09-28).
Arquitetura clássica Mars-direct+: os landers NÃO voltam — cada nave
que pousa vira infraestrutura permanente da estação:

  casco 9m x ~52m inox 304L  -> módulos de habitat / tanques
  6 Raptors                  -> turbobombas industriais (compressores ISRU)
  tanques CH4/LOX ~1500m3    -> armazenagem água/propelente/armações
  TPS tiles hexagonais       -> revestimento de FORNO (suportam reentrada!)
  flaps + atuadores          -> vigas, guindaste, braços de montagem
  aviónica + baterias + fios -> eletrônica e rede elétrica da estação
  porta payload + pez rail   -> airlock / pórtico de carga
  trem de pouso              -> fundações ancoradas / pilares

NADA é sucata: massa entregue = massa da estação, literalmente.

ROBÔS HUMANOIDES (classe Optimus/Figure): força de trabalho EVA-free —
indústria, montagem, manutenção, estufa, ensacamento de regolito.
O detalhe autocatalítico: robôs fazem manutenção em robôs — a frota
torna-se parcialmente auto-sustentável quando a oficina local fabrica
partes (motores/chips ainda importados nas primeiras eras).

PLANO 60 ANOS em synods (~780 sols cada; 27 synods ~ 57.6 anos):
  Era I   "Ancoragem"    syn 0-3   — landers cargo viram base; ISRU prop
  Era II  "Primeira Pele" syn 4-8  — habitats, estufa, metalurgia piloto
  Era III "Tronco"       syn 9-16  — indústria escala; robôs montam robôs
  Era IV  "Copa"         syn 17-27 — soberania: exporta propelente/ciência

Parâmetros = modelo de engenharia, não medições de hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============ Especificações reais do Colosso (Starship v3, Flight 14) ============

COLOSSUS_V3 = {
    "nome": "Starship v3 / Super Heavy",
    "altura_total_m": 124.4,          # stack v3 (~408 ft)
    "altura_blocos_m": {"v1": 121.0, "v3": 124.4},   # varia por bloco
    "diametro_m": 9.0,
    "liftoff_mass_t": 5000.0,         # stack totalmente abastecido
    "ship_altura_m": 52.1,
    "ship_volume_util_m3": 1000.0,    # bay de carga aproximado
    "booster_motores": 33, "ship_motores": 6,   # 3 sea-level + 3 vacuum
    "thrust_liftoff_mn": 80.0,        # ~18M lbf (v3, 33 Raptors)
    "thrust_liftoff_range_mn": (74.0, 80.8),    # 16.7-18.1 Mlbf por bloco
    "prop_stack_t": 4900.0,           # booster ~3400t + ship ~1500t CH4/LOX
    "ship_prop_t": 1500.0,
    "ship_dry_mass_t": 160.0,         # v3 esticada
    "payload_leo_t": 100.0,           # conservador (spec alvo até 200t reuse)
    "payload_leo_reuse_t": (100.0, 150.0),
    "payload_mars_surface_t": 100.0,  # com refueling orbital completo
    "material": "inox 301/304L soldado",
    "tps_tiles": "hexagonais cerâmicas (reentrada)",
    "engine_out": "provado F14: subiu em órbita com 1 Raptor perdido",
    "retorno": "precisa ISRU CH4/LOX — senão o lander fica (e vira base)",

    "booster": {
        "altura_m": 72.3, "propelente_t": 3650.0, "motores": 33,
        "motor": "Raptor 3 — sem tubulações externas, mais confiável",
        "recuperacao": "retorno propulsivo -> captura 'chopsticks' na torre",
    },
    "ship": {
        "altura_m": (50.0, 52.1), "propelente_t": (1200.0, 1600.0),
        "bay_volume_m3": (1000.0, 1100.0),   # maior compartimento da história
        "motores": "3 Raptor SL + 3 Raptor RVac (bocais maiores)",
        "recuperacao": "belly-flop + pouso propulsivo",
    },

    # variantes funcionais — o mesmo colosso, missões diferentes
    "variants": {
        "cargo":  {"porta": "boca-de-jacaré",
                   "missao": "satélites grandes (Starlink V3 deploy hoje, F14)"},
        "crew":   {"capacidade": "até 100 astronautas",
                   "missao": "cabines + suporte de vida + janelas"},
        "hls":    {"contrato": "NASA Artemis — lander lunar tripulado",
                   "diferenca": "SEM flaps nem TPS; motores de pouso p/ regolito lunar"},
        "tanker": {"missao": "petroleiro orbital — refueling em LEO",
                   "papel": "viabiliza Lua/Marte: enche o propellant do ship"},
    },
}


# ============ Mapa de salvamento — cada peça vira ativo da estação ============

SALVAGE_MAP: List[Dict] = [
    {"component": "casco_ship_9m", "mass_frac": 0.55,
     "becomes": "habitat_modules + tanques + estrutura de domo",
     "process": "corte a plasma + re-solda in-situ"},
    {"component": "motores_raptor_x6", "mass_frac": 0.12,
     "becomes": "turbobombas industriais / compressores ISRU / geradores",
     "process": "reconfiguração — turbopump gira em regime industrial"},
    {"component": "tanques_ch4_lox", "mass_frac": 0.10,
     "becomes": "armazenagem de água/propelente/NH3",
     "process": "limpeza criogênica + repressurização"},
    {"component": "tps_tiles", "mass_frac": 0.06,
     "becomes": "revestimento de forno metalúrgico (carboredução 800C)",
     "process": "transferência direta — já são refratários de reentrada"},
    {"component": "flaps_atuadores_x4", "mass_frac": 0.07,
     "becomes": "vigas de domo + braços de guindaste",
     "process": "desmontagem por robôs; atuadores -> juntas de braços"},
    {"component": "avionica_baterias_cabos", "mass_frac": 0.04,
     "becomes": "computadores, rede elétrica, storage da estação",
     "process": "re-deploy direto"},
    {"component": "header_tanks_copvs", "mass_frac": 0.03,
     "becomes": "armazenagem gas alta-pressão (O2/N2/CO2)",
     "process": "re-certificação de pressão"},
    {"component": "misc_estrutura", "mass_frac": 0.03,
     "becomes": "fundamentos, escadas, trilhos, hardware geral",
     "process": "estoque de material de obra"},
]


@dataclass
class ColossusAsBase:
    """Um lander que pousa -> inventário de ativos recuperados.

    Regra soberana: massa_entregue = massa_da_estacao. Nada se perde.
    """

    ships: int = 1

    def salvaged_mass_t(self) -> float:
        """Massa da estrutura da nave (dry mass) aproveitada."""
        return round(self.ships * COLOSSUS_V3["ship_dry_mass_t"], 1)

    def delivered_cargo_t(self) -> float:
        return round(self.ships * COLOSSUS_V3["payload_mars_surface_t"], 1)

    def station_mass_growth_t(self) -> float:
        """Carga útil + casco: cada nave deposita ~260t na superfície."""
        return round(self.delivered_cargo_t() + self.salvaged_mass_t(), 1)

    def asset_inventory(self) -> Dict[str, Dict]:
        return {s["component"]: {"becomes": s["becomes"],
                                 "t_per_ship": round(s["mass_frac"] *
                                 COLOSSUS_V3["ship_dry_mass_t"], 2)}
                for s in SALVAGE_MAP}

    def habitat_volume_m3(self) -> float:
        """Volume pressurizável recuperado por nave (bay + casco parcial)."""
        return round(self.ships * COLOSSUS_V3["ship_volume_util_m3"] * 0.8, 1)


# ============ Robôs humanoides — a força de trabalho ============

HUMANOID_SPEC = {
    "classe": "humanoid (Optimus/Figure-class)",
    "massa_kg": 70.0,
    "altura_m": 1.73,
    "dof": 40,
    "bateria_kwh": 3.0,
    "horas_sol": 16.0,          # sol 24.6h; carga+revisão no restante
    "payload_kg": 20.0,
    "vantagem": "trabalho EVA-free — não precisa traje, suíte ou oxigênio",
    "insumos_importados": ["motores", "atualizadores_chips", "juntas_seladas"],
    "insumos_locais": ["estrutura mars_steel", "cascas basalt_fiber",
                       "baterias molten_salt (NaCl fundido)"],
}

HUMANOID_TASKS = {
    "montagem_estrutura":  {"h_unidade": 8.0,  "skill": "montagem"},
    "manutencao_frota":    {"h_sol_robo": 0.15, "skill": "manutencao"},
    "ensacar_regolito":    {"h_t": 0.5,          "skill": "manual"},
    "estufa_tending":      {"h_m2_sol": 0.02,  "skill": "bio"},
    "solda_casco":         {"h_m": 2.0,         "skill": "montagem"},
    "inspecao":            {"h_sol": 1.0,       "skill": "diagnostico"},
}


@dataclass
class LaborEconomy:
    """Horas de trabalho da frota humanoide por sol, líquidas de
    auto-manutenção. Robôs mantêm robôs — a fração de manutenção cai
    quando a oficina local fabrica partes."""

    n_robots: int = 20
    local_parts_frac: float = 0.4     # cresce por era

    def gross_hours_sol(self) -> float:
        return round(self.n_robots * HUMANOID_SPEC["horas_sol"], 1)

    def maintenance_hours_sol(self) -> float:
        """Horas consumidas mantendo a própria frota; partes locais reduzem."""
        base = self.n_robots * HUMANOID_TASKS["manutencao_frota"]["h_sol_robo"]
        return round(base * (1.5 - self.local_parts_frac), 2)

    def net_hours_sol(self) -> float:
        return round(self.gross_hours_sol() - self.maintenance_hours_sol(), 1)

    def work_capacity(self) -> Dict:
        h = self.net_hours_sol()
        return {"robots": self.n_robots, "gross_h": self.gross_hours_sol(),
                "self_maintenance_h": self.maintenance_hours_sol(),
                "net_h_sol": h,
                "equiv": f"~{round(h/8)} turnos-equivalentes/sol",
                "assembly_m2_sol": round(h / HUMANOID_TASKS['montagem_estrutura']['h_unidade'], 1)}


# ============ Plano de 60 anos (27 synods ~ 57.6 anos) ============

STATION_TIMELINE = [
    {"era": "I_ancoragem", "synods": (0, 3),
     "colossos": 6, "robots_chegam": 40,
     "marcos": ["6 landers pousam e FICAM", "casco vira habitat+tanques",
                "ISRU propelente enche os tanques", "fissão + campo solar",
                "pad sinterizado para os próximos"],
     "metrica": "260t/lander de estacao depositada"},
    {"era": "II_primeira_pele", "synods": (4, 8),
     "colossos": 8, "robots_chegam": 80,
     "marcos": ["domo basalt_glass operacional", "estufa cultivando",
                "metalurgia piloto (aço+geopolímero)", "estufa microbioma",
                "robôs fazem 100% da montagem externa"],
     "metrica": "fração importada < 0.7"},
    {"era": "III_tronco", "synods": (9, 16),
     "colossos": 10, "robots_chegam": 200,
     "marcos": ["oficina fabrica estruturas de robôs locais",
                "metalurgia industrial", "fazendas de regolito classificado",
                "segunda malha de domos", "robo mantém robô (self-repair)"],
     "metrica": "import_fraction < 0.4; frota > 300 unidades"},
    {"era": "IV_copa", "synods": (17, 27),
     "colossos": 12, "robots_chegam": 400,
     "marcos": ["exporta propelente para naves de retorno",
                "ciência de fronteira autônoma", "colônia bio-industrial",
                "a estação produz mais massa/ano que recebe"],
     "metrica": "import_fraction < 0.25 — soberania material"},
]


@dataclass
class StationPlan60:
    """Projeção 50-60 anos: naves acumuladas, frota robô, soberania.

    Cada synod (~780 sols): landers adicionam massa; robôs crescem por
    chegada + montagem local; a fração importada cai (BootstrapCurve).
    """

    from_src: float = 0.34     # t/sol refinado (PowerBudget padrão)
    sols_synod: int = 780

    def synod_snapshot(self, synod: int) -> Dict:
        era = next(e for e in STATION_TIMELINE
                   if e["synods"][0] <= synod <= e["synods"][1])
        # naves acumuladas até o synod (cargo paradas por era)
        ships_landed = sum(e["colossos"] for e in STATION_TIMELINE
                           if e["synods"][0] <= synod)
        base = ColossusAsBase(ships=min(ships_landed, 2 + synod))
        robots = sum(e["robots_chegam"] for e in STATION_TIMELINE
                     if e["synods"][0] <= synod)
        local_prod_t = self.from_src * self.sols_synod * max(1, synod + 1)
        return {"synod": synod, "ano_aprox": round(synod * 780 / 668.6, 1),
                "era": era["era"], "landers": min(ships_landed, 2 + synod * 2),
                "robots_fleet": robots, "station_mass_t": base.station_mass_growth_t(),
                "local_production_t_acum": round(local_prod_t, 0),
                "labor_net_h_sol": LaborEconomy(robots).net_hours_sol()}

    def report(self) -> List[Dict]:
        return [self.synod_snapshot(s) for s in (0, 3, 8, 16, 27)]


# ============ Era V — a primeira geração humana (só quando provada) ============

# Visão do operador: máquinas colonizam ~50 anos; humanos chegam depois,
# reproduzem, e gerações nascem lá. Organização soberana: NÃO por data —
# por GATE medido. A frota deve PROVAR habitabilidade primeiro.

HABITABILITY_GATE = {
    # critérios que a camada maquínica precisa MEDIR antes do 1o humano:
    "radiacao_surface_msv_dia_max": 0.7,      # ~limite aceitável pós-blindagem
    "loop_vida_fechamento_min": 0.98,          # % ar+água reciclados comprovado
    "geracoes_mamiferos_ok_min": 3,            # mamíferos saudáveis NASCIDOS em Marte
    "sols_estufa_estavel_min": 2500,           # ~4 anos terr. de produção contínua
    "energia_kw_redundante_min": 300.0,        # redundância real, não nominal
    "frota_autoreparo_min": 0.85,              # fração de manutenção autônoma
    "alimento_local_frac_min": 0.9,            # dieta quase toda local
}
# Por que mamíferos primeiro: nenhum mamífero foi concebido em Marte.
# A fronteira real não é o foguete — é reprodução em 0.38g + radiação.
# A estação roda isso ANTES: ratos -> primatas -> só então humanos.


@dataclass
class HabitabilityGate:
    """Avalia critérios medidos; humanos embarcam só quando TODOS passam."""

    def evaluate(self, measured: Dict) -> Dict:
        checks = {
            "radiacao": measured.get("radiacao_msv_dia", 9e9)
                        <= HABITABILITY_GATE["radiacao_surface_msv_dia_max"],
            "loop_vida": measured.get("loop_fechamento", 0.0)
                        >= HABITABILITY_GATE["loop_vida_fechamento_min"],
            "mamiferos": measured.get("geracoes_mamiferos", 0)
                        >= HABITABILITY_GATE["geracoes_mamiferos_ok_min"],
            "estufa": measured.get("sols_estufa_estavel", 0)
                        >= HABITABILITY_GATE["sols_estufa_estavel_min"],
            "energia": measured.get("energia_kw_redundante", 0.0)
                        >= HABITABILITY_GATE["energia_kw_redundante_min"],
            "autoreparo": measured.get("frota_autoreparo", 0.0)
                        >= HABITABILITY_GATE["frota_autoreparo_min"],
            "alimento": measured.get("alimento_local_frac", 0.0)
                        >= HABITABILITY_GATE["alimento_local_frac_min"],
        }
        n = sum(checks.values())
        return {"checks": checks, "passed": n, "total": len(checks),
                "habitable": n == len(checks),
                "verdict": ("LIBERADO — embarque humano autorizado" if n == len(checks)
                            else f"{n}/{len(checks)} — camada maquínica ainda não provou")}


# ============ Coortes humanas — chegam depois do gate ============

HUMAN_PHASE = {
    "primeiro_embarque_synod": 17,      # ~ano 31.5 terrestre
    "coorte0": 12,                      # engenheiros+biólogos, não turistas
    "crescimento_por_synod": 2.0,       # coortes dobram até limite de habitat
    "habitat_cap": 400,                 # pessoas sustentáveis (volume+loop)
    "primeira_gravidez_gate": {
        "synod_min": 19,              # ~2 synods após chegada, sob observação
        "exige": "geracoes_mamiferos_ok >= 3 E radiacao < 0.7 mSv/dia"},
}


@dataclass
class HumanCohorts:
    """População humana: coortes importadas + geração nascida em Marte.

    Primeira geração: concepção só após o gate de gravidez — os dados
    dos mamíferos (marcian_evolution) são a premissa exigida.
    """

    def population(self, synod: int, gate_open: bool = True) -> Dict:
        if not gate_open or synod < HUMAN_PHASE["primeiro_embarque_synod"]:
            return {"synod": synod, "humanos": 0, "marcianos_nascidos": 0,
                    "status": "aguardando gate" if not gate_open else "era maquínica"}
        synods_in = synod - HUMAN_PHASE["primeiro_embarque_synod"]
        imported = min(HUMAN_PHASE["coorte0"] * (HUMAN_PHASE["crescimento_por_synod"]
                        ** synods_in), HUMAN_PHASE["habitat_cap"])
        # nascidos: começam após gate de gravidez (synod 19+), coorte pequena
        born = max(0, synod - HUMAN_PHASE["primeira_gravidez_gate"]["synod_min"]) * 4
        return {"synod": synod, "ano_aprox": round(synod * 780 / 668.6, 1),
                "humanos_importados": int(imported),
                "marcianos_nascidos": int(born),
                "populacao_total": int(imported + born),
                "maquinas_por_humano": None}  # preenchido por StationPlan60

    def first_martian_gen(self) -> Dict:
        return {"concepcao_synod": HUMAN_PHASE["primeira_gravidez_gate"]["synod_min"],
                "premissa": "mamíferos modelaram gestação 0.38g OK",
                "simbolo": "primeira criança nascida fora da Terra — "
                           "a estação vira lar, não posto avançado"}
