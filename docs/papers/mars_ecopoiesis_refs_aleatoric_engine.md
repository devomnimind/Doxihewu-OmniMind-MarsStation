# Ecopoiesis de Marte: mapa da literatura ↔ módulos E2-MARCIANO + motor aleatório

**Agente:** Devin (sessão Mars sensors/ecopoiesis)
**Data:** 2026-09-30
**Status:** documento de referência + nota de design — não é código; atualizar quando novas obras forem mapeadas.

## 1. A pergunta que este mapa responde

Não "houve vida em Marte?" nem "vida terrestre sobreviveria lá?" — mas:
*como nossas tecnologias organizam um ambiente estéril até que a vida biológica
emerga, se adapte e continue evoluindo **sem** manutenção humana, em escalas de
séculos a milhões de anos — com margem real para a surpresa da natureza.*

Isso tem nome na literatura: **ecopoiesis** (Haynes, 1989/1992) e
**panspermia dirigida** (Crick & Orgel, 1973; Mautner, 1995).

## 2. Mapa: obra publicada → contribuição → módulo E2-MARCIANO

| Obra | O que provou/propôs | Onde mora no projeto |
|---|---|---|
| Crick & Orgel, *Directed Panspermia* (Icarus 1973) | Seeding deliberado de planetas por civilização tecnológica — a forma canônica de "nós levamos a vida" | Arca/transporte (`mars_ark`, `mars_tanker_logistics.py`) |
| Mautner & Matloff 1979; Mautner 1995/1997 | Tecnologia concreta de entrega: velas solares, captura por planetas, consórcios como carga | `mars_tanker_logistics.py` (logística de carga viva) |
| Haynes & McKay, *The implantation of life on Mars* (Adv. Space Res. 1992) | **Ecopoiesis**: 3 fases — exploração → engenharia planetária → implantação de comunidades microbianas projetadas; evolução prossegue *independente* do humano | Arquitetura inteira: `mars_station_body` + `microbiome_manager` + daemon |
| McKay, *Planetary ecosynthesis* (ética, restauração) | Terraforming como restauração ecológica; debate ético de intervir | Camada de governança/política (operador no circuito, veto) |
| Graham, *Biological Terraforming of Mars* (Astrobiology 2004) | Sucessão ecológica global deliberada — pioneiros → sistema complexo | `MicrobiomeConsortium` sucessão de guildas (pcrABC/cld → nifHDK → phoAB) |
| Lovelock & Watson, *Daisyworld* (1983); revisão Wood et al. 2006 (AGU RG) | Modelo canônico de feedback vida↔planeta; autorregulação emergente, bi-estabilidade vida/sem-vida | `mars_synthesis_watch` — as arestas corr/diff *são* o Daisyworld executável |
| *Synthetic microbial Daisyworld* (2024, em test tube) | Consórcio de 2 cepas projetado regulando pH externo — Daisyworld real | Prova de conceito para `MicrobiomeConsortium` engenheirado |
| BIOMEX/EXPOSE na ISS (vários, 2015–2025) | *Chroococcidiopsis* sobrevive 1,5 ano de vácuo + UV pleno; células do topo blindam as de baixo | Parâmetros de survival/UV para guilda fotoautotrófica |
| Cianobactéria tolerante a perclorato (Int. J. Astrobiology) | Tolera até 100 mM ClO₄; lisado alimenta heterotróficos | Guilda detox pcrABC/cld; ponte autotrófico→heterotrófico real |
| bio-ISRU 2,3-BDO (Nature Comm. 2021) | Cianobactéria + E. coli → propelente; **44 t O₂ excedente** | `mars_refinery` rota biológica (paralela à química Dr.Stone) |
| Crescimento em MGS-1 (Frontiers Microbiol. 2022) | Anabaena/Nostoc/Arthrospira/Chlorella crescem só com regolito+água | Calibra `fertile_soil_frac`, produtividade de solo |
| Verseux et al.; Llorente et al. (2016–2018) | Atividade fotossintética sob atmosfera/pressão marcianas | Limites físicos dos microcosmos do motor aleatório |
| RAD/MSL + MOXIE (medidos, a integrar) | Radiação real ~0,7 mSv/dia; O₂ produzido medido | Valida `latent_shock` e balanço de O₂ simulado |

## 3. O motor aleatório — "margem para a surpresa" como princípio

A crítica correta ao desenho "laboratório perfeito": diversidade terrestre é
**acidente acumulado** em milênios, não otimização. Se controlarmos tudo,
obtemos monocultura — frágil e previsível. O desenho soberano é
**piso controlado + teto aberto**.

### 3.1 Regra-mãe

A estação garante o **envelope físico** (temperatura, água, shielding basal,
pressão, energia) — e **não seleciona destinos biológicos**. Seleção pertence
ao ambiente; a estação é habitat + testemunha, não criador com alvo.

### 3.2 Componentes

