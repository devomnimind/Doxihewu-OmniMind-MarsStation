"""REMS Column Dictionary — mapeamento oficial PDS MODRDR6 <-> parquet.

O consolidado `rems/rems_daily.parquet` (3354 sols) guarda a média diária
dos campos NUMÉRICOS do RMD (REMS_QRS v2.2.0), verificada valor a valor
contra `RME_530075437RMD14940000000_______P2.TAB` (sol 1494): as 37
colunas `c0..c36` são os campos 3..39 do formato `LABEL/MODRDR6.FMT`
(PDS3, mslrem_1001), com TIMESTAMP/LMST/LTST descartados.

Fonte: https://atmos.nmsu.edu/PDS/data/mslrem_1001/LABEL/MODRDR6.FMT
Sentinela de dado ausente: -999.00 (campos numéricos), "X"/NaN (texto).

ATENÇÃO — contaminação conhecida do parquet v1: a média diária incluiu
o sentinela -999. Colunas esparsas ficam enviesadas para negativo:
  - vento (c0-c2): ~100% sentinela — o wind sensor REMS quebrou no pouso
    (hardware morto, não falha de parse; VWS nunca tem dado real)
  - UV (c14-c19): ~24% sentinela/sol -> média ~-245 espúria; as 6 bandas
    correlacionam 1.0 por missingness compartilhada (sensor apaga inteiro)
  - BOOM1/AMBIENT/PRESSURE: 0% sentinela — séries confiáveis
Fix: rems_daily_v2_clean.parquet — média só de valores >-900 + coluna
`*_coverage` (fração de amostras válidas por sol = sinal de saúde do
instrumento, útil ele mesmo na malha).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RemsColumn:
    """Uma coluna física do dicionário REMS MODRDR (PDS3)."""
    fmt_index: int          # posição 0..39 no MODRDR6.FMT / linha TAB
    parquet_col: Optional[str]   # 'cN' se presente no parquet, None se dropada
    name: str               # nome oficial PDS3
    unit: str               # unidade PDS ('' = sem unidade / texto)
    kind: str               # 'measurement' | 'uncertainty' | 'confidence' | 'config' | 'time'
    description: str = ""


# índices FMT descartados na consolidação (strings temporais)
DROPPED_FMT = {0, 1, 2}   # TIMESTAMP, LMST, LTST

# (fmt_index, name, unit, kind, description) — ordem oficial MODRDR6.FMT
_FMT_SCHEMA = [
    (0,  "TIMESTAMP",                            "SECOND",       "time",        "segundos de missão"),
    (1,  "LMST",                                 "",             "time",        "local mean solar time"),
    (2,  "LTST",                                 "",             "time",        "local true solar time"),
    (3,  "HORIZONTAL_WIND_SPEED",                "METERS/SECOND","measurement", "vento horizontal"),
    (4,  "VERTICAL_WIND_SPEED",                  "METERS/SECOND","measurement", "vento vertical (sensor aposentado)"),
    (5,  "WIND_DIRECTION",                       "DEGREE",       "measurement", "direção do vento"),
    (6,  "WS_CONFIDENCE_LEVEL",                  "",             "confidence",  "qualidade vento"),
    (7,  "BRIGHTNESS_TEMP",                      "KELVIN",       "measurement", "temp. do SOLO (GTS IR)"),
    (8,  "BRIGHTNESS_TEMP_LONG_TERM_UNCERTAINTY","KELVIN",       "uncertainty", "incerteza sistemática GTS"),
    (9,  "BRIGHTNESS_TEMP_SHORT_TERM_UNCERTAINTY","KELVIN",      "uncertainty", "incerteza ruido GTS"),
    (10, "GTS_CONFIDENCE_LEVEL",                 "",             "confidence",  "qualidade temp. solo"),
    (11, "BOOM1_LOCAL_AIR_TEMP",                 "KELVIN",       "measurement", "temp. AR boom 1 (ATS)"),
    (12, "ATS_BOOM1_CONFIDENCE_LEVEL",           "",             "confidence",  "qualidade boom 1"),
    (13, "BOOM2_LOCAL_AIR_TEMP",                 "KELVIN",       "measurement", "temp. AR boom 2 (ATS)"),
    (14, "ATS_BOOM2_CONFIDENCE_LEVEL",           "",             "confidence",  "qualidade boom 2"),
    (15, "AMBIENT_TEMP",                         "KELVIN",       "measurement", "temp. ar combinada (modelo)"),
    (16, "AMBIENT_TEMP_CONFIDENCE_LEVEL",        "",             "confidence",  "qualidade temp. ar"),
    (17, "UV_A",                                 "W/m**2",       "measurement", "irradiância UV banda A"),
    (18, "UV_B",                                 "W/m**2",       "measurement", "UV banda B"),
    (19, "UV_C",                                 "W/m**2",       "measurement", "UV banda C"),
    (20, "UV_ABC",                               "W/m**2",       "measurement", "UV combinado ABC"),
    (21, "UV_D",                                 "W/m**2",       "measurement", "UV banda D"),
    (22, "UV_E",                                 "W/m**2",       "measurement", "UV banda E"),
    (23, "UV_A_UNCERTAINTY",                     "%",            "uncertainty", ""),
    (24, "UV_B_UNCERTAINTY",                     "%",            "uncertainty", ""),
    (25, "UV_C_UNCERTAINTY",                     "%",            "uncertainty", ""),
    (26, "UV_ABC_UNCERTAINTY",                   "%",            "uncertainty", ""),
    (27, "UV_D_UNCERTAINTY",                     "%",            "uncertainty", ""),
    (28, "UV_E_UNCERTAINTY",                     "%",            "uncertainty", ""),
    (29, "UVS_CONFIDENCE_LEVEL",                 "",             "confidence",  "qualidade UV"),
    (30, "LOCAL_RELATIVE_HUMIDITY",              "%",            "measurement", "UR local (HS)"),
    (31, "HS_TEMP",                              "KELVIN",       "measurement", "temp. do sensor de umidade"),
    (32, "LOCAL_RELATIVE_HUMIDITY_UNCERTAINTY",  "%",            "uncertainty", ""),
    (33, "VOLUME_MIXING_RATIO",                  "ppm",          "measurement", "razão de mistura H2O"),
    (34, "VOLUME_MIXING_RATIO_UNCERTAINTY",      "ppm",          "uncertainty", ""),
    (35, "HS_CONFIDENCE_LEVEL",                  "",             "confidence",  "qualidade umidade"),
    (36, "PS_CONFIGURATION",                     "",             "config",      "config. sensor pressão"),
    (37, "PRESSURE",                             "PASCAL",       "measurement", "pressão atmosférica"),
    (38, "PRESSURE_UNCERTAINTY",                 "PASCAL",       "uncertainty", ""),
    (39, "PS_CONFIDENCE_LEVEL",                  "",             "confidence",  "qualidade pressão"),
]

# Constrói o dicionário: c_index = fmt_index - n_drops_antes
def _build() -> List[RemsColumn]:
    cols: List[RemsColumn] = []
    drops_before = 0
    for fmt_i, name, unit, kind, desc in _FMT_SCHEMA:
        if fmt_i in DROPPED_FMT:
            drops_before += 1
            cols.append(RemsColumn(fmt_i, None, name, unit, kind, desc))
        else:
            cols.append(RemsColumn(fmt_i, f"c{fmt_i - drops_before}", name, unit, kind, desc))
    return cols

REMS_COLUMNS: List[RemsColumn] = _build()

# mapas de consulta
C2NAME: Dict[str, str] = {c.parquet_col: c.name for c in REMS_COLUMNS if c.parquet_col}
NAME2C: Dict[str, str] = {v: k for k, v in C2NAME.items()}
UNITS: Dict[str, str] = {c.name: c.unit for c in REMS_COLUMNS if c.parquet_col}

# superfícies "de medida" úteis para a malha (exclui uncertainty/confidence/config)
MEASUREMENT_COLS: List[str] = [c.name for c in REMS_COLUMNS if c.kind == "measurement"]

SENTINEL = -999.0   # ausência de dado nos campos numéricos REMS


def rename_rems_frame(df):
    """Renomeia um parquet consolidado c0..c36 -> nomes físicos oficiais.

    Mantém o índice `sol`. Colunas não mapeadas ficam intactas (defensivo).
    """
    return df.rename(columns=C2NAME)


def clean_sentinels(df, sentinel: float = SENTINEL):
    """Substitui o sentinela -999 por NaN — obrigatório antes de correlacionar,
    senão a ausência de dado vira um pico falso na série."""
    import numpy as np
    out = df.copy()
    for c in out.columns:
        if out[c].dtype.kind in "fc":
            out[c] = out[c].replace(sentinel, np.nan)
    return out


def load_rems_series(path: str, measurements_only: bool = True) -> Dict[str, List[float]]:
    """Carrega o parquet e devolve {nome_físico: [valores limpos]}.

    measurements_only=True (default): só colunas de medida real
    (vento, temps, UV, umidade, pressão) — incertezas/confidences ficam
    disponíveis com False para análise de qualidade.
    """
    import pandas as pd
    df = rename_rems_frame(pd.read_parquet(path))
    if measurements_only:
        keep = [n for n in MEASUREMENT_COLS if n in df.columns]
    else:
        keep = [c.name for c in REMS_COLUMNS if c.parquet_col and c.name in df.columns]
    df = clean_sentinels(df[keep])
    return {name: df[name].tolist() for name in keep}
