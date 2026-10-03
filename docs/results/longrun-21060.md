# Longrun Canônico — 21.060 Sols (v19)

**Seed 42 · física pós-auditoria · reprodução bit-a-bit local ≡ Colab**

## Tabela canônica

| Métrica | Valor |
|---|---:|
| Massa útil | **7.897,3 t** |
| Regolito minerado | 12.904 t |
| Solo lixiviado | 52.578 t |
| clean_soil | 52.294 t |
| Fe/aço | 1.732,4 t |
| Cimento | 2.616,5 t |
| Tijolos | 2.758,3 t |
| O₂ | 2.293,9 t |
| H₂SO₄ | 789,7 t |
| CH₄ | 200,1 t |
| Si | 0,45 t |
| Água final | 519.543 L |
| Água mínima | 2.003 L |
| Perclorato processado | ~361 t |
| Incidentes | 217 |
| Integridade | 0,5691 |
| Frota (fab/canib/recond/perdas) | 109 / 64 / 638 / 39 |

## Artefatos

- JSON canônico: `job_results/station_longrun_21060_v19_soilwash.json` no dataset HF `fabricioslv/mars-monoculture-data`
- Checkpoint: `longrun_v19` pickle — restore bit-idêntico (subsystem_state completo)

## Suíte

254 testes verdes — incluindo invariantes de conservação hídrica, ledger energético, restore completo (11 camadas + órgãos + RNG + subsystem_state), presença de órgãos opcionais e sem dupla mitigação de poeira.
