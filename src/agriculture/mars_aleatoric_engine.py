"""Mars Aleatoric Engine — piso controlado + teto aberto.

Implementa o motor aleatório do paper de referência
(docs/papers/mars_ecopoiesis_refs_aleatoric_engine.md §3.2): a estação
garante o envelope físico e NÃO seleciona destinos biológicos. Seleção
pertence ao ambiente; a estação é habitat + testemunha.

Componentes (1:1 com o design):

1. NoiseBudget — orçamento de ruído por geração: a taxa de mutação não é
   setpoint; é sorteada por sol dentro de banda segura. NitalMutagen
   modula (autorização dirigida) mas nunca zera o componente estocástico.
   Radiação/UV REAIS (env do REMS/RAD) entram como fonte natural de
   mutação não-otimizada — o dia sem vento e o dia de tempestade têm
   orçamentos diferentes porque o planeta é assim.

2. NicheMosaic — N microcosmos com T/pH/ClO4/atividade de água/
   irradiância distintos. Cada nicho tem seu ótimo ambiental (derivado
   das condições do nicho, não de um alvo externo); traços derivam em
   direção ao ótimo + ruído proporcional ao NoiseBudget, com migração
   parcial entre nichos (isolamento parcial = motor de diversificação).

3. HGTPool aberto — a amostra genética disponível é um sorteio
   estocástico do pool (genes_of_interest do HGTSimulator), não lista
   fixa: a cada sol cada nicho pode importar um gene amostrado.

4. SurpriseDetector — testemunha de novidade: distância do vetor de
   traços ao baseline EMA do mosaico > tau -> evolutionary_surprise_event.
   Análogo biológico do latent_shock_inc: a estação CAPTA o acidente em
   vez de preveni-lo. Baseline EMA adapta lento — surpresa é desvio do
   regime conhecido, não distância absoluta.

5. Não-otimização como lei — as métricas (diversidade entre nichos,
   ocupação, surpresas) são OBSERVÁVEIS, não targets. Nenhum gradiente
   de fitness externo é aplicado: o ótimo de cada nicho vem das suas
   próprias condições físicas.

Calibração: mesma disciplina dos outros órgãos — ordens de grandeza
ancoradas (mutation_rate wheat 1.5e-6, 4 traços do MartianMutagenesis),
a novidade mora na CADEIA (ruído real -> mosaico -> surpresa capta).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from src.agriculture.mars_mutagenesis import NitalMutagen
except ImportError:
    try:
        from mars_mutagenesis import NitalMutagen
    except ImportError:
        NitalMutagen = None


# ============ 1) Orçamento de ruído — a taxa sorteada por sol ============

@dataclass
class NoiseBudget:
    """Taxa de mutação por sol: banda segura + fonte natural + bônus
    dirigido. NUNCA zero — o chão estocástico é lei."""

    base_rate: float = 1.5e-6      # wheat-calibrado (MartianMutagenesis)
    band_low: float = 0.4          # multiplicador mínimo do base
    band_high: float = 3.0         # teto seguro (acima: mutação letal)
    env_gain: float = 0.5          # quanto rad/uv reais modulam a taxa
    nital_bonus: float = 0.0       # 0 sem autorização dirigida

    def draw(self, env: Dict[str, float], rng: random.Random) -> float:
        """Sorteia a taxa do sol. Log-uniform na banda (ordens de
        grandeza igualmente prováveis), modulada pelo ambiente real."""
        u = math.exp(rng.uniform(math.log(self.band_low),
                                 math.log(self.band_high)))
        rad = env.get("rad_msv_day", 0.67) / 0.67
        uv = env.get("uv_abc_w_m2", 0.03) / 0.03
        natural = 1.0 + self.env_gain * ((rad + uv) / 2.0 - 1.0)
        rate = self.base_rate * u * max(0.1, natural)
        return rate * (1.0 + self.nital_bonus)


# ============ 2) Mosaico de nichos — heterogeneidade como motor ============

# traços vivos (mesmo espaço do MartianMutagenesis):
#   [clo4_tol, cold_tol, rad_tol, growth]
TRAIT_NAMES = ["clo4_tol", "cold_tol", "rad_tol", "growth"]


@dataclass
class Niche:
    """Um microcosmo: condições físicas próprias = ótimo ambiental próprio."""
    name: str
    temp_k: float
    ph: float
    clo4_mM: float
    water_activity: float      # 0..1
    irradiance_rel: float      # 0..1 (1 = sol direto)
    traits: List[float] = field(default_factory=lambda: [0.3] * 4)
    density: float = 0.1       # fração do nicho colonizada

    def optimum(self) -> List[float]:
        """O alvo vem DAS CONDIÇÕES — seleção do ambiente, não do design."""
        return [
            min(1.0, self.clo4_mM / 2.4),                    # mais ClO4 -> mais tolerância ótima
            min(1.0, max(0.0, (270.0 - self.temp_k) / 60.0)), # mais frio -> mais psicrofilia
            min(1.0, self.irradiance_rel),                  # mais rad/UV -> mais tolerância
            min(1.0, self.water_activity),                  # mais água -> mais crescimento
        ]

    def viability(self) -> float:
        """Fração do nicho que o traço atual consegue ocupar — observável."""
        return min(1.0, sum(
            1.0 - abs(t - o) for t, o in
            zip(self.traits, self.optimum())) / 4.0)


class NicheMosaic:
    """N microcosmos divergindo sob seleção ambiental + ruído + migração."""

    NICHES_DEFAULT = (
        # (nome, temp_k, pH, clo4_mM, aw, irradiance)
        ("regolith_open",   215.0, 9.0, 2.4, 0.15, 1.0),
        ("subsurface_ice",  250.0, 7.5, 0.5, 0.45, 0.05),
        ("eclss_biofilm",   295.0, 7.0, 0.1, 0.90, 0.3),
        ("airlock_rim",     230.0, 8.0, 0.8, 0.25, 0.8),
        ("greenhouse_soil", 293.0, 6.5, 0.3, 0.85, 0.6),
        ("dust_trap",       240.0, 8.5, 1.8, 0.20, 0.5),
    )

    def __init__(self, seed: int = 17,
                 niches: Optional[List[Niche]] = None) -> None:
        self.niches = niches or [Niche(*n) for n in self.NICHES_DEFAULT]
        self._sol = 0

    def step(self, noise_rate: float, rng: random.Random,
             migration_frac: float = 0.02) -> None:
        """Um sol do mosaico: deriva ao ótimo + ruído do orçamento +
        migração parcial entre nichos."""
        self._sol += 1
        sigma = math.sqrt(noise_rate * 1e6) * 0.02  # escala do passo
        for n in self.niches:
            opt = n.optimum()
            for i in range(4):
                drift = 0.01 * (opt[i] - n.traits[i])          # seleção ambiental
                noise = rng.gauss(0.0, sigma)                  # componente aleatório
                n.traits[i] = min(1.0, max(0.0, n.traits[i] + drift + noise))
            n.density = min(1.0, 0.85 * n.density + 0.15 * n.viability())
        # migração parcial: uma cópia de traço troca de nicho por sol
        if rng.random() < migration_frac * len(self.niches):
            a, b = rng.sample(self.niches, 2)
            i = rng.randrange(4)
            b.traits[i] = 0.5 * (b.traits[i] + a.traits[i])

    def diversity(self) -> float:
        """Entropia de Shannon sobre a ocupação dos nichos — observável."""
        tot = sum(n.density for n in self.niches) or 1.0
        return -sum((n.density / tot) * math.log(n.density / tot)
                    for n in self.niches if n.density > 0) / math.log(
                        len(self.niches))

    def trait_spread(self) -> float:
        """Dispersão média entre nichos no espaço de traços."""
        if len(self.niches) < 2:
            return 0.0
        acc, cnt = 0.0, 0
        for i in range(len(self.niches)):
            for j in range(i + 1, len(self.niches)):
                acc += math.dist(self.niches[i].traits, self.niches[j].traits)
                cnt += 1
        return acc / cnt

    def centroid(self) -> List[float]:
        return [sum(n.traits[i] for n in self.niches) / len(self.niches)
                for i in range(4)]


# ============ 3) Pool HGT aberto — amostra estocástica do genoma ============

GENE_POOL = ["pcrA", "pcrB", "pcrC", "cld", "nifH", "nifD", "nifK",
             "phoA", "phoB", "dna_repair", "osmoprotectant", "antioxidant",
             "desiccation_tol", "ice_binding", "uv_screen", "biofilm_matrix"]


class HGTPool:
    """Amostra estocástica: a cada sol um gene pode entrar num nicho —
    o pool é aberto, não lista fixa por espécie."""

    def __init__(self) -> None:
        self.niche_genes: Dict[str, set] = {}

    def step(self, mosaic: NicheMosaic, noise_rate: float,
             rng: random.Random) -> int:
        """Retorna nº de eventos HGT do sol."""
        events = 0
        for n in mosaic.niches:
            self.niche_genes.setdefault(n.name, set())
            # taxa proporcional ao ruído do sol (mesma fonte)
            if rng.random() < noise_rate * 3e4 * n.density:
                gene = rng.choice(GENE_POOL)
                if gene not in self.niche_genes[n.name]:
                    self.niche_genes[n.name].add(gene)
                    events += 1
        return events


# ============ 4) SurpriseDetector — a testemunha do acidente ============

@dataclass
class SurpriseEvent:
    sol: int
    niche: str
    distance: float
    trait: str
    value: float


class SurpriseDetector:
    """Excursão do próprio regime do nicho > tau -> evento.

    Nichos divergentes SÃO o design (seleção ambiental) — o desvio
    permanente entre nichos não é surpresa. Surpresa é o acidente: o
    traço salta fora do SEU próprio regime recente (EMA por nicho),
    ou cruza o envelope histórico do mosaico (novidade absoluta)."""

    def __init__(self, k_sigma: float = 4.0, tau_abs: float = 0.15,
                 ema: float = 0.97) -> None:
        self.k_sigma = k_sigma               # desvios típicos para disparar
        self.tau_abs = tau_abs               # piso absoluto (novidade)
        self.ema = ema
        self.regime: Dict[str, List[float]] = {}   # EMA por nicho
        self.dev_ema: Dict[str, List[float]] = {}  # EMA do |desvio| por nicho
        self.envelope_lo = [1.0] * 4
        self.envelope_hi = [0.0] * 4
        self.events: List[SurpriseEvent] = []

    def observe(self, mosaic: NicheMosaic, sol: int) -> List[SurpriseEvent]:
        new: List[SurpriseEvent] = []
        for n in mosaic.niches:
            ema = self.regime.setdefault(n.name, list(n.traits))
            dev = self.dev_ema.setdefault(n.name, [1e-4] * 4)
            for i, name in enumerate(TRAIT_NAMES):
                d = abs(n.traits[i] - ema[i])
                # 1) excursão rara: > k_sigma vezes o desvio típico —
                # o limiar respira com o orçamento de ruído (sob Nital
                # sobe junto; surpresa continua sendo o acidente RELATIVO)
                if d > self.k_sigma * max(dev[i], 1e-4):
                    ev = SurpriseEvent(sol, n.name, round(d, 4),
                                       name, round(n.traits[i], 4))
                    self.events.append(ev)
                    new.append(ev)
                # 2) novidade absoluta — fora do envelope histórico
                if n.traits[i] > self.envelope_hi[i] + self.tau_abs or \
                        n.traits[i] < self.envelope_lo[i] - self.tau_abs:
                    ev = SurpriseEvent(sol, n.name, round(d, 4),
                                       name + "!novel", round(n.traits[i], 4))
                    self.events.append(ev)
                    new.append(ev)
                self.envelope_hi[i] = max(self.envelope_hi[i], n.traits[i])
                self.envelope_lo[i] = min(self.envelope_lo[i], n.traits[i])
                dev[i] = 0.95 * dev[i] + 0.05 * d
            # EMA por nicho — o regime local se move devagar
            self.regime[n.name] = [self.ema * e + (1 - self.ema) * t
                                   for e, t in zip(ema, n.traits)]
        return new


# ============ O motor — composição por sol ============

@dataclass
class AleatoricEngine:
    """Piso controlado + teto aberto. step_sol(env) -> telemetria."""

    seed: int = 23
    noise: NoiseBudget = field(default_factory=NoiseBudget)
    mosaic: NicheMosaic = field(default_factory=NicheMosaic)
    hgt: HGTPool = field(default_factory=HGTPool)
    detector: SurpriseDetector = field(default_factory=SurpriseDetector)
    mutagen: Optional[object] = None   # NitalMutagen se autorizado
    _sol: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def authorize_directed(self, hno3_conc: float = 0.30) -> None:
        """Experimento dirigido autorizado pelo operador: NitalMutagen
        entra como bônus SOBRE o chão — nunca substitui o estocástico."""
        if NitalMutagen is not None:
            self.mutagen = NitalMutagen(hno3_conc=hno3_conc)
            self.noise.nital_bonus = self.mutagen.mutation_rate()

    def step_sol(self, env: Dict[str, float]) -> Dict[str, object]:
        self._sol += 1
        rate = self.noise.draw(env, self._rng)
        self.mosaic.step(rate, self._rng)
        hgt_events = self.hgt.step(self.mosaic, rate, self._rng)
        surprises = self.detector.observe(self.mosaic, self._sol)
        return {
            "ale_sol": self._sol,
            "ale_noise_rate": round(rate, 9),
            "ale_diversity": round(self.mosaic.diversity(), 4),
            "ale_trait_spread": round(self.mosaic.trait_spread(), 4),
            "ale_hgt_events": hgt_events,
            "ale_surprises_today": len(surprises),
            "ale_surprises_total": len(self.detector.events),
            "ale_niche_occupancy": {
                n.name: round(n.density, 3) for n in self.mosaic.niches},
            "ale_nital_active": self.noise.nital_bonus > 0,
        }
