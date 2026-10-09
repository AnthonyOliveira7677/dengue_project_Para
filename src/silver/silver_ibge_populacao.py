import json
from pathlib import Path

import pandas as pd


ANO = 2024

PASTA_BRONZE = Path(
    "data/bronze/ibge_populacao"
)

PASTA_SILVER = Path(
    "data/silver/ibge"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/ibge"
)

ARQUIVO_MUNICIPIOS = Path(
    "data/silver/ibge/municipios_para_silver.csv"
)

ARQUIVO_SAIDA = (
    PASTA_SILVER
    / f"populacao_para_{ANO}_silver.csv"
)

ARQUIVO_QUARENTENA = (
    PASTA_QUARENTENA
    / f"populacao_invalida_{ANO}.csv"
)

PASTA_SILVER.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_QUARENTENA.mkdir(
    parents=True,
    exist_ok=True
)



manifestos = list(
    PASTA_BRONZE.glob(
        f"manifest_{ANO}_*.json"
    )
)

if not manifestos:

    raise FileNotFoundError(
        "Nenhum manifesto Bronze de população foi encontrado."
    )


cargas = []

for arquivo_manifesto in manifestos:

    with arquivo_manifesto.open(
        "r",
        encoding="utf-8"
    ) as arquivo:

        manifesto = json.load(
            arquivo
        )

    cargas.append(
        (
            pd.to_datetime(
                manifesto[
                    "ingestion_timestamp"
                ],
                utc=True
            ),
            manifesto
        )
    )


cargas.sort(
    key=lambda item: item[0],
    reverse=True
)


manifesto = cargas[0][1]

arquivo_bronze = Path(
    manifesto[
        "bronze_file"
    ]
)


if not arquivo_bronze.exists():

    raise FileNotFoundError(
        f"Arquivo Bronze não encontrado: {arquivo_bronze}"
    )


print(
    "Carga Bronze selecionada:"
)

print(
    "Load ID:",
    manifesto["load_id"]
)

print(
    "Arquivo:",
    arquivo_bronze
)



cabecalho = manifesto.get(
    "sidra_header",
    {}
)


if not cabecalho:

    raise ValueError(
        "Cabeçalho SIDRA não encontrado no manifesto."
    )


print(
    "\nCabeçalho SIDRA:"
)

for chave, descricao in cabecalho.items():

    print(
        f"{chave}: {descricao}"
    )



def localizar_campo(
    cabecalho,
    texto_obrigatorio,
    texto_proibido=None
):

    for chave, descricao in cabecalho.items():

        descricao_normalizada = (
            str(
                descricao
            )
            .strip()
            .lower()
        )

        if (
            texto_obrigatorio.lower()
            not in descricao_normalizada
        ):

            continue

        if (
            texto_proibido
            and texto_proibido.lower()
            in descricao_normalizada
        ):

            continue

        return chave

    return None


campo_codigo_municipio = localizar_campo(
    cabecalho,
    "município",
    "nome"
)


# Tenta primeiro identificar explicitamente código.
for chave, descricao in cabecalho.items():

    descricao_lower = str(
        descricao
    ).lower()

    if (
        "município" in descricao_lower
        and "código" in descricao_lower
    ):

        campo_codigo_municipio = chave
        break


campo_nome_municipio = None

for chave, descricao in cabecalho.items():

    descricao_lower = str(
        descricao
    ).lower()

    if (
        "município" in descricao_lower
        and "código" not in descricao_lower
    ):

        campo_nome_municipio = chave
        break


campo_valor = None

for chave, descricao in cabecalho.items():

    if str(
        descricao
    ).strip().lower() == "valor":

        campo_valor = chave
        break


campo_ano = None

for chave, descricao in cabecalho.items():

    descricao_lower = str(
        descricao
    ).lower()

    if (
        descricao_lower == "ano"
        or (
            "ano" in descricao_lower
            and "código" not in descricao_lower
        )
    ):

        campo_ano = chave
        break


print(
    "\nCampos identificados:"
)

print(
    "Código município:",
    campo_codigo_municipio
)

print(
    "Nome município:",
    campo_nome_municipio
)

print(
    "Valor população:",
    campo_valor
)

print(
    "Ano:",
    campo_ano
)


if campo_codigo_municipio is None:

    raise ValueError(
        "Campo de código municipal não identificado."
    )

if campo_nome_municipio is None:

    raise ValueError(
        "Campo de nome municipal não identificado."
    )

if campo_valor is None:

    raise ValueError(
        "Campo de valor não identificado."
    )



