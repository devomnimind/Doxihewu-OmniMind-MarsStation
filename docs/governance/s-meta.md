# S-Meta — Regime e Carta

A estação opera sob um meta-regime com **histerese**, não setpoint: transições de regime exigem evidência sustentada (`_integrity_hist` de 30 sols, estado `_pending` com contador), evitando oscilação em fronteira.

## Vetos compartilhados

- **Veto energético**: frota, usina de lavagem, EDS, forno e ECLSS disputam o mesmo pool de 100 kWe — nenhum órgão desenha energia que não existe
- **Revisão de meia-vida**: overhaul obrigatório no Sínodo 14 (sol ~10.920) — troca de selos e atuadores na provisão pesada

## Estado persistido

O regime vive no checkpoint (`subsystem_state.regime`): `s_meta`, `_pending`, `_integrity_hist`. Um restore que reiniciasse a histerese do zero estaria mentindo — o teste de restore bit-idêntico trava isso.