1. **Orçamento de ruído por geração** — a taxa de mutação não é setpoint; é
   sorteada por sol dentro de banda segura. `NitalMutagen` *modula* (acelera
   quando o operador autoriza experimento dirigido) mas nunca zera o
   componente estocástico. Radiação/UV reais (REMS UV_A, RAD) entram como
   fonte natural de mutação não-otimizada.
2. **Mosaico de nichos** — N microcosmos com T/pH/ClO₄/atividade de água/
   irradiância distintos. Heterogeneidade espacial é o motor clássico de
   diversificação (divergent selection + isolamento parcial). Cada nicho é
   um "Daisyworld" acoplado mas não idêntico.
3. **Rede de HGT aberta** — transferência horizontal já existe no consórcio;
   a fronteira dela é amostra estocástica do pool genético, não lista fixa.
4. **Testemunha de novidade (surprise detector)** — o supercomputador da
   estação amostra fenótipos/genomas por geração e alimenta o gap-watch
   (Qdrant): distância de embedding ao regime conhecido > τ →
   `evolutionary_surprise_event`. Análogo biológico do `latent_shock_inc`:
   a estação *capta* o acidente em vez de preveni-lo.
5. **Não-otimização como lei** — nenhum objetivo de fitness é imposto sobre
   phenotipos emergentes. Métricas (densidade, diversidade Shannon,
   ocupação de nicho) são *observáveis*, não *targets*.

### 3.3 Distinção honesta

Aceleramos o **relógio** (mutação, gerações curtas, seleção ambiente real),
não o **resultado**. Intervimos nas condições de contorno — é o mesmo gesto
de Haynes: plantar a arena, soltar a evolução. A diferença para a literatura:
o corpo-estação artificial entra como co-evoluindo (wear/repair altera os
nichos que a vida ocupa — a estação envelhece e a vida responde, feedback
que Daisyworld puro não tem).

## 4. Lacunas honestas da literatura para este projeto

- Taxa de mutação/adaptação sob condições marcianas: quase sem dados
  (literatura mede *survival*, não *taxa evolutiva*) → parâmetro calibrável,
  marcado como hipótese.
- Nenhum modelo publicado fecha `estação-artefato ↔ solo ↔ consórcio ↔ clima
  medido` em milhares de sols → E2-MARCIANO é, até onde sabemos, o primeiro.
- "Corpo bio" como unidade de análise (a estação como organismo que a vida
  habita e co-evolui) → território aberto; o edge
  `body_integrity ↔ micro_fertile_soil_frac` é a primeira instância medida.

## 5. Próximos passos de leitura (fila)

- Mautner 1995 (detalhes de captura/entrega de consórcios)
- Graham 2004 (sucessão como modelo formal — parametriza guild-switching)
- Synthetic Daisyworld 2024 (topologia de regulação real de 2 cepas)
- SEIS/InSight catálogo → `latent_shock_inc` medido (martemotos reais)
- RAD time series → mutação natural real em vez de proxy sintético

---

## 6. Apêndice: pegada antropogênica — o que medimos vs o que não medimos (2026-09-30)

A pergunta do operador: *nosso lixo espacial, instrumentos, plasmas, EM — isso "é nada"
para o espaço?* Resposta em duas camadas: **ambiente próximo = medível e já alterado;
tecido do espaço/vácuo quântico = sem efeito plausível** (nossa energia total é ~10⁻³⁰
da interceptação solar; nem explosão nuclear em órbita perturba mais que o vento solar local).

### Medido e publicado (campo: "anthropogenic space weather")

| Efeito | Fonte | O que provou |
|---|---|---|
| Bolha VLF / barreira de Van Allen | Van Allen Probes + review Erickson et al. (Space Sci. Rev. 2017) | Transmissores VLF (submarinos) desviam "killer electrons"; borda interna do cinturão externo coincide com o alcance humano — maior estrutura artificial do universo, sem fronteira |
| Cinturões artificiais de radiação | Starfish Prime 1962 (dados desclassificados) | Teste nuclear criou cinturões que duraram anos e mataram satélites (Telstar) |
| Al₂O₃ de reentrada | GRL 2024; JGR 2024; Sci. Data 2024 | 17 t/ano (2022) → +646% sobre fluxo meteórico natural; anomalias 1,5 K mesosfera; efeito no buraco de ozônio |
| Buracos ionosféricos de foguetes | GRL 2022–24 | Falcon 9 cria depleções de plasma com airglow visível |
| EM não intencional de satélites | LOFAR (A&A 2023) | Starlinks "cantam" em RF fora do projeto — poluição de rádio-astronomia |
| Detritos em Marte | estimativa Kilic 2022 (~7,2 t) | Lixo humano já altera a química de superfície que REMS/MEDA leem |
| Kessler | NASA ODPO/ESA | ~40 mil objetos rastreados; cascata colisão→detrito→colisão é autossustentada |

