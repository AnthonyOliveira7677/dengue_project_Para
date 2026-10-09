import json
from pathlib import Path

import pandas as pd


ANO = 2024


ARQUIVO_SINAN = Path(
    f"data/silver/sinan/dengue_para_{ANO}_silver.csv"
)

ARQUIVO_CLIMA = Path(
    f"data/silver/nasa_power/clima_para_{ANO}_silver.csv"
)

ARQUIVO_POPULACAO = Path(
    f"data/silver/ibge/populacao_para_{ANO}_silver.csv"
)


PASTA_GOLD = Path(
    "data/gold"
)

PASTA_GOLD.mkdir(
    parents=True,
    exist_ok=True
)


ARQUIVO_GOLD = (
    PASTA_GOLD
    / f"dengue_clima_para_{ANO}_gold.csv"
)

ARQUIVO_RESUMO = (
    PASTA_GOLD
    / f"resumo_gold_{ANO}.json"
)


for arquivo in [
    ARQUIVO_SINAN,
    ARQUIVO_CLIMA,
    ARQUIVO_POPULACAO
]:

    if not arquivo.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado: {arquivo}"
        )


sinan = pd.read_csv(
    ARQUIVO_SINAN,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string",
        "competencia": "string"
    }
)


clima = pd.read_csv(
    ARQUIVO_CLIMA,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string",
        "competencia": "string"
    }
)


populacao = pd.read_csv(
    ARQUIVO_POPULACAO,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string"
    }
)


print(
    "SINAN:",
    len(sinan),
    "linhas"
)

print(
    "NASA POWER:",
    len(clima),
    "linhas"
)

print(
    "População:",
    len(populacao),
    "linhas"
)


if len(sinan) != 1728:

    raise ValueError(
        f"SINAN deveria possuir 1728 linhas. "
        f"Encontrado: {len(sinan)}"
    )


if len(clima) != 1728:

    raise ValueError(
        f"NASA POWER deveria possuir 1728 linhas. "
        f"Encontrado: {len(clima)}"
    )


if len(populacao) != 144:

    raise ValueError(
        f"População deveria possuir 144 linhas. "
        f"Encontrado: {len(populacao)}"
    )


duplicatas_sinan = sinan.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


duplicatas_clima = clima.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


duplicatas_populacao = populacao.duplicated(
    subset=[
        "codigo_ibge"
    ]
).sum()


if duplicatas_sinan > 0:

    raise ValueError(
        "SINAN possui duplicatas na chave."
    )


if duplicatas_clima > 0:

    raise ValueError(
        "Clima possui duplicatas na chave."
    )


if duplicatas_populacao > 0:

    raise ValueError(
        "População possui códigos IBGE duplicados."
    )


clima_selecionado = clima[
    [
        "codigo_ibge",
        "competencia",
        "temperatura_media_c",
        "umidade_media_pct",
        "precipitacao_total_mm",
        "cobertura_temperatura_pct",
        "cobertura_umidade_pct",
        "cobertura_precipitacao_pct"
    ]
].copy()


gold = sinan.merge(
    clima_selecionado,
    on=[
        "codigo_ibge",
        "competencia"
    ],
    how="left",
    validate="one_to_one",
    indicator="_match_clima"
)


match_clima = (
    gold["_match_clima"]
    == "both"
).sum()


sem_match_clima = (
    gold["_match_clima"]
    != "both"
).sum()


print(
    "\nMatch SINAN x clima:",
    match_clima,
    "/",
    len(gold)
)

print(
    "Sem match climático:",
    sem_match_clima
)


gold = gold.drop(
    columns=[
        "_match_clima"
    ]
)


populacao_selecionada = populacao[
    [
        "codigo_ibge",
        "populacao"
    ]
].copy()


gold = gold.merge(
    populacao_selecionada,
    on="codigo_ibge",
    how="left",
    validate="many_to_one",
    indicator="_match_populacao"
)


match_populacao = (
    gold["_match_populacao"]
    == "both"
).sum()


sem_match_populacao = (
    gold["_match_populacao"]
    != "both"
).sum()


print(
    "Match com população:",
    match_populacao,
    "/",
    len(gold)
)

print(
    "Sem população:",
    sem_match_populacao
)


gold = gold.drop(
    columns=[
        "_match_populacao"
    ]
)


if gold["populacao"].isna().any():

    raise ValueError(
        "Existem registros sem população."
    )


if (
    gold["temperatura_media_c"].isna().any()
    or gold["umidade_media_pct"].isna().any()
    or gold["precipitacao_total_mm"].isna().any()
):

    raise ValueError(
        "Existem registros sem dados climáticos."
    )


gold["incidencia_100mil"] = (
    gold["casos_provaveis"]
    /
    gold["populacao"]
    *
    100000
)


gold["incidencia_confirmada_100mil"] = (
    gold["casos_confirmados"]
    /
    gold["populacao"]
    *
    100000
)


gold["taxa_confirmacao_pct"] = 0.0


mascara_casos = (
    gold["casos_provaveis"]
    > 0
)


gold.loc[
    mascara_casos,
    "taxa_confirmacao_pct"
] = (
    gold.loc[
        mascara_casos,
        "casos_confirmados"
    ]
    /
    gold.loc[
        mascara_casos,
        "casos_provaveis"
    ]
    *
    100
)


