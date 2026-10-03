# ExcavatorFleet — Frota Viva

`src/mars_excavator_fleet.py`

A frota substituiu a constante mágica de 340 kg/sol (v17) por um órgão de colheita com história, desgaste e reciclagem.

## Capacidade por era

| Era | Capacidade unitária | Caráter |
|---|---:|---|
| I | — | sem frota |
| II | ~85 kg/sol/unidade | rovers pequenos, raízes |
| III | média | crescimento |
| IV | haulers industriais | copa explosiva |

## Economia circular interna

- **Canibalização**: unidade esgotada → 70% do chassi vira `spare_parts`, 18% volta como Fe — nunca perda
- **Recondicionamento**: peças do banco restauram saúde (+0,2 por 25 kg) e remontam chassi
- **Auto-fabricação** (Era III+): unidades novas custam 350 kg do próprio Fe da estação
- **Perda real só em missão externa**: incidente latente > 2,2 pode perder uma unidade fora da estação

## Números v19

| Métrica | Valor |
|---|---:|
| Regolito minerado | 12.904 t |
| Unidades fabricadas | 109 |
| Canibalizadas | 64 |
| Recondicionamentos | 638 |
| Perdidas em missão | 39 |

O churn é financiado pela colheita, não por importação — a frota paga o próprio custo.

## Veto energético

Mineração debita energia do pool de 100 kWe compartilhado com EDS, forno, ECLSS e usina de lavagem — `labor_bonus` converte excedente de peças em horas de trabalho (draw limitado, com reserva para manutenção da frota).