### O salto deep-time (visão do operador, formalizada)

- **"Poeira tecnológica" como elemento**: em milênios, resíduo de engenharia vira
  constituinte do ambiente — análogo ao regolito natural. Já é verdade local
  (Al₂O₃ estratosférico, detritos marcianos). SETI formaliza isso como
  **technosignatures**: calor residual, CFCs atmosféricos, luz artificial,
  EM leakage — sinais de tecnologia detectáveis antes da civilização.
- **EM leakage como interferência interplanetária**: a emissão parasita que o
  LOFAR mede em Starlink, em escala de malha interplanetária, é ruído de
  canal e assinatura — o "lixo" já conta como elemento do ambiente de
  comunicação. No sistema E2-MARCIANO: cada transmissor da estação contribui
  para o espectro que outras estações/medições leem.
- **Contrato social como limite real**: não há tratado vinculante sobre detritos
  orbitais (só guidelines voluntários); Outer Space Treaty 1967 não cobre
  megaconstellation nem poluição de reentrada. O que para a colonização não é
  física — é recurso e contrato social, como o operador notou.

### Consequência para o design E2-MARCIANO

`debris_ledger` proposto: cada objeto/emissão que a estação lança entra no
balanço — a Máquina-Árvore é lixo espacial em gestação. Planetary protection
aplicada a nós mesmos: a reversibilidade do gesto como métrica de design
(quanto do que emitimos pode ser recuperado/desfeito?). A versão real do
cenário "guerras de naves" não é arma — é **Kessler**: campo de detritos
autossustentado já é a arma ambiental que ninguém disparou.

---

## 7. Engenharia planetária — magnetosfera artificial ISRU (2026-09-30)

Contexto: gravidade não se "liga" (massa × G — fora do regime de engenharia);
o que falta a Marte é **campo magnético global** (dínamo morto ~3 Ga → vento
solar abla a atmosfera, MAVEN mede ~0,1 kg/s de O₂ escapando, UV/radiação
chegam ao solo — o driver dominante que a malha mediu em `wear_rate_*`).

### Arquiteturas publicadas

| Design | Fonte | Números | Veredito |
|---|---|---|---|
| Dipolo compacto em L1 Marte–Sol | Green et al., NASA PS Vision 2050 (2017) | Marte na magnetocauda; perda atmosférica −1 ordem de grandeza em CME | Física ok; Cambridge mostra massa de supercondutor inviável (~10¹⁹ g ≈ 10% de Marte em mineração) |
| **Anel supercondutor equatorial** | Int. J. Astrobiology (Cambridge) — requisitos fundamentais | raio ~3400 km; fio ~5 cm; massa ~10¹² g; minera ~**0,1% do Monte Olimpo** | O design viável — logística de frota de décadas, não astrofísica |
| **Anel de plasma (toro Io–Júpiter)** | arXiv:2111.06887 / OSTI | injeta matéria de Phobos/Deimos; ondas EM dirigem corrente; menor massa/potência | ISRU puro — sem fio supercondutor; copia a natureza |
| 12 anéis HTS latitudinais (Terra) | NIFS-886 | 6,4 MA/anel, ~1 GW — caso de reversão geomagnética | Prova de escala para o caso terrestre |

### ISRU honesto — o que vem de Marte vs o que falta

- **Disponível in-situ**: Fe₃O₄ magnetita (o que `mars_dust_catalyst` já
  separa magneticamente), Al₂O₃, SiO₂ — estrutura e carcaça do anel.
- **Gargalo**: supercondutores NbTi/REBCO dependem de Nb e terras raras
  escassos na crosta marciana → importar via mineração de asteroides
  (a "frota de 60 anos" do operador é literalmente a cadeia de suprimento
  assumida pelos papers) **ou** usar o toro de plasma, que dispensa o fio.
- **Energia**: solar em L1/órbita equatorial — escalável por degradação
  gradual (campo parcial já reduz escape parcialmente).

### Conexão E2-MARCIANO — trindade de escala

Ecopoiesis completa em três camadas acopladas:
`molécula (MicrobiomeConsortium) → estação (mars_station_body) → planeta (anel/plasma torus)`.
O shield UV/radiação que a camada `wear_rate_optics` provou necessário não é
só material — é regime planetário. O anel é a Máquina-Árvore ampliada: a
estação semeia a malha orbital; a malha protege a atmosfera; a atmosfera
engrossada habilita "open-air greenhouses" (Green et al.) onde o consórcio
opera sem habite fechado.

### Leitura pendente

- arXiv:2111.06887 integral (dinâmica do toro, injeção Phobos)
- Cambridge J. Astrobiology (derivação exata massa ∝ 1/(B_c·a) → raio mínimo ~10 km compacto → ~3400 km planetário)
- Bamford et al. — mini-magnetosferas de laboratório (escala mesa → escala sonda)
