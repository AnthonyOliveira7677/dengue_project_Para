from pathlib import Path

import pandas as pd


ANO = 2024

ARQUIVO_GOLD = Path(
    f"data/gold/dengue_clima_para_{ANO}_gold.csv"
)

ARQUIVO_SAIDA = Path(
    f"data/gold/dengue_clima_lags_{ANO}.csv"
)

ARQUIVO_CORRELACOES = Path(
    f"data/gold/correlacoes_clima_dengue_{ANO}.csv"
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


df = df.sort_values(
    [
        "codigo_ibge",
        "competencia"
    ]
).reset_index(
    drop=True
)


variaveis_climaticas = [
    "temperatura_media_c",
    "umidade_media_pct",
    "precipitacao_total_mm"
]


for variavel in variaveis_climaticas:

    df[
        f"{variavel}_lag1"
    ] = (
        df
        .groupby(
            "codigo_ibge"
        )[variavel]
        .shift(1)
    )


    df[
        f"{variavel}_lag2"
    ] = (
        df
        .groupby(
            "codigo_ibge"
        )[variavel]
        .shift(2)
    )


df[
    "incidencia_lag1"
] = (
    df
    .groupby(
        "codigo_ibge"
    )[
        "incidencia_100mil"
    ]
    .shift(1)
)


df[
    "casos_provaveis_lag1"
] = (
    df
    .groupby(
        "codigo_ibge"
    )[
        "casos_provaveis"
    ]
    .shift(1)
)


duplicatas = df.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


if duplicatas > 0:

    raise ValueError(
        "Existem duplicatas na chave."
    )


if len(df) != 1728:

    raise ValueError(
        f"Esperadas 1728 linhas, encontradas {len(df)}."
    )


df.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)


variaveis_correlacao = [
    "temperatura_media_c",
    "temperatura_media_c_lag1",
    "temperatura_media_c_lag2",

    "umidade_media_pct",
    "umidade_media_pct_lag1",
    "umidade_media_pct_lag2",

    "precipitacao_total_mm",
    "precipitacao_total_mm_lag1",
    "precipitacao_total_mm_lag2",

    "incidencia_lag1"
]


resultados = []


for variavel in variaveis_correlacao:

    dados_validos = df[
        [
            variavel,
            "incidencia_100mil"
        ]
    ].dropna()


    pearson = (
        dados_validos[
            variavel
        ]
        .corr(
            dados_validos[
                "incidencia_100mil"
            ],
            method="pearson"
        )
    )


    spearman = (
        dados_validos[
            variavel
        ]
        .corr(
            dados_validos[
                "incidencia_100mil"
            ],
            method="spearman"
        )
    )


    resultados.append(
        {
            "variavel": variavel,

            "observacoes": len(
                dados_validos
            ),

            "correlacao_pearson": round(
                pearson,
                4
            ),

            "correlacao_spearman": round(
                spearman,
                4
            )
        }
    )


correlacoes = pd.DataFrame(
    resultados
)


correlacoes[
    "abs_spearman"
] = (
    correlacoes[
        "correlacao_spearman"
    ]
    .abs()
)


correlacoes = (
    correlacoes
    .sort_values(
        "abs_spearman",
        ascending=False
    )
    .drop(
        columns=[
            "abs_spearman"
        ]
    )
    .reset_index(
        drop=True
    )
)


correlacoes.to_csv(
    ARQUIVO_CORRELACOES,
    index=False,
    encoding="utf-8"
)


print(
    "\n========================================"
)

print(
    "ANÁLISE CLIMÁTICA x DENGUE - 2024"
)

print(
    "========================================"
)

print(
    "Linhas:",
    len(df)
)

print(
    "Municípios:",
    df[
        "codigo_ibge"
    ].nunique()
)

print(
    "Duplicatas:",
    duplicatas
)

print(
    "\nCorrelações com incidência de dengue:"
)

print(
    correlacoes.to_string(
        index=False
    )
)

print(
    "\nArquivo com lags:",
    ARQUIVO_SAIDA
)

print(
    "Arquivo de correlações:",
    ARQUIVO_CORRELACOES
)

print(
    "========================================"
)