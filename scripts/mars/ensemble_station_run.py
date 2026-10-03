#!/usr/bin/env python3
"""Ensemble do simulador unificado da estação — Camada 0 do plano A100.

Cada trajetória é um "mundo": amostra parâmetros de forcing (tempestades,
radiação basal, cobertura de sensores) e roda 60 anos marcianos (21060 sols)
com a física real do StationUnifiedSimulator + resolver S_meta.

Métricas por trajetória — decomposição arrival vs persistence:
  arrival    : t_first_critical / t_first_collapse (quando o regime degrada)
  persistence: dwell segments em critical/collapse + fração de episódios
               que retornam a regime melhor (recovery)
Saída: JSONL por trajetória (append, resumível por seed) + aggregate JSON.

Uso:
  python scripts/mars/ensemble_station_run.py --n 500 --workers 6 \
      --out data/mars_ensemble/ensemble_run.jsonl
  python scripts/mars/ensemble_station_run.py --n 10000 --workers 8 \
      --out data/mars_ensemble/ensemble_run.jsonl --resume
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

REGIMES = ("stable", "decaying", "critical", "collapse")


def sample_world(rng: random.Random) -> dict:
    """Um 'mundo' = vetor de parâmetros de forcing da trajetória."""
    return {
        "storm_rate": rng.uniform(0.02, 0.20),   # P(tempestade | season>0.4)
        "storm_boost": rng.uniform(1.5, 4.5),    # choque latente de poeira
        "rad_base": rng.uniform(0.55, 0.95),     # mSv/dia basal
        "wind_shift": rng.uniform(-1.0, 1.0),    # m/s no vento médio
        "seismic_rate": rng.uniform(0.005, 0.06),
        "env_coverage": rng.uniform(0.60, 1.0),  # observabilidade (sensores)
    }


def run_trajectory(task: tuple) -> dict:
    seed, n_sols = task
    world_rng = random.Random(seed ^ 0x5EED)
    world = sample_world(world_rng)
    env_rng = random.Random(seed ^ 0xE11)

    sim = StationUnifiedSimulator(seed=seed)
    deposition = sim.dcs.flux.deposition

    counts = {r: 0 for r in REGIMES}
    defense_sols = refusal_sols = 0
    t_first_critical = t_first_collapse = None
    episodes = []          # {regime, start, len, defense_sols}
    cur = None             # episódio aberto (critical/collapse)
    n_recovered = 0
    s_meta_min, s_meta_final = 1.0, 1.0
    integrity_min, amci_final = 1.0, 0.0
    s_meta_dec = []
    era_final = "I_ancoragem"

    for sol in range(1, n_sols + 1):
        # Ambiente: mesma receita do sim interno, parametrizada pelo mundo
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
        regime = res.get("regime")
        if regime is None:
            continue
        counts[regime] += 1
        defense_sols += 1 if res["defense_active"] else 0
        refusal_sols += 1 if res["homeostatic_refusal"] else 0
        s = res["s_meta"]
        s_meta_min = min(s_meta_min, s)
        s_meta_final = s
        integrity_min = min(integrity_min, res["body_integrity"])
        amci_final = res["amci_closure"]
        era_final = res["era"]
        if sol % 200 == 0:
            s_meta_dec.append(round(s, 4))

        # chegada (qualquer causa — inclui tempestades)
        if regime == "critical" and t_first_critical is None:
            t_first_critical = sol
        if regime == "collapse" and t_first_collapse is None:
            t_first_collapse = sol

        # episódios: abre/fecha + flag de coincidência com defesa
        if regime in ("critical", "collapse"):
            if cur is None or cur["regime"] != regime:
                if cur is not None:
                    episodes.append(cur)
                    n_recovered += 1
                cur = {"regime": regime, "start": sol, "len": 1,
                       "defense_sols": 1 if res["defense_active"] else 0}
            else:
                cur["len"] += 1
                cur["defense_sols"] += 1 if res["defense_active"] else 0
        elif cur is not None:
            episodes.append(cur)
            n_recovered += 1
            cur = None

    if cur is not None:
        episodes.append(cur)

    # episódios storm-coincident (>=50% dos sols em defesa) vs endógenos
    crit_eps = [e for e in episodes if e["regime"] == "critical"]
    coll_eps = [e for e in episodes if e["regime"] == "collapse"]
    endo_eps = [e for e in episodes
                if e["defense_sols"] / e["len"] < 0.5]
    t_first_endo_critical = next(
        (e["start"] for e in episodes
         if e["regime"] == "critical" and e["defense_sols"] / e["len"] < 0.5),
        None)

    return {
        "seed": seed, "world": world, "n_sols": n_sols,
        "regime_counts": counts,
        "defense_sols": defense_sols, "refusal_sols": refusal_sols,
        "t_first_critical": t_first_critical,
        "t_first_collapse": t_first_collapse,
        "t_first_endo_critical": t_first_endo_critical,
        "critical_dwells_storm": [e["len"] for e in crit_eps
                                 if e["defense_sols"] / e["len"] >= 0.5],
        "critical_dwells_endo": [e["len"] for e in crit_eps
                                if e["defense_sols"] / e["len"] < 0.5],
        "collapse_dwells_storm": [e["len"] for e in coll_eps
                                 if e["defense_sols"] / e["len"] >= 0.5],
        "collapse_dwells_endo": [e["len"] for e in coll_eps
                                if e["defense_sols"] / e["len"] < 0.5],
        "n_critical_episodes": len(crit_eps),
        "n_collapse_episodes": len(coll_eps),
        "n_endo_episodes": len(endo_eps),
        "n_recovered_episodes": n_recovered,
        "s_meta_min": round(s_meta_min, 4), "s_meta_final": round(s_meta_final, 4),
        "s_meta_decimated": s_meta_dec,
        "body_integrity_min": round(integrity_min, 4),
        "amci_final": amci_final, "era_final": era_final,
    }


def aggregate(rows: list) -> dict:
    """Decomposição arrival vs persistence:
    arrival    — chegada endógena (critical sem coincidência de defesa)
    persistence— dwells storm vs endo + taxa de recuperação por episódio."""
    n = len(rows)
    med = lambda a: sorted(a)[len(a) // 2] if a else None
    flat = lambda key: [d for r in rows for d in r[key]]

    endo = [r for r in rows if r["t_first_endo_critical"] is not None]
    coll = [r for r in rows if r["t_first_collapse"] is not None]
    arrivals_endo = sorted(r["t_first_endo_critical"] for r in endo)
    arrivals_any = sorted(r["t_first_critical"] for r in rows
                          if r["t_first_critical"] is not None)
    total_eps = sum(r["n_critical_episodes"] + r["n_collapse_episodes"]
                    for r in rows)
    total_rec = sum(r["n_recovered_episodes"] for r in rows)
    occ = {r_: sum(r["regime_counts"][r_] for r in rows)
           / (n * rows[0]["n_sols"]) for r_ in REGIMES}

    def pct(a, q):
        if not a:
            return None
        a = sorted(a)
        return a[min(len(a) - 1, int(len(a) * q))]

    endo_dwells = flat("critical_dwells_endo") + flat("collapse_dwells_endo")
    storm_dwells = flat("critical_dwells_storm") + flat("collapse_dwells_storm")
    long_endo = [r for r in rows
                 if any(d >= 30 for d in r["critical_dwells_endo"]
                        + r["collapse_dwells_endo"])]

    return {
        "n_trajectories": n,
        "p_reach_critical_any": round(len(arrivals_any) / n, 4),
        "p_reach_critical_endogenous": round(len(endo) / n, 4),
        "p_reach_collapse": round(len(coll) / n, 4),
        "p_long_endo_episode_30sol": round(len(long_endo) / n, 4),
        "median_arrival_any_sol": med(arrivals_any),
        "median_arrival_endogenous_sol": med(arrivals_endo),
        "dwell_critical_storm_p50_p90_p99_max": [
            med(flat("critical_dwells_storm")),
            pct(flat("critical_dwells_storm"), 0.90),
            pct(flat("critical_dwells_storm"), 0.99),
            max(flat("critical_dwells_storm"), default=None)],
        "dwell_critical_endo_p50_p90_p99_max": [
            med(flat("critical_dwells_endo")),
            pct(flat("critical_dwells_endo"), 0.90),
            pct(flat("critical_dwells_endo"), 0.99),
            max(flat("critical_dwells_endo"), default=None)],
        "dwell_all_endo_p50_p90_p99_max": [
            med(endo_dwells), pct(endo_dwells, 0.90),
            pct(endo_dwells, 0.99), max(endo_dwells, default=None)],
        "dwell_all_storm_p50_p90_p99_max": [
            med(storm_dwells), pct(storm_dwells, 0.90),
            pct(storm_dwells, 0.99), max(storm_dwells, default=None)],
        "recovery_rate_per_episode": (round(total_rec / total_eps, 4)
                                    if total_eps else None),
        "regime_occupancy_frac": {k: round(v, 4) for k, v in occ.items()},
        "mean_s_meta_min": round(sum(r["s_meta_min"] for r in rows) / n, 4),
        "mean_body_integrity_min": round(
            sum(r["body_integrity_min"] for r in rows) / n, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--sols", type=int, default=21060)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.resume and args.out.exists():
        with args.out.open() as f:
            done = {json.loads(l)["seed"] for l in f if l.strip()}

    tasks = [(args.seed_base + i, args.sols) for i in range(args.n)
             if args.seed_base + i not in done]
    print(f"trajetórias a rodar: {len(tasks)} (skip {len(done)} já feitas)",
          flush=True)

    t0 = time.time()
    rows = []
    with args.out.open("a") as fout, mp.Pool(args.workers) as pool:
        for i, row in enumerate(pool.imap_unordered(run_trajectory, tasks), 1):
            fout.write(json.dumps(row) + "\n")
            rows.append(row)
            if i % 50 == 0 or i == len(tasks):
                fout.flush()
                print(f"{i}/{len(tasks)} em {time.time()-t0:.0f}s", flush=True)

    # aggregate sobre TODAS as linhas do arquivo (resume-safe)
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