gold["ano"] = (
    gold["competencia"]
    .str[:4]
    .astype("int64")
)


gold["mes"] = (
    gold["competencia"]
    .str[5:7]
    .astype("int64")
)


gold = gold.sort_values(
    [
        "codigo_ibge",
        "competencia"
    ]
).reset_index(
    drop=True
)


duplicatas_gold = gold.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


if duplicatas_gold > 0:

    raise ValueError(
        "Gold possui duplicatas na chave."
    )


if len(gold) != 1728:

    raise ValueError(
        f"Gold deveria possuir 1728 linhas. "
        f"Encontrado: {len(gold)}"
    )


if (
    gold["codigo_ibge"]
    .nunique()
    != 144
):

    raise ValueError(
        "Gold não possui os 144 municípios."
    )


if (
    gold["competencia"]
    .nunique()
    != 12
):

    raise ValueError(
        "Gold não possui as 12 competências."
    )


for coluna in [
    "incidencia_100mil",
    "incidencia_confirmada_100mil",
    "taxa_confirmacao_pct",
    "temperatura_media_c",
    "umidade_media_pct",
    "precipitacao_total_mm"
]:

    gold[coluna] = (
        gold[coluna]
        .round(3)
    )


colunas_finais = [
    "codigo_ibge",
    "codigo_ibge_6",
    "municipio",
    "codigo_uf",
    "uf",
    "ano",
    "mes",
    "competencia",
    "populacao",

    "notificacoes",
    "casos_provaveis",
    "casos_confirmados",
    "casos_inconclusivos",
    "dengue",
    "dengue_sinais_alarme",
    "dengue_grave",
    "casos_descartados",
    "classificacoes_ausentes",

    "incidencia_100mil",
    "incidencia_confirmada_100mil",
    "taxa_confirmacao_pct",

    "temperatura_media_c",
    "umidade_media_pct",
    "precipitacao_total_mm",

    "cobertura_temperatura_pct",
    "cobertura_umidade_pct",
    "cobertura_precipitacao_pct"
]


gold = gold[
    colunas_finais
]


gold.to_csv(
    ARQUIVO_GOLD,
    index=False,
    encoding="utf-8"
)


resumo = {

    "ano": ANO,

    "granularidade": (
        "municipio_mes"
    ),

    "chave": [
        "codigo_ibge",
        "competencia"
    ],

    "linhas": int(
        len(gold)
    ),

    "municipios": int(
        gold[
            "codigo_ibge"
        ].nunique()
    ),

    "competencias": int(
        gold[
            "competencia"
        ].nunique()
    ),

    "duplicatas_chave": int(
        duplicatas_gold
    ),

    "match_clima": int(
        match_clima
    ),

    "sem_match_clima": int(
        sem_match_clima
    ),

    "match_populacao": int(
        match_populacao
    ),

    "sem_match_populacao": int(
        sem_match_populacao
    ),

    "casos_provaveis_total": int(
        gold[
            "casos_provaveis"
        ].sum()
    ),

    "casos_confirmados_total": int(
        gold[
            "casos_confirmados"
        ].sum()
    ),

    "populacao_total_estado": int(
        populacao[
            "populacao"
        ].sum()
    ),

    "incidencia_maxima_mensal_100mil": float(
        gold[
            "incidencia_100mil"
        ].max()
    )
}


with ARQUIVO_RESUMO.open(
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        resumo,
        arquivo,
        ensure_ascii=False,
        indent=4
    )


print(
    "\n========================================"
)

print(
    "RESUMO DA GOLD"
)

print(
    "========================================"
)

print(
    "Linhas:",
    len(gold)
)

print(
    "Municípios:",
    gold[
        "codigo_ibge"
    ].nunique()
)

print(
    "Competências:",
    gold[
        "competencia"
    ].nunique()
)

print(
    "Duplicatas na chave:",
    duplicatas_gold
)

print(
    "Match climático:",
    match_clima,
    "/",
    len(gold)
)

print(
    "Match população:",
    match_populacao,
    "/",
    len(gold)
)

print(
    "Casos prováveis:",
    gold[
        "casos_provaveis"
    ].sum()
)

print(
    "Casos confirmados:",
    gold[
        "casos_confirmados"
    ].sum()
)

print(
    "Maior incidência mensal por 100 mil:",
    round(
        gold[
            "incidencia_100mil"
        ].max(),
        2
    )
)

print(
    "Arquivo Gold:",
    ARQUIVO_GOLD
)

print(
    "Resumo:",
    ARQUIVO_RESUMO
)

print(
    "========================================"
)


print(
    "\nTop 10 município/mês por incidência:"
)


top10 = (
    gold
    .sort_values(
        "incidencia_100mil",
        ascending=False
    )
    [
        [
            "municipio",
            "competencia",
            "casos_provaveis",
            "populacao",
            "incidencia_100mil",
            "temperatura_media_c",
            "umidade_media_pct",
            "precipitacao_total_mm"
        ]
    ]
    .head(
        10
    )
)


print(
    top10.to_string(
        index=False
    )
)