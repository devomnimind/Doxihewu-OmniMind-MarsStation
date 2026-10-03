# Cadeia de Água

Gelo subsuperficial → elevador era-escalado → reservatório → eletrólise (H₂ + O₂) → Sabatier (CO₂ + H₂ → CH₄ + H₂O) → retorno ao reservatório.

## Números v19

| Métrica | Valor |
|---|---:|
| Água final | 519.543 L |
| Mínimo histórico | 2.003 L (rampa da Era II) |
| CH₄ acumulado | 200,1 t |
| Custo v19 (lavagem) | −48 L/sol na Era IV |

O **elevador de gelo** sustenta o piso emergencial (~2.000 L) até a mineração industrial entrar em escala — a curva nunca cruza zero.

## Conservação auditável

`test_electrolysis_sabatier_water_net_consumer` + `test_ice_chain_scales_with_era` — a eletrólise é consumidora líquida de água (Sabatier recupera parte, não tudo) e a cadeia de gelo escala por era. Invariantes travados em teste, não em comentário.