registros = []


with arquivo_bronze.open(
    "r",
    encoding="utf-8"
) as arquivo:

    for linha in arquivo:

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
    "\nRegistros Bronze lidos:",
    len(df)
)



silver = pd.DataFrame()


silver[
    "codigo_ibge"
] = (
    df[
        campo_codigo_municipio
    ]
    .astype(
        "string"
    )
    .str.strip()
    .str.replace(
        r"\.0$",
        "",
        regex=True
    )
    .str.zfill(
        7
    )
)


silver[
    "municipio_sidra"
] = (
    df[
        campo_nome_municipio
    ]
    .astype(
        "string"
    )
    .str.strip()
)



silver[
    "populacao"
] = (
    df[
        campo_valor
    ]
    .astype(
        "string"
    )
    .str.strip()
    .str.replace(
        ".",
        "",
        regex=False
    )
    .str.replace(
        ",",
        ".",
        regex=False
    )
)


silver[
    "populacao"
] = pd.to_numeric(
    silver[
        "populacao"
    ],
    errors="coerce"
)


# População deve ser inteira.
silver[
    "populacao"
] = silver[
    "populacao"
].round()



if campo_ano is not None:

    silver[
        "ano"
    ] = pd.to_numeric(
        df[
            campo_ano
        ],
        errors="coerce"
    )

else:

    silver[
        "ano"
    ] = ANO


invalidos = silver[
    silver[
        "codigo_ibge"
    ].isna()
    |
    silver[
        "populacao"
    ].isna()
    |
    (
        silver[
            "populacao"
        ] <= 0
    )
].copy()


print(
    "Registros inválidos:",
    len(invalidos)
)


if not invalidos.empty:

    invalidos.to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )


silver = silver[
    ~silver.index.isin(
        invalidos.index
    )
].copy()



if not ARQUIVO_MUNICIPIOS.exists():

    raise FileNotFoundError(
        "Silver dos municípios não encontrada."
    )


df_municipios = pd.read_csv(
    ARQUIVO_MUNICIPIOS,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string",
        "codigo_uf": "string",
        "uf": "string"
    }
)



resultado = df_municipios.merge(
    silver[
        [
            "codigo_ibge",
            "municipio_sidra",
            "ano",
            "populacao"
        ]
    ],
    on="codigo_ibge",
    how="left",
    validate="one_to_one"
)



sem_populacao = resultado[
    resultado[
        "populacao"
    ].isna()
].copy()


print(
    "Municípios sem população após JOIN:",
    len(sem_populacao)
)


if not sem_populacao.empty:

    sem_populacao.to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )



duplicatas = resultado.duplicated(
    subset=[
        "codigo_ibge"
    ]
).sum()


if duplicatas > 0:

    raise ValueError(
        "Existem códigos IBGE duplicados."
    )


if len(resultado) != 144:

    raise ValueError(
        f"Esperados 144 municípios, "
        f"encontrados {len(resultado)}."
    )


if not sem_populacao.empty:

    raise ValueError(
        f"{len(sem_populacao)} municípios "
        "ficaram sem população."
    )


resultado[
    "populacao"
] = resultado[
    "populacao"
].astype(
    "int64"
)


resultado[
    "ano"
] = resultado[
    "ano"
].fillna(
    ANO
).astype(
    "int64"
)


resultado = resultado[
    [
        "codigo_ibge",
        "codigo_ibge_6",
        "municipio",
        "codigo_uf",
        "uf",
        "ano",
        "populacao"
    ]
]


resultado = resultado.sort_values(
    "codigo_ibge"
).reset_index(
    drop=True
)



resultado.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)



print(
    "\n========================================"
)

print(
    "RESUMO DA SILVER - POPULAÇÃO IBGE"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Registros Bronze:",
    len(df)
)

print(
    "Registros inválidos:",
    len(invalidos)
)

print(
    "Municípios:",
    len(resultado)
)

print(
    "Municípios sem população:",
    len(sem_populacao)
)

print(
    "Duplicatas na chave:",
    duplicatas
)

print(
    "Menor população:",
    resultado[
        "populacao"
    ].min()
)

print(
    "Maior população:",
    resultado[
        "populacao"
    ].max()
)

print(
    "População total representada:",
    resultado[
        "populacao"
    ].sum()
)

print(
    "Arquivo Silver:",
    ARQUIVO_SAIDA
)

print(
    "========================================"
)


print(
    "\nPrimeiros municípios:"
)

print(
    resultado.head(
        10
    ).to_string(
        index=False
    )
)