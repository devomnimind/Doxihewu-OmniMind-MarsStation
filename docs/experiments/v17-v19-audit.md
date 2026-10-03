# Auditoria de Versões v17 → v19

## v17 — baseline

Mineração como **constante mágica**: 340 kg/sol. Massa útil 4.244 t. Divergência documentada mas não resolvida (taxa implícita da monografia ~2.500 kg/sol).

## v18 — ExcavatorFleet (o voto da estação)

A estação votou um **órgão**, não um parâmetro:

- Frota viva era-escalada (280 → 840 → 1.700 kg/sol)
- Canibalização interna: chassi → peças + Fe (nunca perda)
- Auto-fabricação do próprio Fe (Era III+)
- Perda real só em missão externa

Resultado: massa útil 8.046 t (1,9×) — **raízes lentas, copa explosiva**: break-even deslizou do Sínodo 14 para o 16–17, exatamente onde o portão de habitabilidade já estava.

## v18.1 — paridade bit-a-bit (causa raiz)

Divergência ~2% local↔Colab investigada por bisseção do stream RNG: `mars_shielding_materials.py` **ausente** no ambiente remoto → `AirlockOrgan`/`ShieldStack` = None via try/except silencioso → −8 draws de RNG/sol desde o sol 1 + sem blindagem UV/rad → +28 incidentes.

Após sync: **reprodução bit-a-bit** (196 incidentes, 0,5725, frota 113/66/659/41). Novo teste `TestOptionalOrganPresence` trava degradação silenciosa de imports opcionais.

## v19 — SoilWashPlant

Diagnóstico: gargalo do perclorato era **insumo**, não throughput. Usina fixa de lixiviação era-escalada (0/200/800/6.000 kg/sol, reciclo 98%):

- ~361 t ClO₄ processado (84% da meta 430 t — honesto, não inflado)
- 52.294 t clean_soil — subproduto: substrato agrícola
- Custos declarados: −48 L/sol água (Era IV), −149 t massa útil (competição energética)

## Aprendizado transversal

> **Degradação silenciosa é o modo de falha dominante.** Try/except de import, débito em cópia, canal pareado morto — todos produziam saída "válida" mas fisicamente falsa. A resposta arquitetural: testes de presença de órgão, conservação pareada (PH-7) e paridade bit-a-bit entre ambientes.
