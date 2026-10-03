"""Confiabilidade por Monte Carlo — vida útil 30 anos (estilo LP365).

Conglomerado do paper de reliability do Lunar Palace 1: modelar a
disponibilidade do sistema em 30 anos (10.958 sols marcianos ~ 11.000) sob
falha exponencial de subsistemas + reparo autônomo. Estende a vida útil do
checklist (25 -> 30 anos) quando a redundância Voronoi + reparo sustentam.
"""

from dataclasses import dataclass
import random


@dataclass
class ReliabilityMonteCarlo:
    """Disponibilidade em 30 anos via Monte Carlo."""

    subsystem_mtbf_years: float = 8.0    # tempo médio entre falhas por subsistema
    repair_days: float = 7.0             # reparo autônomo médio
    n_subsystems: int = 12               # subsistemas críticos (por braço/core)
    redundancy: int = 2                  # quantos podem falhar sem parar a árvore

    def simulate(self, years: float = 30.0, runs: int = 2000, seed: int = 7) -> dict:
        """Fração de runs em que o sistema permanece operacional em `years`."""
        rng = random.Random(seed)
        days = years * 365.25
        ok = 0
        mtbf_days = self.subsystem_mtbf_years * 365.25
        for _ in range(runs):
            # amostra falhas exponenciais por subsistema; a árvore sobrevive
            # se nunca mais de `redundancy` estiverem em reparo ao mesmo tempo
            down = [0.0] * self.n_subsystems
            t = 0.0
            alive = True
            while t < days:
                t += rng.expovariate(self.n_subsystems / mtbf_days)
                if t >= days:
                    break
                i = rng.randrange(self.n_subsystems)
                down[i] = t + self.repair_days
                concurrent = sum(1 for d in down if d > t)
                if concurrent > self.redundancy:
                    alive = False
                    break
            ok += int(alive)
        return {"reliability": round(ok / runs, 4), "years": years, "runs": runs,
                "mtbf_years": self.subsystem_mtbf_years, "redundancy": self.redundancy}
