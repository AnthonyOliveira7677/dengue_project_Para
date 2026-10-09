import json
from pathlib import Path

import pandas as pd



PASTA_BRONZE = Path(
    "data/bronze/ibge/records"
)

PASTA_SILVER = Path(
    "data/silver/ibge"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/ibge"
)

PASTA_SILVER.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_QUARENTENA.mkdir(
    parents=True,
    exist_ok=True
)

ARQUIVO_SAIDA = (
    PASTA_SILVER
    / "municipios_para_silver.csv"
)

ARQUIVO_QUARENTENA = (
    PASTA_QUARENTENA
    / "municipios_invalidos.csv"
)



arquivos_bronze = sorted(
    PASTA_BRONZE.glob(
        "**/*.jsonl"
    )
)

if not arquivos_bronze:

    raise FileNotFoundError(
        "Nenhum arquivo Bronze do IBGE foi encontrado."
    )


print(
    "Arquivos Bronze encontrados:",
    len(arquivos_bronze)
)


for arquivo in arquivos_bronze:

    print(
        "-",
        arquivo
    )



registros = []

for arquivo in arquivos_bronze:

    with arquivo.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            linha = linha.strip()

            if not linha:
                continue

            registros.append(
                json.loads(
                    linha
                )
            )


df = pd.DataFrame(
    registros
)


print(
    "\nRegistros lidos da Bronze:",
    len(df)
)



colunas_obrigatorias = [
    "id",
    "nome",
    "_ingestion_timestamp",
    "_record_hash",
    "_load_id"
]


faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in df.columns
]


if faltantes:

    raise ValueError(
        "Colunas obrigatórias ausentes: "
        + ", ".join(
            faltantes
        )
    )



df["id"] = pd.to_numeric(
    df["id"],
    errors="coerce"
)

df["nome"] = (
    df["nome"]
    .astype("string")
    .str.strip()
)

df["_ingestion_timestamp"] = pd.to_datetime(
    df["_ingestion_timestamp"],
    errors="coerce",
    utc=True
)



invalidos = df[
    df["id"].isna()
    |
    df["nome"].isna()
    |
    (
        df["nome"].str.len()
        == 0
    )
    |
    df[
        "_ingestion_timestamp"
    ].isna()
].copy()


print(
    "\nRegistros inválidos:",
    len(invalidos)
)


if not invalidos.empty:

    invalidos.to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )



validos = df[
    ~df.index.isin(
        invalidos.index
    )
].copy()



validos = validos.sort_values(
    "_ingestion_timestamp",
    ascending=False
)


antes_deduplicacao = len(
    validos
)


validos = validos.drop_duplicates(
    subset=[
        "id"
    ],
    keep="first"
)


depois_deduplicacao = len(
    validos
)


print(
    "Registros antes da deduplicação:",
    antes_deduplicacao
)

print(
    "Registros depois da deduplicação:",
    depois_deduplicacao
)

print(
    "Duplicatas removidas:",
    (
        antes_deduplicacao
        - depois_deduplicacao
    )
)



validos[
    "codigo_ibge"
] = (
    validos[
        "id"
    ]
    .astype(
        "int64"
    )
    .astype(
        "string"
    )
)

validos[
    "codigo_ibge_6"
] = (
    validos[
        "codigo_ibge"
    ]
    .str[:6]
)


validos[
    "municipio"
] = (
    validos[
        "nome"
    ]
)


validos[
    "codigo_uf"
] = "15"

validos[
    "uf"
] = "PA"



silver = validos[
    [
        "codigo_ibge",
        "codigo_ibge_6",
        "municipio",
        "codigo_uf",
        "uf"
    ]
].copy()



silver = silver.sort_values(
    [
        "codigo_ibge"
    ]
).reset_index(
    drop=True
)



duplicados_chave = (
    silver.duplicated(
        subset=[
            "codigo_ibge"
        ]
    )
    .sum()
)


print(
    "\nDuplicatas na chave codigo_ibge:",
    duplicados_chave
)


if duplicados_chave > 0:

    raise ValueError(
        "Existem códigos IBGE duplicados na Silver."
    )



quantidade_municipios = (
    silver[
        "codigo_ibge"
    ]
    .nunique()
)


print(
    "Municípios únicos:",
    quantidade_municipios
)


if quantidade_municipios != 144:

    raise ValueError(
        "Esperados 144 municípios do Pará, "
        f"mas foram encontrados {quantidade_municipios}."
    )




codigos_invalidos = silver[
    ~silver[
        "codigo_ibge"
    ].str.match(
        r"^\d{7}$"
    )
]


if not codigos_invalidos.empty:

    raise ValueError(
        "Existem códigos IBGE fora do padrão de 7 dígitos."
    )



silver.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)



print(
    "\n========================================"
)

print(
    "RESUMO DA SILVER - IBGE"
)

print(
    "========================================"
)

print(
    "Arquivos Bronze processados:",
    len(arquivos_bronze)
)

print(
    "Registros Bronze lidos:",
    len(df)
)

print(
    "Registros inválidos:",
    len(invalidos)
)

print(
    "Duplicatas removidas:",
    (
        antes_deduplicacao
        - depois_deduplicacao
    )
)

print(
    "Municípios na Silver:",
    len(silver)
)

print(
    "Duplicatas na chave:",
    duplicados_chave
)

print(
    "Arquivo Silver:",
    ARQUIVO_SAIDA
)

if not invalidos.empty:

    print(
        "Quarentena:",
        ARQUIVO_QUARENTENA
    )

else:

    print(
        "Quarentena: nenhum registro inválido"
    )

print(
    "========================================"
)


# ============================================================
# 19. AMOSTRA
# ============================================================

print(
    "\nPrimeiros municípios:"
)

print(
    silver.head(
        10
    ).to_string(
        index=False
    )
)