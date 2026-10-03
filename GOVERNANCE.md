# GOVERNANCE — E2-MARCIANO

Regras operacionais derivadas da monografia (PARTE VII — Ecopoiese Aberta,
Governança e Regras de Veto). Este documento resume; a fonte canônica é
`docs/papers/mars_monografia_sistema_arvore_ecopoiese.md`.

## Piso Controlado + Teto Aberto

- **Piso**: cadeias de recurso (água, O₂, N, energia) e integridade corporal
  operam sob vetos determinísticos — nenhum otimizador adaptativo pode
  desligar uma cadeia viva nem rebaixar um veto de segurança.
- **Teto**: acima do piso, o sistema é aberto — evolução aleatória
  (NoiseBudget, HGTPool, NicheMosaic) produz trajetórias que o design não
  antecipou. Margem para a natureza é lei, não metáfora.

## Vetos operacionais

1. **Veto de toxicidade sistêmica** — linhagem que envenene ciclo hídrico ou
   corrompa membrana além da capacidade ECLSS → quarentena (`StationGlia`).
2. **Veto de integridade** — `body_integrity` abaixo de limiar por camada →
   supressão da carga agregadora correspondente.
3. **Veto de reversibilidade** — ação irreversível sem buffer redundante →
   bloqueio até redundância.

## Habitability Gate (Sínodo 17 / 36,3 anos terrestres)

Sete critérios objetivos G1–G7 auditam a transição para biosfera aberta —
ver monografia §"O Portal de Habitabilidade". Decisão binária com cláusulas
de veto e rollback explícitas.

## Honestidade de calibração

- Regimes do classificador são **homologias operacionais**, não identidade
  biológica: `metabolic_habitat` ≠ metabolismo vivo.
- Surpresa é definida relativamente ao próprio regime do nicho (>4σ da
  dispersão local) — nunca por limiar absoluto importado.
- Mutagênese dirigida (Nital) acelera o relógio estocástico; não fabrica
  novidade nem elimina aleatoriedade.

## Contribuição

Ver `NOTICE.md` para o padrão de autoria. Mudanças substantivas em física
ou semântica de regime exigem atualização do `contracts/` correspondente
e revalidação da suíte de 229 testes.
