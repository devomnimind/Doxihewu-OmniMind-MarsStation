"""SabatierReactor — CO2 + 4H2 -> CH4 + 2H2O (gap_6, MOXIE-derivado).

MARS_SYSTEM_CONTRACT.yaml · missing_build_specs_critical.gap_6

Reação de Sabatier (300-400°C, catalisador Ni/Al2O3): metano combustível +
água, a partir de CO2 atmosférico marciano (95%) + H2 de eletrólise.
Estoque de CH4 alimenta fuel cells e elevadores; H2O fecha o ciclo da água.
"""

from __future__ import annotations

# Massas molares (g/mol)
M_CO2, M_H2, M_CH4, M_H2O = 44.0, 2.0, 16.0, 18.0


class SabatierReactor:
    """Reator Sabatier: CO2 + 4H2 -> CH4 + 2H2O (Ni/Al2O3, 350°C, 95%)."""

    def __init__(self, catalyst: str = "Ni/Al2O3", temp_c: float = 350.0,
                 pressure_bar: float = 5.0, efficiency: float = 0.95) -> None:
        self.catalyst = catalyst
        self.temp_c = temp_c
        self.pressure_bar = pressure_bar
        self.efficiency = efficiency
        self.ch4_stock_kg = 0.0
        self.h2o_produced_kg = 0.0
        self.runs = 0

    def process(self, co2_kg: float, h2_kg: float) -> dict:
        """Processa CO2 e H2; retorna CH4 e H2O produzidos (limites por reagente)."""
        if co2_kg <= 0 or h2_kg <= 0:
            return {"ch4_kg": 0.0, "h2o_kg": 0.0, "limiting": None}
        # estequiometria: 1 mol CO2 (44g) + 4 mol H2 (8g) -> 1 mol CH4 (16g) + 2 mol H2O (36g)
        mols_co2 = co2_kg * 1000.0 / M_CO2
        mols_h2 = h2_kg * 1000.0 / M_H2
        limiting_mol = min(mols_co2, mols_h2 / 4.0)
        ch4_kg = limiting_mol * M_CH4 / 1000.0 * self.efficiency
        h2o_kg = limiting_mol * M_H2O * 2.0 / 1000.0 * self.efficiency
        self.ch4_stock_kg += ch4_kg
        self.h2o_produced_kg += h2o_kg
        self.runs += 1
        return {"ch4_kg": ch4_kg, "h2o_kg": h2o_kg,
                "limiting": "co2" if mols_co2 < mols_h2 / 4.0 else "h2"}
