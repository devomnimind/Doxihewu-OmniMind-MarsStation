#!/usr/bin/env python3
"""Ensemble Camada 1 — classificação por capacidade de cadeia.

Mesma física e mesmo universo de mundos do Camada 0
(ensemble_station_run.py), mas a métrica muda de "quanto tempo o regime
dura" para "quais cadeias o mundo consegue rodar": cada trajetória leva
um ChainCapacityClassifier e emite ocupação dos 4 regimes de capacidade,
eventos de bifurcação (rho_closure / repro_ratio / stock_drain), tempo
de chegada a metabolic/evolutionary e fração de sols com Exceção_τ.

O mundo Camada-1 estende o Camada-0 com o lado da demanda:
  crew_eq    habitantes-equivalentes (O₂ 0.84 kg/sol, H₂O 3 L/sol)
  leak_base  vazamento base por sol escalado por (1 − integridade)

Saída: JSONL por trajetória (append, resumível por seed) + aggregate JSON.

Uso:
  python scripts/mars/ensemble_chain_capacity_run.py --n 500 --workers 6 \
      --out data/mars_ensemble/chain_capacity.jsonl
  python scripts/mars/ensemble_chain_capacity_run.py --n 10000 --workers 8 \
      --out data/mars_ensemble/chain_capacity.jsonl --resume --policy functional
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.agriculture.mars_unified_simulator import StationUnifiedSimulator  # noqa: E402
from src.agriculture.mars_chain_capacity import (  # noqa: E402
    CHAIN_REGIMES, ChainCapacityClassifier)


def sample_world(rng: random.Random) -> dict:
    """Mundo Camada-1 = forcing Camada-0 + demanda (crew_eq, leak)."""
    return {
        "storm_rate": rng.uniform(0.02, 0.20),
        "storm_boost": rng.uniform(1.5, 4.5),
        "rad_base": rng.uniform(0.55, 0.95),
        "wind_shift": rng.uniform(-1.0, 1.0),
        "seismic_rate": rng.uniform(0.005, 0.06),
        "env_coverage": rng.uniform(0.60, 1.0),
        "crew_eq": rng.uniform(0.0, 30.0),      # estação robótica→tripulada
        "leak_base": rng.uniform(0.001, 0.01),  # vazamento no limiar I=0
        "policy": None,                          # preenchido por main
    }


def run_trajectory(task: tuple) -> dict:
    seed, n_sols, policy = task
    world_rng = random.Random(seed ^ 0x5EED)
    world = sample_world(world_rng)
    world["policy"] = policy
    env_rng = random.Random(seed ^ 0xE11)

    sim = StationUnifiedSimulator(seed=seed)
    clf = ChainCapacityClassifier(
        policy=policy,
        crew_eq=world["crew_eq"],
        leak_base=world["leak_base"])
    deposition = sim.dcs.flux.deposition

    counts = {r: 0 for r in CHAIN_REGIMES}
    t_metabolic = t_evolutionary = t_metabolic_loss = None
    excecao_sols = 0
    rho_max = rho_final = 0.0
    repro_ratios = []
    endo_metabolic = storm_metabolic = 0
    collapse_sols = 0

    for sol in range(1, n_sols + 1):
        season = math.sin(2 * math.pi * sol / 669.0)
        wind = max(0.5, 4.2 + 1.5 * season + world["wind_shift"]
                   + env_rng.gauss(0, 1.2))
        is_storm = (season > 0.4) and (env_rng.random() < world["storm_rate"])
        dust = deposition(wind, world["storm_boost"] if is_storm else 0.0, sol)
        env = {
            "wind_speed_ms": round(wind, 2),
            "wind_gust_ms": round(wind * (1.3 + 0.3 * env_rng.random()), 2),
            "dust_flux": round(dust, 4),
            "air_temp_k": round(210.0 + 20.0 * season + env_rng.gauss(0, 5), 1),
            "ground_temp_delta": round(65.0 + 10.0 * abs(season), 1),
            "uv_abc_w_m2": round(0.035 * max(0.2, 1.0 - 0.5 * min(dust, 4.0) / 4.0), 4),
            "rad_msv_day": round(world["rad_base"] + 0.1 * env_rng.random(), 3),
            "perchlorate_wt": 0.6,
            "seismic_shock": 1.0 if env_rng.random() < world["seismic_rate"] else 0.0,
            "env_coverage": world["env_coverage"],
        }

        res = sim.step(env)
        cap = clf.observe(res, world)

        r = cap["regime_cadeia"]
        counts[r] += 1
        if cap["excecao_tau"]:
            excecao_sols += 1
        rho_max = max(rho_max, cap["rho_repro"])
        rho_final = cap["rho_repro"]
        if sol % 10 == 0:
            repro_ratios.append(cap["repro_ratio"])
        if res.get("regime") == "collapse":
            collapse_sols += 1

        # chegada (arrival) e perda — decomposição por contexto
        if r == "metabolic_habitat" or r == "evolutionary_habitat":
            if t_metabolic is None:
                t_metabolic = sol
                if res.get("defense_active"):
                    storm_metabolic += 1
                else:
                    endo_metabolic += 1
            if r == "evolutionary_habitat" and t_evolutionary is None:
                t_evolutionary = sol
        elif t_metabolic is not None and r in ("survival_only",
                                               "sterile_physical"):
            if t_metabolic_loss is None:
                t_metabolic_loss = sol

    repro_sorted = sorted(repro_ratios)
    return {
        "seed": seed, "world": world, "n_sols": n_sols, "policy": policy,
        "cadeia_counts": counts,
        "cadeia_occupancy": {k: round(v / n_sols, 4)
                             for k, v in counts.items()},
        "t_metabolic_first": t_metabolic,
        "t_evolutionary_first": t_evolutionary,
        "t_metabolic_loss": t_metabolic_loss,
        "excecao_tau_frac": round(excecao_sols / n_sols, 4),
        "rho_max": round(rho_max, 4), "rho_final": round(rho_final, 4),
        "repro_ratio_p50": (repro_sorted[len(repro_sorted) // 2]
                            if repro_sorted else None),
        "bifurcation_events": [e.as_dict() for e in clf.events],
        "n_bifurcation_events": len(clf.events),
        "s_meta_collapse_sols": collapse_sols,
        "era_final": res["era"],
    }


def aggregate(rows: list) -> dict:
    n = len(rows)
    med = lambda a: sorted(a)[len(a) // 2] if a else None
    occ = {r: sum(row["cadeia_counts"][r] for row in rows)
           / (n * rows[0]["n_sols"]) for r in CHAIN_REGIMES}
    evo = [r for r in rows if r["t_evolutionary_first"] is not None]
    meta = [r for r in rows if r["t_metabolic_first"] is not None]
    loss = [r for r in rows if r["t_metabolic_loss"] is not None]
    n_events = sum(r["n_bifurcation_events"] for r in rows)

    # correlação mundo→regime: crew_eq médio por destino final
    def mean_w(key, subset):
        return round(sum(r["world"][key] for r in subset) / len(subset), 3) \
            if subset else None

    return {
        "n_trajectories": n,
        "policy": rows[0]["policy"],
        "chain_regime_occupancy": {k: round(v, 4) for k, v in occ.items()},
        "p_reach_metabolic": round(len(meta) / n, 4),
        "p_reach_evolutionary": round(len(evo) / n, 4),
        "p_lose_metabolic_after_reach": round(len(loss) / max(1, len(meta)), 4),
        "median_t_metabolic_sol": med([r["t_metabolic_first"] for r in meta]),
        "median_t_evolutionary_sol": med(
            [r["t_evolutionary_first"] for r in evo]),
        "mean_excecao_tau_frac": round(
            sum(r["excecao_tau_frac"] for r in rows) / n, 4),
        "mean_rho_final": round(sum(r["rho_final"] for r in rows) / n, 4),
        "mean_bifurcation_events_per_world": round(n_events / n, 3),
        "crew_eq_mean_evolutionary": mean_w("crew_eq", evo),
        "crew_eq_mean_never_metabolic": mean_w(
            "crew_eq", [r for r in rows if r["t_metabolic_first"] is None]),
        "storm_rate_mean_evolutionary": mean_w("storm_rate", evo),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--sols", type=int, default=21060)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--policy", choices=["strict", "functional"],
                    default="functional")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.resume and args.out.exists():
        with args.out.open() as f:
            done = {json.loads(l)["seed"] for l in f if l.strip()}

    tasks = [(args.seed_base + i, args.sols, args.policy)
             for i in range(args.n)
             if args.seed_base + i not in done]
    print(f"trajetórias Camada-1 a rodar: {len(tasks)} "
          f"(skip {len(done)} já feitas)", flush=True)

    t0 = time.time()
    with args.out.open("a") as fout, mp.Pool(args.workers) as pool:
        for i, row in enumerate(
                pool.imap_unordered(run_trajectory, tasks), 1):
            fout.write(json.dumps(row) + "\n")
            if i % 50 == 0 or i == len(tasks):
                fout.flush()
                print(f"{i}/{len(tasks)} em {time.time()-t0:.0f}s",
                      flush=True)

    all_rows = []
    with args.out.open() as f:
        for l in f:
            if l.strip():
                all_rows.append(json.loads(l))
    agg = aggregate(all_rows)
    agg_path = args.out.with_suffix(".aggregate.json")
    agg_path.write_text(json.dumps(agg, indent=2))
    print(json.dumps(agg, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
