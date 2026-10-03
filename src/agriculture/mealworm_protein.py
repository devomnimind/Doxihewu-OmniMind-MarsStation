"""Mealworm (Tenebrio molitor) — proteína animal do fechamento alimentar.

Conglomerado de Lunar Palace 1 (LP365): os mealworms convertem resíduos
vegetais (casca/folha não-comestível) em proteína animal — a única fonte de
proteína integral no ecossistema fechado que atingiu ~100% de comida em 370
dias. Cobre a lacuna do Monoculture (só proteína vegetal/algácea).
"""

from dataclasses import dataclass


@dataclass
class MealwormFarm:
    """Criação de Tenebrio molitor sobre resíduo vegetal não-comestível."""

    feed_conversion_ratio: float = 0.30   # kg biomassa inseto / kg resíduo seco
    protein_fraction: float = 0.50        # ~50% proteína (seco, LP1)
    harvest_days: int = 40                # ciclo larva->colheita
    population_density_kg_m2: float = 2.0

    def __post_init__(self):
        self.biomass_kg: float = 0.0
        self.harvest_cycle_kg: float = 0.0

    def feed(self, plant_residue_kg: float, area_m2: float = 10.0) -> float:
        """Alimenta os mealworms com resíduo; retorna biomassa ganha."""
        gain = max(0.0, plant_residue_kg) * self.feed_conversion_ratio
        capacity = self.population_density_kg_m2 * area_m2
        self.biomass_kg = min(capacity, self.biomass_kg + gain)
        return gain

    def harvest(self) -> dict:
        """Colheita do ciclo: proteína disponível (kg)."""
        harvest_kg = self.biomass_kg * 0.7   # ~70% da biomassa colhida por ciclo
        self.biomass_kg *= 0.3               # 30% reprodutores
        protein = harvest_kg * self.protein_fraction
        self.harvest_cycle_kg = harvest_kg
        return {"biomass_kg": round(harvest_kg, 3),
                "protein_kg": round(protein, 3),
                "cycle_days": self.harvest_days}

    def protein_per_day(self, residue_kg_day: float, area_m2: float = 10.0) -> float:
        """Proteína média diária sob alimentação contínua (kg/dia)."""
        gain_day = residue_kg_day * self.feed_conversion_ratio
        capacity_gain = self.population_density_kg_m2 * area_m2 / self.harvest_days
        biomass_day = min(gain_day, capacity_gain)
        return biomass_day * 0.7 * self.protein_fraction
