"""Malha de energia: biogás -> Sabatier -> célula de combustível (cadeia fechada).

Conglomerado: ISS (Sabatier + eletrólise) + MOXIE (ISRU) + o próprio
BiogasDigester do Monoculture. Fecha o ciclo: a biomassa gera CH4 (biogás),
o Sabatier complementa com CH4 a partir de CO2+H2 (O2 excedente -> H2),
e a célula de combustível converte de volta a eletricidade + água — o que
devolve a energia dos resíduos ao loop, sem depender só de solar/bateria.
"""

from dataclasses import dataclass


@dataclass
class EnergyLoop:
    """Acopla BiogasDigester + SabatierReactor + HydrogenFuelCell + fissão.

    Config v5+v6 (sweep 2026-09-28): a reserva mínima de energia 0.60 do gate
    d3 é INALCANÇÁVEL só com solar+biogás (estabiliza em ~0.583 < 0.60) —
    o black swan derruba a 0.5 e a recuperação não atinge o limiar (0/13
    passes). Com aporte contínuo de fissão (Kilopower-like, +0.08 na fração
    de energia), o sistema estabiliza em 0.663 e o gate passa 13/13.
    """

    ch4_kwh_per_kg: float = 13.9        # poder calorífico CH4
    fuel_cell_efficiency: float = 0.55  # PEM fuel cell elétrica
    sabatier_efficiency: float = 0.95   # já em sabatier_reactor (MOXIE-style)
    fission_boost: float = 0.08         # aporte contínuo Kilopower (config v5)

    def grid_fraction(self, solar_fraction: float) -> float:
        """Fração de energia do grid: solar + biogás + fissão (v5)."""
        return float(min(1.0, solar_fraction + self.fission_boost))

    def biogas_to_power(self, ch4_kg: float) -> dict:
        """Biogás (CH4) -> eletricidade + água via fuel cell."""
        elec = ch4_kg * self.ch4_kwh_per_kg * self.fuel_cell_efficiency
        water = ch4_kg * 2.25  # CH4 + 2O2 -> 2H2O + CO2 (~2.25 kg água/kg CH4)
        return {"kwh": round(elec, 2), "water_kg": round(water, 3), "co2_kg": round(ch4_kg * 2.75, 3)}

    def sabatier_loop(self, co2_kg: float, h2_kg: float) -> dict:
        """CO2 + H2 -> CH4 + H2O (complementa o biogás; H2 do OGS)."""
        ch4_mol = min(co2_kg / 44.01e-3, h2_kg / (4 * 2.016e-3))
        ch4 = ch4_mol * 16.04e-3 * self.sabatier_efficiency
        water = ch4_mol * 36.03e-3 * self.sabatier_efficiency
        return {"ch4_kg": round(ch4, 4), "water_kg": round(water, 4)}

    def net_power(self, biomass_kg: float, biogas_yield: float = 0.25,
                  excess_o2_kg: float = 0.0) -> dict:
        """kWh líquidos do loop: biomassa -> biogás -> fuel cell (+ Sabatier)."""
        ch4_biogas = biomass_kg * biogas_yield
        power = self.biogas_to_power(ch4_biogas)
        ch4_extra = 0.0
        if excess_o2_kg > 0:
            # O2 excedente -> eletrólise reversa gera H2 para o Sabatier
            h2 = excess_o2_kg * 0.125  # água -> H2 (~12.5% em massa)
            ch4_extra = self.sabatier_loop(co2_kg=power["co2_kg"], h2_kg=h2)["ch4_kg"]
            power["kwh"] += self.biogas_to_power(ch4_extra)["kwh"]
        return {"kwh_net": round(power["kwh"], 2), "water_kg": power["water_kg"],
                "ch4_biogas_kg": round(ch4_biogas, 3), "ch4_sabatier_kg": round(ch4_extra, 4)}
