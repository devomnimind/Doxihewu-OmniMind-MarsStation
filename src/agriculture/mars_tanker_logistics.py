"""Mars Tanker Logistics — arquitetura tanker -> cargo -> Marte.

A pergunta operacional: quantos tankers por cargo ship por janela?

Física honesta (COLOSSUS_V3 + equação de foguete):
  - Ship sai da Terra quase vazio de propelente orbital:
    booster queima os ~3650t só para por o ship em LEO.
  - Para TMI (trans-Mars injection) o ship precisa de propelente
    completo ~1500t: ~3.6-4.5 km/s de queima + reserva de pouso EDL.
  - O propelente sobe em TANKERS: cada tanker entrega ~100-150t em LEO
    e retorna. Boiloff criogênico cobra taxa por dia de campanha.
  - Janelas de transferência: a cada synod (~26 meses), abertura ~60 dias.

Resultado do modelo: ~9-11 tankers por cargo ship v3 (boiloff incluído),
lançados em cadência ~semanal dentro da janela.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


# ============ Constantes do veículo (COLOSSUS_V3 / ship block) ============

SHIP_DRY_T = 160.0            # v3 esticada
SHIP_PROP_CAP_T = 1500.0      # tanque do ship (1200-1600 por bloco)
SHIP_RESIDUAL_LEO_T = 200.0   # o que sobra em LEO após a subida
PAYLOAD_MARS_T = 100.0        # carga na superfície marciana
LANDING_RESERVE_T = 120.0     # propelente guardado p/ pouso propulsivo final

RVAC_ISP_S = 380.0            # Raptor vacuum, segundos
G0 = 9.80665

TANKER_DELIVERY_T = 110.0     # propelente útil que um tanker transfere em LEO
                             # (payload menos margem docking/ullage)
BOILOFF_FRAC_DAY = 0.0005     # ~0.05%/dia com sombreamento ativo (metano)
SYNOD_MONTHS = 25.6           # janela de transferência Terra->Marte
WINDOW_DAYS = 60              # campanha útil por janela


# ============ Orçamento TMI — quanto propelente o ship precisa ============

@dataclass
class TMIBudget:
    """Propelente necessário na partida para injeção trans-Marte.

    dv_TMI = Isp*g0*ln(m0/m1). m1 = dry + payload + landing_reserve.
    Fast transit (menos dias no espaço, menos radiação) pede mais dv.
    """

    dv_kms: float = 3.8        # 3.6 mínimo econômico; 4.3+ fast transit
    dry_t: float = SHIP_DRY_T
    payload_t: float = PAYLOAD_MARS_T
    landing_reserve_t: float = LANDING_RESERVE_T

    def prop_needed_t(self) -> float:
        m1 = self.dry_t + self.payload_t + self.landing_reserve_t
        ratio = math.exp(self.dv_kms * 1000 / (RVAC_ISP_S * G0))
        return round(m1 * (ratio - 1), 1)

    def departure_mass_t(self) -> float:
        """Massa total do ship ao acender os motores para Marte."""
        return round(self.dry_t + self.payload_t + self.prop_needed_t()
                     + self.landing_reserve_t, 1)

    def report(self) -> Dict:
        return {"dv_kms": self.dv_kms,
                "prop_tmi_t": self.prop_needed_t(),
                "departure_mass_t": self.departure_mass_t(),
                "tank_capacity_t": SHIP_PROP_CAP_T,
                "fits_tank": self.prop_needed_t() + self.landing_reserve_t
                             <= SHIP_PROP_CAP_T}


# ============ Frota tanker — quantos voos para encher um ship ============

@dataclass
class TankerCampaign:
    """Campanha de reabastecimento dentro de uma janela sinódica.

    O ship parte com residual ~200t; precisa chegar a
    landing_reserve + prop_tmi. Cada tanker entrega TANKER_DELIVERY_T,
    mas o propelente já transferido evapora a BOILOFF_FRAC_DAY por dia
    enquanto a campanha demora — cadência é tudo.
    """

    dv_kms: float = 3.8
    cadence_days: float = 5.0      # um tanker a cada N dias (reuso do booster)
    boiloff_frac_day: float = BOILOFF_FRAC_DAY
    delivery_t: float = TANKER_DELIVERY_T

    def target_prop_t(self) -> float:
        return TMIBudget(dv_kms=self.dv_kms).prop_needed_t() + LANDING_RESERVE_T

    def n_tankers(self) -> Dict:
        """Itera a campanha: a cada tanker, propelente sobe delivery e
        evapora o acumulado pelos dias de espera até o próximo."""
        need = self.target_prop_t()
        prop = SHIP_RESIDUAL_LEO_T
        n, days = 0, 0.0
        while prop < need and n < 50:
            prop += self.delivery_t
            prop *= (1 - self.boiloff_frac_day) ** self.cadence_days
            n += 1
            days += self.cadence_days
        return {"n_tankers": n, "campaign_days": round(days, 1),
                "prop_at_departure_t": round(prop, 1),
                "target_t": need, "fits_window": days <= WINDOW_DAYS,
                "boiloff_losses_t": round(n * self.delivery_t * self.boiloff_frac_day
                                        * self.cadence_days, 1)}

    def sensitivity(self) -> List[Dict]:
        """Como o número de tankers muda com dv e cadência — o eixo real
        da arquitetura (janela rápida = mais propelente = mais tankers)."""
        rows = []
        for dv in (3.4, 3.8, 4.3):
            for cad in (3.0, 5.0, 10.0):
                c = TankerCampaign(dv_kms=dv, cadence_days=cad)
                r = c.n_tankers()
                rows.append({"dv_kms": dv, "cadence_d": cad,
                             "tankers": r["n_tankers"],
                             "days": r["campaign_days"],
                             "fits_window": r["fits_window"]})
        return rows


# ============ Janela sinódica — a arquitetura inteira por ciclo ============

@dataclass
class SynodWindow:
    """Uma janela Terra->Marte: quantos cargo ships saem e quantos
    tankers a constelação precisa voar no total."""

    cargo_ships: int = 2          # landers que ficam (viram estação)
    dv_kms: float = 3.8
    cadence_days: float = 5.0

    def launches(self) -> Dict:
        per_ship = TankerCampaign(dv_kms=self.dv_kms,
                                  cadence_days=self.cadence_days).n_tankers()
        tankers = per_ship["n_tankers"] * self.cargo_ships
        total = tankers + self.cargo_ships   # + os próprios cargos
        days = per_ship["campaign_days"]
        return {"cargo_ships": self.cargo_ships,
                "tankers_per_ship": per_ship["n_tankers"],
                "tanker_launches": tankers,
                "total_launches": total,
                "campaign_days": days,
                "launches_per_week": round(total / (days / 7), 1),
                "mass_delivered_t": self.cargo_ships * PAYLOAD_MARS_T,
                "propellant_lifted_t": round(tankers * TANKER_DELIVERY_T, 1)}

    def fleet_plan(self, n_synods: int = 6, ramp: List[int] = None) -> List[Dict]:
        """Crescimento por janela: mais ships por synod conforme a
        cadência de produção de Raptor/booster escala."""
        ramp = ramp or [2, 2, 4, 4, 6, 8]
        return [{"synod": s, "ano_aprox": round(s * SYNOD_MONTHS / 12, 1),
                 **{k: v for k, v in
                    SynodWindow(cargo_ships=ramp[min(s, len(ramp)-1)],
                                dv_kms=self.dv_kms,
                                cadence_days=self.cadence_days).launches().items()}}
                for s in range(n_synods)]


# ============ E o lado de Marte — o espelho ISRU ============

@dataclass
class MarsRefuelMirror:
    """O retorno precisa do mesmo enchimento — mas vindo do SOLO:
    a planta ISRU da estação é o 'tanker marciano'. Amarra a
    arquitetura ao PowerBudget/BootstrapCurve (resources surface).
    """

    isru_t_per_sol: float = 0.34        # refino atual (PowerBudget)
    prop_yield_frac: float = 0.30       # fração do refino que vira propelente
    ship_prop_t: float = SHIP_PROP_CAP_T

    def sols_to_fill_one_ship(self) -> float:
        """Sols de produção ISRU para encher um ship de retorno."""
        daily = self.isru_t_per_sol * self.prop_yield_frac * 1000  # kg->t
        return round(self.ship_prop_t / (daily / 1000), 0)

    def return_fleet_capacity(self, ships_returning: int) -> Dict:
        sols = self.sols_to_fill_one_ship() * ships_returning
        return {"ships": ships_returning, "sols_needed": sols,
                "synods_needed": round(sols / 780, 1),
                "verdict": "ISRU e o gargalo do retorno — a estacao precisa "
                           "escalar prop producao ANTES de querer devolver naves"}
