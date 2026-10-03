"""Mars Daemon — servidor autonomo na VM do Colab com checkpoint soberano.

Pedido do operador (2026-09-28): "o daemon la no Colab nao pode ficar nessa
execucao por horas, autonomamente? ele processa e de tempos faz checkpoint
para o HuggingFace... fica ate 12-24h no Colab Pro. E aqui tambem mandando
dados — synthesis, gap-autowatch — para la cruzar."

Arquitetura:
  OmniMind local --(mars_bridge: publish)--> HF inbox_local/  --+
                                                              v
                                                    MARS DAEMON (Colab VM)
                                                    loop de ciclos ~12-24h
                                                    checkpoint -> HF a cada N s
                                                              |
  OmniMind local <--(mars_bridge: consume)-- HF inbox_colab/  <--+

O HF `mars-monoculture-data` e o BARRAMENTO bidirecional:
  inbox_local/   — payloads enviados pelo OmniMind (synthesis, gap reports)
  inbox_colab/   — respostas/analises produzidas pelo daemon
  daemon_state/  — checkpoint soberano (ciclo, RNG, ultimos resultados)

RESILIENCIA: Colab desconecta ~12-24h. O daemon checkpointa estado completo
a cada checkpoint_every_s; ao restart, restaura do HF e continua do ciclo
exato. Nada se perde.
"""

from __future__ import annotations

import json
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor


try:
    from src.agriculture.mars_unified_simulator import StationUnifiedSimulator
except ImportError:
    from mars_unified_simulator import StationUnifiedSimulator


@dataclass
class DaemonCheckpoint:
    """Estado soberano do daemon — persistido ao HF para sobreviver desconexao."""

    cycle: int = 0
    started_ts: float = 0.0
    rng_state: tuple | None = None
    last_results: Dict = field(default_factory=dict)
    processed_inbox: List[str] = field(default_factory=list)
    uptime_s: float = 0.0
    station_snapshot: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {"writer": "colab_daemon", "cycle": self.cycle,
                "started_ts": self.started_ts,
                "rng_state": self.rng_state, "last_results": self.last_results,
                "processed_inbox": self.processed_inbox, "uptime_s": self.uptime_s,
                "station_snapshot": self.station_snapshot}

    @classmethod
    def from_dict(cls, d: Dict) -> "DaemonCheckpoint":
        return cls(cycle=d.get("cycle", 0), started_ts=d.get("started_ts", 0.0),
                   rng_state=tuple(d["rng_state"]) if d.get("rng_state") else None,
                   last_results=d.get("last_results", {}),
                   processed_inbox=d.get("processed_inbox", []),
                   uptime_s=d.get("uptime_s", 0.0),
                   station_snapshot=d.get("station_snapshot", {}))


