# Corpo da Estação — 11 Camadas

`src/mars_station_body.py`

A estação não é um edifício — é um corpo de camadas empilhadas cuja integridade composta decai sob incidentes e é restaurada por reparo (`repair_fraction = 0.12`).

## Cascata de integridade

A integridade global é o produto da saúde das camadas; incidentes sísmicos/dusto-térmicos degradam camadas específicas. Estado final v19: **integridade 0,5691** após 217 incidentes.

## Superfícies canônicas de estado

O snapshot de checkpoint persiste, além do RNG Mersenne e histórico, o `subsystem_state`:

- `regime` — histerese S-Meta (`s_meta`, `_pending`, `_integrity_hist` de 30 sols)
- `mesh` — filtros Kalman (`vbkf x/P/nu/tau`, `afex.ema`, `glia`)
- `dcs`, `refinery` — escalares operacionais
- `soil_wash` — acumuladores da usina de lixiviação

A garantia medida: **restaurar-e-continuar é bit-idêntico a nunca ter parado** (teste `test_restore_preserves_body_and_rng` + extensão subsystem_state).

## Órgãos acoplados

| Órgão | Módulo | Função |
|---|---|---|
| SurfaceOrgan | `mars_surface_organ.py` | Pele EDS + berm + forno |
| ExcavatorFleet | `mars_excavator_fleet.py` | Colheita + banco de reparo |
| SoilWashPlant | `mars_soil_wash.py` | Lixiviação era-escalada |
| Boundary (airlock/EVA) | `mars_shielding_materials.py` | AirlockOrgan + ShieldStack |
| Refinaria | `mars_refinery.py` | Scheduler estequiométrico |
| Malha/regime | `mars_station_mesh.py`, regime | Kalman + histerese |

!!! warning "Degradação silenciosa proibida"
    `TestOptionalOrganPresence` trava a suíte se qualquer import opcional de órgão resolver `None` — lição da v18.1, quando a ausência de `mars_shielding_materials.py` no ambiente remoto removeu airlock/EVA (8 draws de RNG/sol) e blindagem UV/rad (+28 incidentes) sem erro.
