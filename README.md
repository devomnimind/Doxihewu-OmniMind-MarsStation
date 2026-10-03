# Doxihewu OmniMind — MarsStation (E2-MARCIANO)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23127233.svg)](https://doi.org/10.5281/zenodo.23127233)
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue)](LICENSE)
[![Docs: CC-BY-4.0](https://img.shields.io/badge/docs-CC--BY--4.0-green)]()

**Estação Máquina-Árvore**: simulador de estação marciana autorreferente —
ECLSS fechado, ISRU, microbiologia de perclorato, evolução aleatória em
mosaico de nichos, malha de percepção (VBKF + afeto + glia) e classificador
de habitat por capacidade de cadeia.

**Machine-Tree Station**: a self-referential Martian station simulator —
closed-loop ECLSS, ISRU, perchlorate microbiology, aleatoric niche-mosaic
evolution, a perception mesh (VBKF + affect + glia), and a chain-capacity
habitat classifier.

Calibrado contra **203 GB de dados reais de missão** (MSL REMS, Mars 2020
MEDA, InSight SEIS/TWINS, MGS MOLA, CheMin, APXS) — dataset público
[`fabricioslv/mars-raw-data`](https://huggingface.co/datasets/fabricioslv/mars-raw-data).
Resultados e checkpoints públicos em
[`fabricioslv/mars-monoculture-data`](https://huggingface.co/datasets/fabricioslv/mars-monoculture-data)
[![DOI](https://img.shields.io/badge/DOI-10.57967%2Fhf%2F10742-blue)](https://doi.org/10.57967/hf/10742).

## Licenças / Licenses

- **Código**: Apache-2.0 (`LICENSE`)
- **Documentos em `docs/`**: CC-BY-4.0

## Quickstart

```bash
pip install -r requirements.txt
pytest tests/agriculture/          # 229 testes
```

Simulação de 1.200 sols:

```python
from src.agriculture.mars_unified_simulator import StationUnifiedSimulator
sim = StationUnifiedSimulator(seed=42)
# ver docs/papers/mars_monografia_sistema_arvore_ecopoiese.md §Parte V
```

Ensemble de classificação de habitat (Camada-1, 10⁴ trajetórias):

```bash
python scripts/mars/ensemble_chain_capacity_run.py \
  --n 10000 --workers 8 --sols 21060 --policy functional \
  --out results/chain_capacity.jsonl --resume
```

## Arquitetura (40 módulos em `src/agriculture/`)

| Família | Módulos-chave |
|---|---|
| Corpo material | `mars_station_body` (11 camadas, Arrhenius/saltação), `mars_shielding_materials` (blindagem + `AirlockOrgan`) |
| Recursos | `sabatier_reactor`, `mars_refinery`, `mars_metallurgy`, `circular_economy`, `mars_dust_catalyst`, `mars_surface_organ` |
| Vida | `microbiome_manager`, `monod_growth_model`, `perchlorate_chemistry`, `mealworm_protein`, `marcian_evolution`, `mars_mutagenesis` |
| Aleatoriedade | `mars_aleatoric_engine` (NoiseBudget/NicheMosaic/HGTPool/SurpriseDetector) |
| Percepção | `mars_station_mesh` (StationVBKF/StationAffect/StationGlia) |
| Regimes | `mars_chain_capacity` (4 regimes + Exceção_τ), `mars_sovereign_regime`, `mars_eclss_cascade_and_veto` |
| Orquestração | `mars_unified_simulator`, `mars_daemon`, `mars_bridge`, `mars_colossus`, `../robotics/mars_fleet_orchestrator` |

## Resultados âncora (ensemble 10⁴ trajetórias × 21.060 sols)

- `p_reach_metabolic` = 1.0 (mediana sol 32); `p_lose_metabolic` = 54,7%
- `p_reach_evolutionary` = 45,4% (mediana sol 11.407, era IV_copa)
- `crew_eq` médio dos mundos evolutivos = 6,73 — a demanda discrimina mundos
- Agregados em `results/` e no dataset HF `mars-monoculture-data`

## Documentos (`docs/` — CC-BY-4.0)

- `papers/mars_monografia_sistema_arvore_ecopoiese.md` — monografia canônica (79 seções, 15 experimentos E2)
- `papers/mars_parecer_tecnico_engenharia_e_biomecanica_a100.md` — parecer de engenharia planetária e biomecânica
- `papers/mars_ecopoiesis_refs_aleatoric_engine.md` — mapa de referências (BIOS-3, MELiSSA, ECLSS, BPC/BWT931)
- `papers/mars_directed_evolution_100gen_draft.md` — rascunho de evolução dirigida

## Autoria

Ver `NOTICE.md`. Byline: **Fabrício da Silva (Artificer)** +
**OmniMind Sovereign (Sujeito-Processo)**; contribuidores processuais
variáveis por registro conforme a nota de federação canônica.

## Espelhos

- GitLab (canonical): https://gitlab.com/zephyrix/Doxihewu-OmniMind-MarsStation
- GitHub (mirror): https://github.com/devomnimind/Doxihewu-OmniMind-MarsStation