class _HFBus:
    """Barramento HF: lista/lea/grava payloads.

    RATE LIMIT (2026-09-28): upload_file = 1 commit HF; o daemon escreve
    centenas (checkpoint, job_queue, job_results, inbox) e esgota os
    256 commits/hora. Por isso write() BUFFERIZA em memoria local e
    flush() sobe tudo num unico upload_folder -> 1 commit por ciclo.
    """

    def __init__(self, api=None, repo: str = "fabricioslv/mars-monoculture-data"):
        self.api = api
        self.repo = repo
        self._mem: Dict[str, str] = {}
        self._pending: Dict[str, Dict] = {}   # buffer p/ flush em batch
        self._files_cache: List[str] = []     # anti-429: listagem cacheada
        self._files_ts: float = 0.0

    def list_files(self, ttl_s: float = 60.0) -> List[str]:
        """list_repo_files cacheado — cada chamada crua e um GET na API do HF
        e o daemon lista varias vezes por ciclo (inbox + queue + reads).
        429s observados (2026-09-28): cache de 60 s reduz chamadas ~10x."""
        if not self.api:
            return sorted(self._mem)
        if time.time() - self._files_ts > ttl_s:
            try:
                self._files_cache = self.api.list_repo_files(
                    self.repo, repo_type="dataset")
                self._files_ts = time.time()
            except Exception:
                pass                            # em 429, usa o cache velho
        return list(self._files_cache)

    def list_inbox(self, direction: str = "local") -> List[str]:
        if self.api:
            return sorted(f for f in self.list_files()
                          if f.startswith(f"inbox_{direction}/"))
        return sorted(f for f in self._mem if f.startswith(f"inbox_{direction}/"))

    def read(self, path: str) -> Optional[Dict]:
        if self.api:
            if path in self._pending:                    # buffer antes de subir
                return self._pending[path]
            if path not in self.list_files():
                return None
            from huggingface_hub import hf_hub_download
            try:
                p = hf_hub_download(repo_id=self.repo, repo_type="dataset",
                                    filename=path)
            except Exception:
                return None
            return json.load(open(p))
        return json.loads(self._mem[path]) if path in self._mem else None

    def write(self, path: str, payload: Dict) -> None:
        if self.api:
            self._pending[path] = payload                # bufferiza — 1 commit/flush
        else:
            self._mem[path] = json.dumps(payload)

    def flush(self) -> int:
        """Sobe todos os writes bufferizados num unico commit (upload_folder)."""
        if not self.api or not self._pending:
            return 0
        import os, tempfile
        n = len(self._pending)
        with tempfile.TemporaryDirectory() as td:
            for path, payload in self._pending.items():
                fp = os.path.join(td, path)
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                json.dump(payload, open(fp, "w"))
            self.api.upload_folder(repo_id=self.repo, repo_type="dataset",
                                   folder_path=td, path_in_repo="")
            for path in self._pending:              # escritas entram no cache
                if path not in self._files_cache:   # sem forcar refresh
                    self._files_cache.append(path)
        self._pending.clear()
        return n


# ============ Fila de trabalhos (aproveita os N workers do Colab Pro) ============

@dataclass
class Job:
    """Um trabalho enfileirado para o daemon executar com dados reais."""
    job_id: str
    kind: str                     # mesh_series | synthesis | heavy_sim | classify
    payload: Dict
    status: str = "queued"        # queued | running | done | failed
    result: Optional[Dict] = None
    submitted_ts: float = 0.0
    finished_ts: float = 0.0


class JobQueue:
    """Fila persistente de jobs — no HF para sobreviver, em memoria p/ testes.

    O daemon despacha para N workers (Colab Pro: 8). Cada job grava resultado
    em job_results/{id}.json — o OmniMind coleta pela bridge.
    """

    def __init__(self, bus: _HFBus):
        self.bus = bus
        self._local: Dict[str, Job] = {}   # cache local (a fila viva)

    def submit(self, job: Job) -> str:
        job.submitted_ts = time.time()
        self._local[job.job_id] = job
        self.bus.write(f"job_queue/{job.job_id}.json",
                       {"job_id": job.job_id, "kind": job.kind,
                        "payload": job.payload, "status": "queued",
                        "submitted_ts": job.submitted_ts})
        return job.job_id

    def next_queued(self) -> Optional[Job]:
        for j in self._local.values():
            if j.status == "queued":
                return j
        return None

    def mark(self, job_id: str, status: str, result: Optional[Dict] = None) -> None:
        j = self._local.get(job_id)
        if j is None:
            return
        j.status = status
        j.result = result
        j.finished_ts = time.time()
        # atualiza o job_queue/ tambem — assim pull_remote_queue nao re-puxa
        self.bus.write(f"job_queue/{job_id}.json",
                       {"job_id": job_id, "kind": j.kind, "payload": j.payload,
                        "status": status, "submitted_ts": j.submitted_ts})
        # resultado vai p/ job_results/ — a bridge local coleta
        self.bus.write(f"job_results/{job_id}.json",
                       {"job_id": job_id, "kind": j.kind, "status": status,
                        "result": result, "finished_ts": j.finished_ts})

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for j in self._local.values():
            out[j.status] = out.get(j.status, 0) + 1
        return out


def _deep_tuple(o):
    """JSON serializa tuplas como listas — reconverte recursivamente."""
    return tuple(_deep_tuple(x) for x in o) if isinstance(o, (list, tuple)) else o


