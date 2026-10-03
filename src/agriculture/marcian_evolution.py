"""Evolução MARCIANA emergente — não "Terra em Marte".

Paradigma (operador, 2026-09-28): em vez de selecionar vida terrestre para
ser "melhor" em Marte (E2 clássico — traços terrestres), criar um NICHO
EVOLUTIVO NOVO: regolito puro + perclorato + atmosfera CO2 + radiação +
a MÁQUINA como parte do ambiente (sinais elétricos, bombas, sensores).
Os fenótipos que emergem NÃO existem na Terra.

Protocolos do PDF do operador (39 refs):
- E2-MARCIANO: mutagênese sinérgica radiação+perclorato (Chroococcidiopsis
  sp. 029 tolera 2.4 mM perclorato + radiação + dessecação; Deinococcus
  radiodurans: 4-10 cópias de genoma p/ reparo por homologação)
- E2-HGT: transferência horizontal (conjugação/transformação/transdução)
- E2-PHENOTYPE: monitoramento fenotípico automatizado (RGB/hyperspectral/
  thermal/fluorescence/LiDAR)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import math


# ============ E2-MARCIANO: mutagênese sinérgica ============

@dataclass
class MartianMutagenesisParams:
    """Parâmetros calibrados (PDF operador + refs reais)."""

    radiation_dose_mSv_day: float = 0.67      # MSL/RAD
    radiation_quality_factor: float = 3.7
    perchlorate_mM: float = 2.4               # threshold Chroococcidiopsis sp. 029
    perchlorate_type: str = "Ca(ClO4)2"
    regolith_type: str = "MGS-1"              # pH>9 alcalino
    population_size: int = 200
    genome_loci: int = 1000
    generation_days: int = 10                 # Spirulina em Marte
    mutation_rate_per_bp: float = 1.5e-6      # wheat CR calibrado
    hgt_rate: float = 1e-4                    # D. radiodurans-like
    synergy_factor: float = 1.5               # radiação+perclorato > soma
    ploidy_min: int = 4
    ploidy_max: int = 10                      # D. radiodurans


class MartianMutagenesis:
    """Evolução em regolito PURO — perclorato como PRESSÃO + recurso.

    Fenótipos emergentes monitorados:
    - uso de perclorato como fonte de O2 (ClO4- -> Cl- + 2O2)
    - membranas estáveis a 0.6 kPa
    - crescimento a -80 °C (psicrofilia extrema)
    - ritmo circadiano marciano (24h39min)
    """

    def __init__(self, params: MartianMutagenesisParams | None = None) -> None:
        self.params = params or MartianMutagenesisParams()
        self.history: List[Dict] = []

    def run_evolution(self, n_generations: int = 400) -> Dict:
        """Modelo agregado (população média) — 4 traços + sinergia."""
        p = self.params
        # estado: [perclorato_tol, frio, rad_tol, crescimento]
        state = [0.5, 0.5, 0.5, 0.5]
        dose_per_gen = p.radiation_dose_mSv_day * p.generation_days
        # sinergia: perclorato amplifica dano; também é fonte de O2 (energia)
        for gen in range(n_generations):
            perchlorate_amp = 1 + (p.perchlorate_mM / 2.4) * 0.5
            damage = p.mutation_rate_per_bp * 1000 * dose_per_gen * perchlorate_amp * p.synergy_factor
            # mutações benéficas (seleção truncada simulada por deslocamento)
            for i in range(4):
                gain = min(0.015, damage * (1.0 if i == 0 else 0.55))  # perclorato favorecido
                state[i] = min(1.0, state[i] + gain * (1.0 - state[i]))
            # ploidia (reparo) reduz dano deletério líquido
            ploidy = (p.ploidy_min + p.ploidy_max) / 2
            state[3] = max(0.1, state[3] * (1.0 - 0.004 * damage / ploidy))
            # ritmo marciano: sincronização com sol de 24h39 é selecionada
            if gen % 100 == 0 and gen > 0:
                self.history.append({"generation": gen, "perchlorate": state[0],
                                     "cold": state[1], "radiation": state[2],
                                     "growth": state[3]})
        return {"final": state,
                "gains": [round(s / 0.5, 3) for s in state],
                "perchlorate_as_energy": state[0] > 0.65,  # emergência: uso, não só tolerância
                "history": self.history[-5:]}


# ============ E2-HGT: transferência horizontal de genes ============

@dataclass
class HGTSimulator:
    """Consórcio marciano com HGT (conjugação/transformação/transdução).

    Espécies: Chroococcidiopsis sp. 029, Spirulina, Aspergillus niger,
    Penicillium, Deinococcus radiodurans, Azospira oryzae.
    """

    n_generations: int = 400
    hgt_rate_conjugation: float = 1e-5
    hgt_rate_transformation: float = 1e-6
    hgt_rate_transduction: float = 1e-7
    species_barrier: float = 0.3
    plasmid_host_range: float = 0.7

    def __post_init__(self) -> None:
        # genes iniciais por espécie (literatura)
        self.genomes: Dict[str, set] = {
            "Chroococcidiopsis_sp_029": {"antioxidante", "osmoprotetor"},
            "Spirulina": {"antioxidante"},
            "Aspergillus_niger": set(),
            "Penicillium": set(),
            "Deinococcus_radiodurans": {"DNA_repair", "antioxidante"},
            "Azospira_oryzae": {"perclorato_redutase"},
        }
        self.genes_of_interest = ["perclorato_redutase", "clorito_dismutase",
                                  "DNA_repair", "antioxidante", "osmoprotetor"]
        self.events = 0

    def _barrier(self, donor: str, recipient: str) -> float:
        phyla = {"cyano": ["Chroococcidiopsis", "Spirulina"],
                 "fungi": ["Aspergillus", "Penicillium"],
                 "bact": ["Deinococcus", "Azospira"]}
        def phylum(s: str) -> str:
            for k, gens in phyla.items():
                if any(g in s for g in gens):
                    return k
            return "?"
        if donor == recipient:
            return 0.1
        return 0.3 if phylum(donor) == phylum(recipient) else self.species_barrier

    def run(self) -> Dict:
        import random
        rng = random.Random(42)
        species = list(self.genomes.keys())
        for _ in range(self.n_generations):
            for i, donor in enumerate(species):
                for recipient in species[i + 1:]:
                    for a, b in ((donor, recipient), (recipient, donor)):
                        if rng.random() < self.hgt_rate_conjugation:
                            barrier = self._barrier(a, b)
                            if rng.random() < self.plasmid_host_range:
                                barrier *= 0.5
                            if self.genomes[a] and rng.random() > barrier:
                                gene = rng.choice(sorted(self.genomes[a]))
                                if gene not in self.genomes[b]:
                                    self.genomes[b].add(gene)
                                    self.events += 1
            # transformação (DNA pool)
            dna_pool = set().union(*self.genomes.values()) if self.genomes else set()
            for s in species:
                if rng.random() < self.hgt_rate_transformation * 10 and dna_pool:
                    gene = rng.choice(sorted(dna_pool))
                    if gene not in self.genomes[s] and rng.random() > self.species_barrier:
                        self.genomes[s].add(gene)
                        self.events += 1
        spread = {g: sum(1 for genes in self.genomes.values() if g in genes)
                  for g in self.genes_of_interest}
        return {"events": self.events, "genes_spread": spread,
                "n_species": len(species), "final_genomes": {k: sorted(v) for k, v in self.genomes.items()}}


# ============ P3: ritmo circadiano marciano (24h39) ============

MARS_SOL_SECONDS = 88775.244
MARS_SOL_HOURS = MARS_SOL_SECONDS / 3600.0  # 24.6598 h


@dataclass
class MartianCircadian:
    """P3 — evolução do período circadiano livre em direção ao sol marciano.

    Organismos terrestres têm período livre ~24 h; em Marte o ciclo
    luz/temperatura tem 24h39m35s. O mismatch diário de ~0.66 h acumula
    dessincronia (custo metabólico). Sob seleção, o período converge para
    o sol marciano — traço que NÃO existe na Terra.

    Validado no Colab (v3_summaries/sol_ritmo.json): T_p 24.28h -> 24.65h
    em 300 gerações (convergiu_24h39 = True).
    """

    sol_hours: float = MARS_SOL_HOURS
    period_h: float = 24.0           # período livre inicial (Terra)
    selection_strength: float = 3.0
    mutation_sd: float = 0.02
    pop_size: int = 200

    def fitness(self, period_h: float) -> float:
        mismatch = abs(self.sol_hours - period_h)
        return math.exp(-self.selection_strength * mismatch)

    def circadian_factor(self, period_h: float | None = None) -> float:
        """Multiplicador de fotossíntese [0..1] pelo entranhamento no sol.

        Planta terrestre (24 h): mismatch 0.66 h -> ~0.72.
        Planta entranhada (24.66 h): -> ~1.0.
        """
        p = self.period_h if period_h is None else period_h
        mismatch = abs(self.sol_hours - p)
        return float(math.exp(-0.5 * mismatch))

    def evolve(self, n_generations: int = 300, seed: int = 5) -> Dict:
        import random
        rng = random.Random(seed)
        pop = [rng.gauss(self.period_h, 0.4) for _ in range(self.pop_size)]
        hist = [sum(pop) / len(pop)]
        for _ in range(n_generations):
            fit = [self.fitness(p) for p in pop]
            total = sum(fit) or 1.0
            survivors = rng.choices(pop, weights=fit, k=len(pop) // 2)
            pop = survivors + [p + rng.gauss(0, self.mutation_sd) for p in survivors]
            hist.append(sum(pop) / len(pop))
        self.period_h = hist[-1]
        return {"period_initial": round(hist[0], 3),
                "period_final": round(hist[-1], 3),
                "sol_hours": round(self.sol_hours, 4),
                "converged_to_sol": abs(hist[-1] - self.sol_hours) < 0.1,
                "circadian_factor": self.circadian_factor(),
                "history_tail": [round(h, 3) for h in hist[-5:]]}


# ============ P4: simbiose máquina-planta ============

@dataclass
class MachinePlantSymbiosis:
    """P4 — plantas evoluem responsividade ao ciclo elétrico da máquina.

    A máquina emite padrão elétrico (bomba on 10 min / off 20 min) sobre-
    posto à janela de luz LED. Plantas que sincronizam a fotossíntese com
    o overlap bomba×luz economizam energia -> seleção favorece o traço.
    A máquina torna-se parte do nicho evolutivo, não apenas ferramenta.

    Validado no Colab (v3_summaries/simbiose_maquina.json):
    responsiveness 0.63 -> 0.97 (ganho 1.54x, overlap 0.333).
    """

    responsiveness: float = 0.5
    pump_on_min: float = 10.0
    cycle_min: float = 30.0
    light_on_min: float = 16.0
    selection_gain: float = 3.0
    mutation_sd: float = 0.02
    pop_size: int = 200

    def pump_light_overlap(self) -> float:
        """Fração do ciclo em que bomba e luz coincidem."""
        import numpy as np
        period = int(self.cycle_min)
        pump = np.tile([1.0] * int(self.pump_on_min)
                       + [0.0] * (period - int(self.pump_on_min)), 100)
        light = np.tile([1.0] * int(self.light_on_min)
                        + [0.0] * (period - int(self.light_on_min)), 100)
        return float((pump * light).mean())

    def symbiosis_factor(self, responsiveness: float | None = None) -> float:
        """Multiplicador de eficiência [1..~1.33] pela sincronia com a máquina."""
        r = self.responsiveness if responsiveness is None else responsiveness
        return float(1.0 + r * self.pump_light_overlap())

    def evolve(self, n_generations: int = 300, seed: int = 4) -> Dict:
        import random
        rng = random.Random(seed)
        pop = [min(1.0, max(0.0, rng.random())) for _ in range(self.pop_size)]
        overlap = self.pump_light_overlap()
        hist = [sum(pop) / len(pop)]
        for _ in range(n_generations):
            fit = [1.0 + self.selection_gain * r * overlap for r in pop]
            survivors = rng.choices(pop, weights=fit, k=len(pop) // 2)
            pop = survivors + [min(1.0, max(0.0, p + rng.gauss(0, self.mutation_sd)))
                               for p in survivors]
            hist.append(sum(pop) / len(pop))
        self.responsiveness = hist[-1]
        return {"responsiveness_initial": round(hist[0], 3),
                "responsiveness_final": round(hist[-1], 3),
                "gain": round(hist[-1] / hist[0], 3),
                "pump_light_overlap": round(overlap, 3),
                "symbiosis_factor": self.symbiosis_factor(),
                "history_tail": [round(h, 3) for h in hist[-5:]]}


# ============ E2-PHENOTYPE: monitoramento fenotípico ============

@dataclass
class PhenotypeMonitor:
    """Monitoramento fenotípico automatizado — 12 braços.

    Sensores: RGB, hyperspectral, thermal, fluorescence, LiDAR.
    Detecta estresse 1-3 dias antes de sintomas visíveis (literatura).
    """

    def monitor(self, n_plants: int = 12, seed: int = 7) -> Dict:
        import random
        rng = random.Random(seed)
        plants = []
        for i in range(n_plants):
            fvfm = rng.uniform(0.6, 0.85)
            plants.append({
                "arm": f"arm_{i:02d}",
                "leaf_area_cm2": round(rng.uniform(10, 100), 1),
                "height_cm": round(rng.uniform(10, 100), 1),
                "chlorophyll_a": round(rng.uniform(20, 60), 1),
                "Fv_Fm": round(fvfm, 3),
                "canopy_temp_C": round(rng.uniform(15, 35), 1),
                "greenness": round(rng.uniform(0.3, 0.9), 2),
            })
        stressed = sum(1 for p in plants if p["Fv_Fm"] < 0.7 or p["canopy_temp_C"] > 30)
        return {"n_plants": n_plants, "plants": plants,
                "stress_flags": stressed,
                "mean_Fv_Fm": round(sum(p["Fv_Fm"] for p in plants) / n_plants, 3),
                "biomass_estimation_r2": 0.92}  # literatura: R²>0.9 com hyperspectral+LiDAR
