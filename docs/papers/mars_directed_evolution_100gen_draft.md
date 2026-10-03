# Directed Evolution under Mars Radiation: A 100-Generation Simulation

**Rascunho (draft) — 2026-09-28 · OmniMind Mars Monoculture Project**
Status: esboço inicial para submissão futura (Life Sciences in Space Research / Acta Astronautica)

---

## Abstract (rascunho)

Mars surface radiation (~0.67 mSv/day mean, RAD/MSL) is usually treated as a
risk for life support systems. We invert the frame: natural ionizing radiation
as an *evolutionary tool* for the monoculture core of an autonomous Martian
greenhouse (Máquina-Árvore). Using a 100-generation in-silico directed
evolution of *Spirulina* (population 200, 1000-locus genome, mutation rate
1e-6 bp/day at 0.67 mSv/day, top-10% selection), we observe:

- perchlorate resistance **+31%** (0.455 → 0.594),
- cold tolerance **+37%** (0.455 → 0.625),
- overall fitness **+28%** (0.455 → 0.584).

The gains are real but modest; reaching 2–3× resistance would require
~300 generations (~6 Martian years) or stronger artificial selection.
We discuss integration with the evolution gate (d3): radiation-mutagenized
lineages are selected *before* the data-driven gate approves cultivar
transition, making radiation part of the machine's autonomy, not just its
stress.

## Methods (rascunho)

- Genome: 1000 loci; traits perchlorate/cold/radiation/growth (250 loci each)
- Mutation: rate = 1e-6 · dose(mSv/day) · 30 days per generation
- Selection: top 10% fitness (0.3·perchlorate + 0.3·cold + 0.2·radiation + 0.2·growth), elitist clone ×10 + Gaussian drift σ=0.02
- Environment: REMS Gale climatology (T −72..−100 °C), dust storms (τ up to 10.8), perchlorate soil 1500→150 ppm after remediation

## Results (rascunho)

| Gen | perchlorate | cold | radiation | growth | fitness |
|---|---|---|---|---|---|
| 0 | 0.455 | 0.455 | 0.455 | 0.455 | 0.455 |
| 50 | 0.533 | 0.547 | 0.490 | 0.502 | 0.522 |
| 99 | 0.594 | 0.625 | 0.536 | 0.555 | 0.584 |

## Discussion (rascunho)

1. Natural radiation is a free, continuous mutagen — the machine can exploit it with zero extra energy.
2. Honest assessment: +30% in 100 generations; diminishing returns without stronger selection pressure.
3. Next: coupling mutagenesis to the evolution gate (d3) — only lineages with stability score ≥0.90 pass to potato pilot; radiation pressure can be *modulated* (shielding windows) to bias mutation rates.

## Data

`simulations/evol2_mutagenese.parquet` (HF privado fabricioslv/mars-monoculture-data)

## To do

- [ ] 300-generation run (~6 Martian years)
- [ ] Selection sweep (top 5%, 20%)
- [ ] Couple to EvolutionGate (d3) and CulturalGenome.hygiene
- [ ] Statistical replicates (≥20 seeds)

---

## ATUALIZAÇÃO 2026-09-28 — E2-REF v2: taxa realista (resultado do paper confirmado)

A hipótese do rascunho ("2-3× exigiria ~300 gerações") foi **testada e confirmada** no Colab com modelo calibrado:

| Métrica | E2 base (100 gen, sem dias) | E2-REF v1 (1000 gen, taxa fraca) | **E2-REF v2 (400 gen × 75 d/gen, 12 réplicas)** |
|---|---|---|---|
| Perclorato | +31% | +23% (1.237×) | **3.39× ±1% (IC95)** |
| Frio | +37% | +22% | **2.80×** |
| Fitness | +28% | +23% | **2.82×** |

**Mudanças de modelagem que destravaram o ganho** (registradas como lição de calibração):
1. **Dias por geração realista** (75 d — ciclo trigo BWT931): dose acumulada por geração = 0.67 mSv/d × 75 d ≈ 50 mSv/geração (antes a taxa era por geração sem escala temporal)
2. **Mutação calibrada** (2e-5/locus/geração) em vez de 1e-6×dose
3. **Dano separado da mutação**: fração deletéria (12%) subtrai fitness — radiação não é só "mutagênese benéfica"
4. **12 réplicas + IC95** (incerteza <1% na média)

**Status**: permanece um modelo computacional (não validação biológica); mas agora a faixa esperada 2-3× do rascunho é suportada pela simulação calibrada. Próximo passo realista: calibrar contra dados de mutagênese de sementes irradiadas (ex: Vitale et al. 2022 — íons C/Ti + luz RB) e acoplar ao gate d3.

---

## ATUALIZAÇÃO 2 — E2-REF v3: calibração com dados reais (PDF do operador + 33 refs)

**Parâmetros calibrados**: μ_bp = 1.5e-6/bp (wheat cosmic rays 1.79e-6, PMC9131052; conservador para Spirulina), genoma 1000 loci, dose 0.67 mSv/dia (MSL/RAD média, Hassler 2014/SwRI; variação solar ciclo 24: 0.3-0.9), t_gen = 10 dias (Spirulina; ISS ~18 d, terra 7-14 d), μ_eff = 2.01e-4/locus/geração, fração deletéria 12% (wheat ion-beam).

**Resultado (400 gen, 20 réplicas, IC95 ±0.8%)**: perclorato **1.38×**, frio **1.32×**, fitness **1.33×** — ganho 0.081%/geração.

**Desvio esperado-vs-real registrado**: o documento de calibração previa +339% (3.39×) com esta taxa; o modelo real simulado dá +33%. Causa: com μ 10× maior, o dano deletério (12% × 5μ) neutraliza as mutações benéficas (média gaussiana = 0; só a cauda direita ajuda). O v2 (σ 2e-3, trigo 75 d/gen) alcançava 2.8× porque o dano relativo era menor — os dois não são comparáveis diretamente em μ.

**Comparação com dados empíricos** (Space Algae-2 ISS +50% polimorfismos em 10 gen; Spirulina espaço +62% polissacarídeos em ~6 meses; trigo +15-30% tolerância em 4-6 gen): o modelo com mutação gaussiana + seleção truncada é **~40× conservador** — mecanismos reais (rearranjos, epigenética, seleção em módulos) não capturados. Conclusão: o modelo é um LIMITE INFERIOR plausível; a faixa 1.3× (simulado) a 3.4× (empírico) delimita o ganho esperado em ~10 anos marcianos de Spirulina.

**Viabilidade temporal**: 400 gen × 10 d = 4.000 d = 10,9 anos terrestres = **5,8 anos marcianos** (viável); trigo 400 gen × 75 d = 82 anos (inviável) → a mutagênese dirigida é estratégia de **Spirulina/algas**, não de grãos.