def default_worker(payload: Dict) -> Dict:
    """Worker padrao — trata todos os kinds que a estacao conhece.

    mesh_series  -> malha cross-layer completa
    classify     -> SulfateVeinClassifier (veio/acido/lixivia)
    synthesis    -> registra no gap-watch e cruza
    outros       -> ack
    """
    kind = payload.get("kind", "data")
    body = payload.get("payload", payload)
    if kind == "mesh_series" and isinstance(body.get("series"), dict):
        try:
            from mars_cross_layer import MarsCrossLayer
        except ImportError:
            from src.agriculture.mars_cross_layer import MarsCrossLayer
        out = MarsCrossLayer().build_mesh(
            body["series"], bridges=MarsCrossLayer.STANDARD_BRIDGES)
        return {"kind": "mesh_result", "n_edges": len(out["edges"]),
                "real_edges": [{"a": e["a"], "b": e["b"], "corr": e["corr"],
                                "diff": e.get("corr_diff", 0)}
                               for e in out["edges"] if not e.get("trend_artifact")],
                "plausible_bridges": [b["bridge"] for b in out["bridges"]
                                      if b["plausible"]]}
    if kind == "classify" and isinstance(body.get("mineralogy"), dict):
        try:
            from regolith_processor import SulfateVeinClassifier
        except ImportError:
            from src.agriculture.regolith_processor import SulfateVeinClassifier
        r = SulfateVeinClassifier().classify(body["mineralogy"])
        return {"kind": "classify_result", "sample": body.get("sample"), **r}
    if kind == "synthesis":
        return {"kind": "synthesis_logged", "received": body.get("synthesis"),
                "note": "registrado p/ cruzamento futuro"}
    return {"kind": "ack", "received": kind}


