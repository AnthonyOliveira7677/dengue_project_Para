import math
from pathlib import Path

import pandas as pd


ANO = 2024

ARQUIVO_ENTRADA = Path(
    f"data/gold/dengue_clima_lags_{ANO}.csv"
)

PASTA_ML = Path(
    "data/ml"
)

PASTA_ML.mkdir(
    parents=True,
    exist_ok=True
)

ARQUIVO_SAIDA = (
    PASTA_ML
    / f"dataset_ml_{ANO}.csv"
)


if not ARQUIVO_ENTRADA.exists():
    raise FileNotFoundError(
        "Gold com lags não encontrada. "
        "Execute primeiro gold_analise_climatica.py."
    )


df = pd.read_csv(
    ARQUIVO_ENTRADA,
    dtype={
        "codigo_ibge": "string",
        "municipio": "string",
        "competencia": "string"
    }
)


print(
    "Linhas recebidas:",
    len(df)
)


df = df.sort_values(
    [
        "codigo_ibge",
        "competencia"
    ]
).reset_index(
    drop=True
)


df["mes"] = (
    df["competencia"]
    .str[5:7]
    .astype("int64")
)


df["mes_sin"] = df["mes"].apply(
    lambda mes: math.sin(
        2 * math.pi * mes / 12
    )
)


df["mes_cos"] = df["mes"].apply(
    lambda mes: math.cos(
        2 * math.pi * mes / 12
    )
)


df["log_populacao"] = (
    df["populacao"]
    .apply(
        lambda x: math.log1p(x)
    )
)


FEATURES = [
    "incidencia_lag1",

    "precipitacao_total_mm_lag1",
    "precipitacao_total_mm_lag2",

    "temperatura_media_c_lag1",
    "temperatura_media_c_lag2",

    "umidade_media_pct_lag1",
    "umidade_media_pct_lag2",

    "log_populacao",

    "mes_sin",
    "mes_cos"
]


TARGET = "incidencia_100mil"


colunas_identificacao = [
    "codigo_ibge",
    "municipio",
    "competencia",
    "mes"
]


colunas_finais = (
    colunas_identificacao
    + FEATURES
    + [
        TARGET
    ]
)


ml = df[
    colunas_finais
].copy()


antes_drop = len(
    ml
)


ml = ml.dropna(
    subset=(
        FEATURES
        + [
            TARGET
        ]
    )
).copy()


depois_drop = len(
    ml
)


print(
    "Linhas removidas por lags:",
    antes_drop - depois_drop
)


duplicatas = ml.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


if duplicatas > 0:
    raise ValueError(
        "Existem duplicatas no dataset de ML."
    )


nulos = ml[
    FEATURES
    + [
        TARGET
    ]
].isna().sum().sum()


if nulos > 0:
    raise ValueError(
        "Existem valores nulos nas features ou target."
    )


ml["split"] = "train"


ml.loc[
    ml["competencia"].isin(
        [
            "2024-09",
            "2024-10"
        ]
    ),
    "split"
] = "validation"


ml.loc[
    ml["competencia"].isin(
        [
            "2024-11",
            "2024-12"
        ]
    ),
    "split"
] = "test"


quantidade_train = (
    ml["split"]
    == "train"
).sum()


quantidade_validation = (
    ml["split"]
    == "validation"
).sum()


quantidade_test = (
    ml["split"]
    == "test"
).sum()


ml.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)


print(
    "\n========================================"
)

print(
    "DATASET DE MACHINE LEARNING"
)

print(
    "========================================"
)

print(
    "Linhas finais:",
    len(ml)
)

print(
    "Municípios:",
    ml[
        "codigo_ibge"
    ].nunique()
)

print(
    "Competências disponíveis:",
    ml[
        "competencia"
    ].nunique()
)

print(
    "Duplicatas:",
    duplicatas
)

print(
    "Valores nulos:",
    nulos
)


print(
    "\nDivisão temporal:"
)

print(
    "Treino:",
    quantidade_train
)

print(
    "Validação:",
    quantidade_validation
)

print(
    "Teste:",
    quantidade_test
)


print(
    "\nFeatures:"
)

for feature in FEATURES:
    print(
        "-",
        feature
    )


print(
    "\nTarget:",
    TARGET
)

print(
    "\nArquivo:",
    ARQUIVO_SAIDA
)

print(
    "========================================"
)