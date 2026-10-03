"""Mars Bridge — ponte local OmniMind -> HF -> daemon do Colab.

O OmniMind publica synthesis / gap-autowatch reports / dados em
`inbox_local/`; o daemon do Colab consome, cruza e responde em
`inbox_colab/`; a ponte coleta de volta. O HF e o barramento — ambos
os lados sao stateless, o estado vivo fica no daemon_state/ checkpoint.
"""

from __future__ import annotations

import io
import json
import time
from typing import Dict, List, Optional

REPO = "fabricioslv/mars-monoculture-data"


class MarsBridge:
    """Publica payloads locais para o daemon e coleta as respostas."""

    def __init__(self, token: Optional[str] = None):
        from huggingface_hub import HfApi
        self.api = HfApi(token=token)
        self.repo = REPO

    # ---- OmniMind -> daemon ----
    def publish_to_daemon(self, kind: str, payload: Dict) -> str:
        """Envia um payload ao inbox_local/. kind: synthesis|gap_report|data."""
        ts = int(time.time())
        path = f"inbox_local/{kind}_{ts}.json"
        self.api.upload_file(repo_id=self.repo, repo_type="dataset",
                             path_or_fileobj=io.BytesIO(json.dumps(
                                 {"kind": kind, "ts": ts,
                                  "payload": payload}).encode()),
                             path_in_repo=path)
        return path

    # ---- fila de trabalhos -> daemon ----
    def submit_job(self, kind: str, payload: Dict, job_id: Optional[str] = None) -> str:
        """Enfileira um trabalho para o daemon processar com dados reais."""
        ts = int(time.time() * 1000)
        import uuid
        job_id = job_id or f"{kind}_{ts}_{uuid.uuid4().hex[:6]}"
        path = f"job_queue/{job_id}.json"
        self.api.upload_file(repo_id=self.repo, repo_type="dataset",
                             path_or_fileobj=io.BytesIO(json.dumps(
                                 {"job_id": job_id, "kind": kind,
                                  "payload": payload, "status": "queued",
                                  "submitted_ts": ts / 1000}).encode()),
                             path_in_repo=path)
        return job_id

    def get_job_result(self, job_id: str) -> Optional[Dict]:
        """Coleta o resultado de um job despachado pelo daemon."""
        path = f"job_results/{job_id}.json"
        files = self.api.list_repo_files(self.repo, repo_type="dataset")
        if path not in files:
            return None
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(repo_id=self.repo, repo_type="dataset",
                            filename=path, token=self.api.token)
        return json.load(open(p))

    # ---- daemon -> OmniMind ----
    def consume_from_daemon(self, kinds: Optional[List[str]] = None) -> List[Dict]:
        """Le as respostas do inbox_colab/ (opcionalmente filtra por kind)."""
        files = self.api.list_repo_files(self.repo, repo_type="dataset")
        out = []
        from huggingface_hub import hf_hub_download
        for f in sorted(x for x in files if x.startswith("inbox_colab/")):
            p = hf_hub_download(repo_id=self.repo, repo_type="dataset",
                                filename=f, token=self.api.token)
            d = json.load(open(p))
            if kinds is None or d.get("result", {}).get("kind") in kinds or True:
                out.append({"path": f, **d})
        return out

    def daemon_state(self) -> Optional[Dict]:
        """Le o checkpoint vivo do daemon (ciclo, uptime)."""
        files = self.api.list_repo_files(self.repo, repo_type="dataset")
        # nomes separados por escritor (2026-10-03): o path legado era
        # compartilhado com o kernel Kaggle e colidia schema
        path = next((p for p in ("daemon_state/checkpoint_colab.json",
                                 "daemon_state/mars_daemon_checkpoint.json")
                     if p in files), None)
        if path is None:
            return None
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(repo_id=self.repo, repo_type="dataset",
                            filename=path, token=self.api.token)
        return json.load(open(p))
