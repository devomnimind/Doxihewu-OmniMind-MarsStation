"""Mars Mutagenesis & Consortia — a ponte Dr. Stone -> Marte.

O que a refinaria produz vira FERRAMENTA biológica e industrial:

  Nital (HNO3+etanol)  -> mutagênese química dirigida: HNO3 nitrata bases
    (G -> 8-nitroguanina); etanol permeabiliza membrana; perclorato gera
    ROS que amplifica. Dose-controlável (vs radiação) — modula o
    mutation_sd dos modelos de evolução (marcian_evolution).
    HNO3 in-situ: N2 atmosférico marciano (2.7%) + H2O via processo
    plasma (Birkeland-Eyde análogo).
  Gesso -> S -> H2SO4  -> contact process: 2SO2+O2->2SO3; SO3+H2O->H2SO4.
    H2SO4 -> baterias Fe-S (~100 Wh/kg, -70C ok), fertilizante (NH4)2SO4.
  Ca(ClO4)2 + Al       -> propelente sólido (ISP ~250 s, análogo AP).
  SiO2 -> vidro        -> cúpulas, cobertura UV de painéis, fibra óptica.
  Consórcio microbiano -> fixadores N2 + redutores de perclorato +
    solubilizadores de P + decompositores; HGT transfere genes
    (pcrABC, nifHDK, phoAB) — o regolito estéril vira solo.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List


# ============ Nital: mutagênese química dirigida ============

@dataclass
class NitalMutagen:
    """HNO3 + etanol — mutagênico de dose controlada (nitratação de DNA).

    hno3_conc: fração (0.30 = Dr. Stone, mas 0.05-0.10 já mutagênico).
    ethanol: permeabiliza membrana -> aumenta uptake.
    perchlorate_mM: ROS oxidação extra — sinergia marciana.
    """

    hno3_conc: float = 0.30
    ethanol: float = 0.70
    perchlorate_mM: float = 0.0

    def mutation_rate(self) -> float:
        """Taxa efetiva por indivíduo/geração."""
        base = self.hno3_conc * 0.05                 # ~5% por fração HNO3
        permeability = 1.0 + self.ethanol * 0.5
        ros_factor = 1.0 + self.perchlorate_mM / 2.4 * 0.5
        return min(0.95, base * permeability * ros_factor)

    def mutation_sd_multiplier(self) -> float:
        """Escala o mutation_sd do modelo de evolução (dose -> tamanho do passo)."""
        return 1.0 + self.mutation_rate() * 4.0

    def hno3_synthesis_energy_kwh(self, kg: float) -> float:
        """HNO3 in-situ de N2 atmosférico (2.7% em CO2) — plasma + absorção.
        ~11 kWh/kg (fixação de N2 é cara: ~60 kWh/kg N2 -> HNO3 diluído)."""
        return kg * 11.0


@dataclass
class MutagenesisExperiment:
    """Roda evolução sob mutagênio Nital vs controle — convergência medida."""

    mutagen: NitalMutagen = field(default_factory=NitalMutagen)

    def run(self, model, n_generations: int = 300, seed: int = 5) -> Dict:
        """model: qualquer dataclass com evolve(n_generations, seed) e
        mutation_sd (CircadianEntrainment, MachinePlantSymbiosis...)."""
        import copy
        ctrl = copy.deepcopy(model)
        treated = copy.deepcopy(model)
        treated.mutation_sd = model.mutation_sd * self.mutagen.mutation_sd_multiplier()
        c = ctrl.evolve(n_generations, seed)
        t = treated.evolve(n_generations, seed)
        return {"control": c, "nital": t,
                "mutation_sd_boost": round(self.mutagen.mutation_sd_multiplier(), 3),
                "mutation_rate": round(self.mutagen.mutation_rate(), 4)}


# ============ Cadeias Dr. Stone -> Marte (calculadoras) ============

def gypsum_to_sulfuric(gesso_kg: float, eff_s: float = 0.70,
                       eff_ox: float = 0.90) -> Dict[str, float]:
    """CaSO4.2H2O -> S (Claus) -> H2SO4 (contact). 43 kg -> ~6.4 kg S -> ~19 kg H2SO4."""
    s_kg = gesso_kg / 172.0 * 32.0 * eff_s
    h2so4_kg = s_kg / 32.0 * 98.0 * eff_ox
    return {"sulfur_kg": round(s_kg, 3), "h2so4_kg": round(h2so4_kg, 3)}


def perchlorate_al_propellant(perchlorate_kg: float, al_kg: float) -> Dict:
    """3Ca(ClO4)2 + 16Al -> 3CaCl2 + 8Al2O3. ISP ~250 s (análogo NH4ClO4/Al)."""
    mol_p, mol_a = perchlorate_kg * 1000 / 239.0, al_kg * 1000 / 27.0
    ratio = mol_a / max(mol_p, 1e-9)
    limiting = "Al" if ratio < 16 / 3 else "Ca(ClO4)2"
    mol_rxn = mol_a / 16.0 if limiting == "Al" else mol_p / 3.0
    energy_kj = mol_rxn * 2500.0
    return {"limiting": limiting, "energy_kj": round(energy_kj, 1),
            "isp_s": 250, "propellant_kg": round(perchlorate_kg + al_kg, 3)}


def silica_to_glass(silica_kg: float, eff: float = 0.90) -> float:
    """SiO2 + Na2O + CaO -> vidro sodalime. 261 kg SiO2 -> ~196 kg vidro."""
    mol_si = silica_kg * 1000 / 60.08
    return round(mol_si / 6.0 * 478.0 / 1000 * eff, 2)


def isru_energy_budget(process_kwh_kg: float, mass_kg: float,
                       n_panels: int = 10) -> Dict[str, float]:
    """Solar 1.02 kWh/painel/sol (200W x 6h x .85) vs fissão 10 kWe."""
    need = process_kwh_kg * mass_kg
    return {"energy_kwh": round(need, 1),
            "sols_solar": round(need / (n_panels * 1.02), 1),
            "sols_fission_10kwe": round(need / 240.0, 1)}


# ============ Consórcio microbiano — solo marciano ============

@dataclass
class MicrobiomeConsortium:
    """Inóculo funcional: o que transforma regolito estéril em solo.

    Fixadores N2 (Rhizobium/Azospira), redutores de perclorato
    (Dechloromonas — pcrABC), solubilizadores de P, decompositores.
    HGT transfere genes entre grupos — a arca já evoluiu pcr/cld.
    """

    groups: Dict[str, List[str]] = field(default_factory=lambda: {
        "nitrogen_fixers": ["Azospira_oryzae", "Rhizobium"],
        "perchlorate_reducers": ["Dechloromonas", "Azospira"],
        "phosphate_solubilizers": ["Bacillus", "Pseudomonas"],
        "decomposers": ["Aspergillus", "Penicillium"]})
    hgt_genes: Dict[str, List[str]] = field(default_factory=lambda: {
        "perchlorate_reductase": ["pcrA", "pcrB", "pcrC"],
        "chlorite_dismutase": ["cld"],
        "nitrogenase": ["nifH", "nifD", "nifK"],
        "phosphatase": ["phoA", "phoB"]})
    density: float = 0.1          # fração de solo colonizado

    def fertility_rate(self, perchlorate_ppm: float) -> float:
        """Taxa de solo-fértil por sol: microbioma cresce, perclorato limita."""
        detox = sum(1 for g in self.groups["perchlorate_reducers"]) * 0.02
        tox = max(0.0, 1.0 - perchlorate_ppm / 5000.0)
        return self.density * 0.03 * tox * (1.0 + detox)

    def series(self, n_sols: int, clo4_series: List[float],
               mutagen: NitalMutagen | None = None, seed: int = 9) -> Dict:
        rng = random.Random(seed)
        fert = 0.0
        out = {"fertile_soil_frac": [], "microbiome_density": [],
               "hgt_events": [], "mutation_pressure": []}
        for t in range(n_sols):
            clo4 = clo4_series[t] if t < len(clo4_series) else 0.0
            mp = mutagen.mutation_rate() if mutagen else 0.0
            self.density = min(1.0, self.density + self.fertility_rate(clo4 * 1e4))
            fert = min(1.0, fert + self.fertility_rate(clo4 * 1e4) * 0.1)
            hgt = 1 if rng.random() < mp * 0.3 else 0
            out["fertile_soil_frac"].append(round(fert, 4))
            out["microbiome_density"].append(round(self.density, 4))
            out["hgt_events"].append(hgt)
            out["mutation_pressure"].append(round(mp, 4))
        return out