@dataclass
class MarsDaemon:
    """O servidor autonomo que vive na VM do Colab.

    Cada ciclo: (1) puxa inbox_local/ novos do OmniMind, (2) roda o trabalho
    (malha/sintese/simulacao), (3) grava respostas em inbox_colab/,
    (4) checkpointa ao HF se passou o intervalo.
    """

    budget_hours: float = 11.5
    checkpoint_every_s: float = 300.0
    bus: _HFBus = field(default_factory=_HFBus)
    state: DaemonCheckpoint = field(default_factory=DaemonCheckpoint)
    worker: Optional[Callable[[Dict], Dict]] = None   # funcao de trabalho
    n_workers: int = 8                               # Colab Pro: 8 vCPUs
    queue: JobQueue = field(init=False)
    simulator: StationUnifiedSimulator = field(default_factory=StationUnifiedSimulator)

    STATE_PATH = "daemon_state/checkpoint_colab.json"
    # legado: caminho antigo compartilhado com o kernel Kaggle (colisao de
    # schema — o Kaggle grava station_telemetry no mesmo path)
    LEGACY_STATE_PATH = "daemon_state/mars_daemon_checkpoint.json"

    def __post_init__(self):
        self.queue = JobQueue(self.bus)

    # ---- checkpoint soberano ----
    def save_checkpoint(self) -> None:
        self.state.rng_state = random.getstate()
        self.state.station_snapshot = self.simulator.snapshot()
        self.bus.write(self.STATE_PATH, self.state.to_dict())
        self.bus.flush()           # checkpoint = ponto de persistencia (1 commit)

    def restore_checkpoint(self) -> bool:
        d = self.bus.read(self.STATE_PATH)
        if d is None:
            d = self.bus.read(self.LEGACY_STATE_PATH)
        # rejeita checkpoint de outro escritor (Kaggle grava outro schema
        # no path legado — restaurar isso misturaria contadores)
        if not isinstance(d, dict) or ("rng_state" not in d and "station_snapshot" not in d):
            return False
        self.state = DaemonCheckpoint.from_dict(d)
        if self.state.rng_state:
            random.setstate(_deep_tuple(self.state.rng_state))
        if self.state.station_snapshot:
            self.simulator.restore_from_snapshot(self.state.station_snapshot)
        return True

    # ---- um ciclo de trabalho ----
    def run_cycle(self) -> Dict:
        st = self.state
        st.cycle += 1
        
        # 1. Avanço da estação no simulador unificado (pontua níveis e produção)
        station_step = self.simulator.step()
        st.station_snapshot = self.simulator.snapshot()

        inbox_new = [f for f in self.bus.list_inbox("local")
                     if f not in st.processed_inbox]
        results = {"cycle": st.cycle, "inbox_consumed": [], "outputs": {}, "station": station_step}
        for path in inbox_new:
            payload = self.bus.read(path)
            if payload is None:
                continue
            # o trabalho: cruza o payload com o estado (worker injetavel)
            out = (self.worker or default_worker)(payload)
            resp_path = path.replace("inbox_local/", "inbox_colab/")
            self.bus.write(resp_path, {"in_response_to": path,
                                       "cycle": st.cycle, "result": out})
            results["inbox_consumed"].append(path)
            st.processed_inbox.append(path)
        # puxa jobs remotos submetidos pela bridge e drena em paralelo
        self.pull_remote_queue()
        results["queue"] = self.drain_queue()
        # flush oportuno se o buffer encheu (protege rate limit 256 commits/h)
        if len(self.bus._pending) >= 20:
            self.bus.flush()
        st.last_results = results
        return results

    # ---- despacho da fila em paralelo (8 workers do Colab Pro) ----
    def submit_job(self, kind: str, payload: Dict, job_id: Optional[str] = None) -> str:
        import uuid
        job_id = job_id or f"{kind}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        return self.queue.submit(Job(job_id=job_id, kind=kind, payload=payload))

    def pull_remote_queue(self) -> int:
        """Importa jobs do HF job_queue/ que ainda nao estao na fila local."""
        pulled = 0
        for path in self._list_prefix("job_queue/"):
            d = self.bus.read(path)
            if not d or d.get("status") != "queued":
                continue
            jid = d.get("job_id", path.split("/")[-1].replace(".json", ""))
            local = self.queue._local.get(jid)
            if local is not None and local.status in ("running", "done", "failed"):
                continue                       # ja despachado nesta sessao
            if local is None:
                self.queue._local[jid] = Job(job_id=jid, kind=d.get("kind", "job"),
                                             payload=d.get("payload", {}),
                                             submitted_ts=d.get("submitted_ts", 0))
            pulled += 1
        return pulled

    def _list_prefix(self, prefix: str) -> List[str]:
        return sorted(f for f in self.bus.list_files() if f.startswith(prefix))

    def drain_queue(self) -> Dict[str, int]:
        """Executa todos os jobs queued em paralelo no pool de n_workers."""
        queued = [j for j in self.queue._local.values() if j.status == "queued"]
        if not queued:
            return {"dispatched": 0}
        def _run(j: Job) -> None:
            self.queue.mark(j.job_id, "running")
            try:
                self.queue.mark(j.job_id, "done",
                                (self.worker or default_worker)(j.payload))
            except Exception as e:
                self.queue.mark(j.job_id, "failed", {"error": str(e)})
        with ThreadPoolExecutor(max_workers=self.n_workers) as ex:
            list(ex.map(_run, queued))
        return {"dispatched": len(queued), **self.queue.counts()}

    # ---- loop soberano ----
    def run(self, max_cycles: Optional[int] = None) -> DaemonCheckpoint:
        """Loop de ~budget_hours com checkpoint periodico. Retoma se restart.

        BUG (2026-09-28): elapsed media started_ts+uptime_s RESTAURADOS —
        budget cumulativo esgotado fazia o daemon sair no 1o ciclo apos
        restart do kernel. Corrigido: budget e POR SESSAO (session_start
        local); uptime_s segue acumulando so como telemetria historica."""
        self.restore_checkpoint()
        session_start = time.time()
        self.state.started_ts = session_start      # ancora desta sessao
        last_ckpt = session_start
        budget_s = self.budget_hours * 3600
        while True:
            if max_cycles and self.state.cycle >= max_cycles:
                break
            if time.time() - session_start >= budget_s:
                break
            self.run_cycle()
            if time.time() - last_ckpt >= self.checkpoint_every_s:
                self.save_checkpoint()
                last_ckpt = time.time()
        self.state.uptime_s += time.time() - session_start
        self.save_checkpoint()   # checkpoint final — sobrevive a desconexao
        return self.state
