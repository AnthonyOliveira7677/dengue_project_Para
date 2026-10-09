from pathlib import Path

import pandas as pd


ANO = 2024

ARQUIVO_GOLD = Path(
    f"data/gold/dengue_clima_para_{ANO}_gold.csv"
)

ARQUIVO_SAIDA = Path(
    f"data/gold/ranking_municipios_{ANO}.csv"
)


if not ARQUIVO_GOLD.exists():
    raise FileNotFoundError(
        "Gold principal não encontrada."
    )


df = pd.read_csv(
    ARQUIVO_GOLD,
    dtype={
        "codigo_ibge": "string",
        "municipio": "string",
        "competencia": "string"
    }
)


df["dias_mes"] = (
    pd.PeriodIndex(
        df["competencia"],
        freq="M"
    )
    .days_in_month
)


df["temp_ponderada"] = (
    df["temperatura_media_c"]
    * df["dias_mes"]
)

df["umidade_ponderada"] = (
    df["umidade_media_pct"]
    * df["dias_mes"]
)


ranking = (
    df
    .groupby(
        [
            "codigo_ibge",
            "municipio"
        ],
        as_index=False
    )
    .agg(
        populacao=(
            "populacao",
            "first"
        ),

        casos_provaveis=(
            "casos_provaveis",
            "sum"
        ),

        casos_confirmados=(
            "casos_confirmados",
            "sum"
        ),

        casos_inconclusivos=(
            "casos_inconclusivos",
            "sum"
        ),

        precipitacao_total_ano_mm=(
            "precipitacao_total_mm",
            "sum"
        ),

        soma_temp_ponderada=(
            "temp_ponderada",
            "sum"
        ),

        soma_umidade_ponderada=(
            "umidade_ponderada",
            "sum"
        ),

        dias_ano=(
            "dias_mes",
            "sum"
        )
    )
)


ranking["temperatura_media_ano_c"] = (
    ranking["soma_temp_ponderada"]
    / ranking["dias_ano"]
)


ranking["umidade_media_ano_pct"] = (
    ranking["soma_umidade_ponderada"]
    / ranking["dias_ano"]
)


ranking["incidencia_100mil"] = (
    ranking["casos_provaveis"]
    / ranking["populacao"]
    * 100000
)


ranking["incidencia_confirmada_100mil"] = (
    ranking["casos_confirmados"]
    / ranking["populacao"]
    * 100000
)


ranking = ranking.drop(
    columns=[
        "soma_temp_ponderada",
        "soma_umidade_ponderada",
        "dias_ano"
    ]
)


ranking["incidencia_100mil"] = (
    ranking["incidencia_100mil"]
    .round(3)
)

ranking[
    "incidencia_confirmada_100mil"
] = (
    ranking[
        "incidencia_confirmada_100mil"
    ]
    .round(3)
)

ranking[
    "temperatura_media_ano_c"
] = (
    ranking[
        "temperatura_media_ano_c"
    ]
    .round(3)
)

ranking[
    "umidade_media_ano_pct"
] = (
    ranking[
        "umidade_media_ano_pct"
    ]
    .round(3)
)

ranking[
    "precipitacao_total_ano_mm"
] = (
    ranking[
        "precipitacao_total_ano_mm"
    ]
    .round(3)
)


ranking = ranking.sort_values(
    "incidencia_100mil",
    ascending=False
).reset_index(
    drop=True
)


ranking["posicao"] = (
    ranking.index
    + 1
)


ranking = ranking[
    [
        "posicao",
        "codigo_ibge",
        "municipio",
        "populacao",
        "casos_provaveis",
        "casos_confirmados",
        "casos_inconclusivos",
        "incidencia_100mil",
        "incidencia_confirmada_100mil",
        "temperatura_media_ano_c",
        "umidade_media_ano_pct",
        "precipitacao_total_ano_mm"
    ]
]


duplicatas = ranking.duplicated(
    subset=[
        "codigo_ibge"
    ]
).sum()


if len(ranking) != 144:
    raise ValueError(
        "Ranking deveria possuir 144 municípios."
    )


if duplicatas > 0:
    raise ValueError(
        "Existem municípios duplicados no ranking."
    )


if ranking["populacao"].isna().any():
    raise ValueError(
        "Existem municípios sem população."
    )


ranking.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)


print(
    "\n========================================"
)

print(
    "RANKING MUNICIPAL DE DENGUE - 2024"
)

print(
    "========================================"
)

print(
    "Municípios:",
    len(ranking)
)

print(
    "Duplicatas:",
    duplicatas
)

print(
    "Casos prováveis:",
    ranking[
        "casos_provaveis"
    ].sum()
)

print(
    "\nTop 10 por incidência anual:"
)

print(
    ranking[
        [
            "posicao",
            "municipio",
            "populacao",
            "casos_provaveis",
            "incidencia_100mil",
            "temperatura_media_ano_c",
            "umidade_media_ano_pct",
            "precipitacao_total_ano_mm"
        ]
    ]
    .head(10)
    .to_string(
        index=False
    )
)

print(
    "\nArquivo:",
    ARQUIVO_SAIDA
)

print(
    "========================================"
)