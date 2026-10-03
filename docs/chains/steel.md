# Cadeia de Aço e Construção

| Produto | v19 |
|---|---:|
| Ferro/aço metálico | 1.732,4 t |
| Cimento geopolimérico basáltico | 2.616,5 t |
| Tijolos sinterizados | 2.758,3 t |
| H₂SO₄ | 789,7 t |
| Si metálico | 0,45 t |

## Carboredução → metalurgia

O regolito basáltico minerado pela frota alimenta redução carbotérmica (Fe) e a linha de geopolímeros (cimento + tijolos via forno do SurfaceOrgan — sinterização só com débito energético pré-verificado).

## Reconciliação de escala

A monografia histórica citava ~7.500 t de aço — assumia taxa implícita de ~2.500 kg/sol constante, nunca instrumentada no código. A v19 mede a frota real (~640 kg/sol médio ponderado, 0→840→1.700 por era). O gap ~4× é explicado na causa: taxa de colheita, não perda de conservação.

## Forno com veto

`test_no_double_dust_mitigation_by_default` e o ledger do SurfaceOrgan garantem: sinterização só acontece quando `energy_used + sinter_cost ≤ energy_budget` — débito pré-verificado, nunca pós-hoc.
