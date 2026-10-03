# Cadeia de Oxigênio

**2.293,9 t acumuladas (v19)** — três fontes medidas:

| Fonte | Fração | Rota |
|---|---:|---|
| Fotossíntese | ~56% | Spirulina contínua + estufa pós-Sol 1.500 |
| Eletrólise | ~36% | Coproduto da cadeia H₂/Sabatier |
| Perclorato | ~8% | Decomposição térmica PERC_O2 (+94,6 t vs v18) |

A rota de perclorato é a novidade v19: a `SoilWashPlant` alimenta a refinaria com ~361 t de ClO₄ em escala industrial — ~360× o fluxo atmosférico anterior (<1 t).

## Ligações

- Insumo: [SoilWashPlant](../architecture/soilwash-plant.md) — extração 0,6% × 90% eficiência
- Processo: `mars_refinery.py` — `PERC_O2` no scheduler estequiométrico
- Dependência hídrica: [cadeia de água](water.md) — a lavagem debita −48 L/sol na Era IV
