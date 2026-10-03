# Lei da Conservação Pareada

Formalizada no **PH-7** (`docs/tecnico_codigo/PH7_PAIRED_CHANNEL_ESTACAO_ORGANISMO.md`, repo omnimind): **o par é a unidade mínima de confiança** — toda atuação estação→organismo (CH↓) exige medição organismo→estação (CH↑) no mesmo sol.

## As 5 leis do pareamento

1. **Par fechado** — atuação sem medição pareada é canal cego
2. **Histerese, não setpoint** — transições exigem evidência sustentada
3. **Conservação auditável** — massa/energia em CH↓ menos CH↑ é auditável; o desvio vira telemetria, nunca furo silencioso
4. **Veto energético compartilhado** — pool único de 100 kWe
5. **Envelhecimento honesto** — desgaste, canibalização e perda são estado, não exceção

## Taxonomia de falha de acoplamento

| Modo | Sintoma |
|---|---|
| Uplink morto | Comando enviado, organismo não recebe |
| Downlink fujão | Organismo mede, estação não registra |
| Par fantasma | Telemetria reportada sem atuação correspondente |
| Dessincronia de fase | Par ativo mas em sols diferentes |
| Colapso de canal | Ambos os sentidos mortos — organismo órfão |

## Contraexemplo canônico

O bug do scheduler da refinaria (v18): debitava insumos de uma **cópia** `local_stock` — o estoque real nunca era debitado. Conservação violada silenciosamente. Corrigido debitando o plano executado; a lei existe para impedir a classe inteira dessa falha.

## Par mais novo (v19)

`clean_soil ⇄ substrato de estufa` — a usina produz solo desintoxicado; a adoção pela estufa ainda não é modelada (pendência declarada, §Pendências da monografia).
