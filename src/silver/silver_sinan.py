import json
from pathlib import Path

import pandas as pd



ANO = 2024

PASTA_BRONZE = Path(
    "data/bronze/sinan"
)

PASTA_SILVER = Path(
    "data/silver/sinan"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/sinan"
)

ARQUIVO_IBGE = Path(
    "data/silver/ibge/municipios_para_silver.csv"
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
    / f"dengue_para_{ANO}_silver.csv"
)

ARQUIVO_ORFAOS = (
    PASTA_QUARENTENA
    / f"municipios_sinan_sem_ibge_{ANO}.csv"
)

ARQUIVO_CHAVE_INVALIDA = (
    PASTA_QUARENTENA
    / f"registros_sem_municipio_ou_data_{ANO}.csv"
)

ARQUIVO_CLASSIFICACAO_DESCONHECIDA = (
    PASTA_QUARENTENA
    / f"classificacoes_desconhecidas_{ANO}.csv"
)




manifestos = list(
    PASTA_BRONZE.glob(
        f"manifest_{ANO}_*.json"
    )
)

if not manifestos:
    raise FileNotFoundError(
        "Nenhum manifesto Bronze do SINAN foi encontrado."
    )


cargas = []

for arquivo_manifesto in manifestos:

    with arquivo_manifesto.open(
        "r",
        encoding="utf-8"
    ) as f:

        manifesto_lido = json.load(f)

    cargas.append(
        (
            pd.to_datetime(
                manifesto_lido["ingestion_timestamp"],
                utc=True
            ),
            manifesto_lido
        )
    )


cargas.sort(
    key=lambda item: item[0],
    reverse=True
)

manifesto = cargas[0][1]

arquivo_bronze = Path(
    manifesto["bronze_file"]
)


if not arquivo_bronze.exists():
    raise FileNotFoundError(
        f"Arquivo Bronze não encontrado: {arquivo_bronze}"
    )


print("Carga Bronze selecionada:")
print("Load ID:", manifesto["load_id"])
print("Data:", manifesto["ingestion_timestamp"])
print("Arquivo:", arquivo_bronze)



if not ARQUIVO_IBGE.exists():
    raise FileNotFoundError(
        "A Silver do IBGE ainda não existe. "
        "Execute primeiro src/silver/silver_ibge.py"
    )


df_ibge = pd.read_csv(
    ARQUIVO_IBGE,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string",
        "codigo_uf": "string",
        "uf": "string"
    }
)


print(
    "\nMunicípios na Silver do IBGE:",
    len(df_ibge)
)



colunas = [
    "SG_UF",
    "ID_MN_RESI",
    "DT_SIN_PRI",
    "CLASSI_FIN",
    "_record_hash",
    "_load_id"
]



CHUNKSIZE = 200_000

agregacoes = []

total_lido = 0
total_para = 0
total_ano = 0

quantidade_quarentena = 0
quantidade_classificacao_desconhecida = 0

primeiro_bloco_quarentena = True
primeiro_bloco_classificacao = True



print(
    "\nProcessando Bronze do SINAN em blocos..."
)


for numero_bloco, chunk in enumerate(
    pd.read_csv(
        arquivo_bronze,
        compression="gzip",
        usecols=colunas,
        dtype="string",
        chunksize=CHUNKSIZE,
        low_memory=False
    ),
    start=1
):

    total_lido += len(chunk)


    

    chunk["SG_UF"] = (
        chunk["SG_UF"]
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True
        )
        .str.zfill(2)
    )


    

    chunk["ID_MN_RESI"] = (
        chunk["ID_MN_RESI"]
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True
        )
    )

    chunk.loc[
        chunk["ID_MN_RESI"].notna(),
        "ID_MN_RESI"
    ] = (
        chunk.loc[
            chunk["ID_MN_RESI"].notna(),
            "ID_MN_RESI"
        ]
        .str.zfill(6)
    )




    chunk["CLASSI_FIN"] = pd.to_numeric(
        chunk["CLASSI_FIN"],
        errors="coerce"
    )




    chunk["DT_SIN_PRI"] = pd.to_datetime(
        chunk["DT_SIN_PRI"],
        errors="coerce",
        format="%Y-%m-%d"
    )



    chunk = chunk[
        chunk["SG_UF"] == "15"
    ].copy()

    total_para += len(chunk)



    invalidos = chunk[
        chunk["ID_MN_RESI"].isna()
        |
        chunk["DT_SIN_PRI"].isna()
    ].copy()


    if not invalidos.empty:

        quantidade_quarentena += len(
            invalidos
        )

        invalidos[
            "_motivo_quarentena"
        ] = (
            "municipio_residencia_ou_"
            "data_inicio_sintomas_invalida"
        )

        invalidos.to_csv(
            ARQUIVO_CHAVE_INVALIDA,
            mode=(
                "w"
                if primeiro_bloco_quarentena
                else "a"
            ),
            header=primeiro_bloco_quarentena,
            index=False,
            encoding="utf-8"
        )

        primeiro_bloco_quarentena = False


    chunk = chunk.dropna(
        subset=[
            "ID_MN_RESI",
            "DT_SIN_PRI"
        ]
    ).copy()



    chunk = chunk[
        chunk[
            "DT_SIN_PRI"
        ].dt.year == ANO
    ].copy()

    total_ano += len(chunk)


    if chunk.empty:
        continue



    chunk["competencia"] = (
        chunk[
            "DT_SIN_PRI"
        ]
        .dt.to_period("M")
        .astype("string")
    )



    classificacao = chunk[
        "CLASSI_FIN"
    ]



    chunk["caso_inconclusivo"] = (
        classificacao
        .eq(8)
        .fillna(False)
    ).astype(
        "int8"
    )




    chunk["dengue"] = (
        classificacao
        .eq(10)
        .fillna(False)
    ).astype(
        "int8"
    )




    chunk["dengue_sinais_alarme"] = (
        classificacao
        .eq(11)
        .fillna(False)
    ).astype(
        "int8"
    )



    chunk["dengue_grave"] = (
        classificacao
        .eq(12)
        .fillna(False)
    ).astype(
        "int8"
    )


    chunk["chikungunya"] = (
        classificacao
        .eq(13)
        .fillna(False)
    ).astype(
        "int8"
    )



    chunk["caso_descartado"] = (
        classificacao
        .eq(5)
        .fillna(False)
    ).astype(
        "int8"
    )



    chunk["classificacao_ausente"] = (
        classificacao.isna()
    ).astype(
        "int8"
    )




    codigos_conhecidos = [
        5,
        8,
        10,
        11,
        12,
        13
    ]

    chunk[
        "outra_classificacao"
    ] = (
        classificacao.notna()
        &
        ~classificacao.isin(
            codigos_conhecidos
        )
    ).astype(
        "int8"
    )


    classificacoes_desconhecidas = chunk[
        chunk[
            "outra_classificacao"
        ] == 1
    ].copy()


    if not classificacoes_desconhecidas.empty:

        quantidade_classificacao_desconhecida += len(
            classificacoes_desconhecidas
        )

        classificacoes_desconhecidas[
            "_motivo_quarentena"
        ] = (
            "codigo_CLASSI_FIN_nao_reconhecido"
        )

        classificacoes_desconhecidas.to_csv(
            ARQUIVO_CLASSIFICACAO_DESCONHECIDA,
            mode=(
                "w"
                if primeiro_bloco_classificacao
                else "a"
            ),
            header=primeiro_bloco_classificacao,
            index=False,
            encoding="utf-8"
        )

        primeiro_bloco_classificacao = False




    chunk["caso_confirmado"] = (
        classificacao.isin(
            [
                10,
                11,
                12
            ]
        )
    ).astype(
        "int8"
    )



    chunk["caso_provavel"] = (
        classificacao.isin(
            [
                8,
                10,
                11,
                12
            ]
        )
        |
        classificacao.isna()
    ).astype(
        "int8"
    )



    agregado = (
        chunk
        .groupby(
            [
                "ID_MN_RESI",
                "competencia"
            ],
            as_index=False
        )
        .agg(
            notificacoes=(
                "_record_hash",
                "size"
            ),

            casos_provaveis=(
                "caso_provavel",
                "sum"
            ),

            casos_confirmados=(
                "caso_confirmado",
                "sum"
            ),

            casos_inconclusivos=(
                "caso_inconclusivo",
                "sum"
            ),

            dengue=(
                "dengue",
                "sum"
            ),

            dengue_sinais_alarme=(
                "dengue_sinais_alarme",
                "sum"
            ),

            dengue_grave=(
                "dengue_grave",
                "sum"
            ),

            casos_descartados=(
                "caso_descartado",
                "sum"
            ),

            chikungunya=(
                "chikungunya",
                "sum"
            ),

            outras_classificacoes=(
                "outra_classificacao",
                "sum"
            ),

            classificacoes_ausentes=(
                "classificacao_ausente",
                "sum"
            )
        )
    )


    agregacoes.append(
        agregado
    )


    print(
        f"Bloco {numero_bloco} processado "
        f"| total lido: {total_lido:,}"
    )




if not agregacoes:

    raise ValueError(
        "Nenhum registro válido foi encontrado."
    )


sinan_mensal = pd.concat(
    agregacoes,
    ignore_index=True
)


colunas_soma = [
    "notificacoes",
    "casos_provaveis",
    "casos_confirmados",
    "casos_inconclusivos",
    "dengue",
    "dengue_sinais_alarme",
    "dengue_grave",
    "casos_descartados",
    "chikungunya",
    "outras_classificacoes",
    "classificacoes_ausentes"
]


sinan_mensal = (
    sinan_mensal
    .groupby(
        [
            "ID_MN_RESI",
            "competencia"
        ],
        as_index=False
    )[colunas_soma]
    .sum()
)



codigos_ibge = set(
    df_ibge[
        "codigo_ibge_6"
    ]
)


orfaos = sinan_mensal[
    ~sinan_mensal[
        "ID_MN_RESI"
    ].isin(
        codigos_ibge
    )
].copy()


if not orfaos.empty:

    orfaos.to_csv(
        ARQUIVO_ORFAOS,
        index=False,
        encoding="utf-8"
    )


print(
    "\nÓrfãos no JOIN com IBGE:",
    len(orfaos)
)


sinan_mensal = sinan_mensal[
    sinan_mensal[
        "ID_MN_RESI"
    ].isin(
        codigos_ibge
    )
].copy()



competencias = pd.DataFrame(
    {
        "competencia": pd.period_range(
            start=f"{ANO}-01",
            end=f"{ANO}-12",
            freq="M"
        ).astype(
            str
        )
    }
)




municipios = df_ibge[
    [
        "codigo_ibge",
        "codigo_ibge_6",
        "municipio",
        "codigo_uf",
        "uf"
    ]
].copy()


municipios["_join"] = 1
competencias["_join"] = 1


painel = (
    municipios
    .merge(
        competencias,
        on="_join"
    )
    .drop(
        columns="_join"
    )
)



silver = painel.merge(
    sinan_mensal,
    left_on=[
        "codigo_ibge_6",
        "competencia"
    ],
    right_on=[
        "ID_MN_RESI",
        "competencia"
    ],
    how="left"
)


silver = silver.drop(
    columns=[
        "ID_MN_RESI"
    ]
)




for coluna in colunas_soma:

    silver[coluna] = (
        silver[coluna]
        .fillna(0)
        .astype("int64")
    )



silver = silver.sort_values(
    [
        "codigo_ibge",
        "competencia"
    ]
).reset_index(
    drop=True
)




duplicatas = silver.duplicated(
    subset=[
        "codigo_ibge",
        "competencia"
    ]
).sum()


if duplicatas > 0:

    raise ValueError(
        "Existem duplicatas na chave "
        "codigo_ibge + competencia."
    )



linhas_esperadas = (
    144
    * 12
)


if len(silver) != linhas_esperadas:

    raise ValueError(
        f"Esperadas {linhas_esperadas} linhas, "
        f"mas foram encontradas {len(silver)}."
    )



municipios_silver = (
    silver[
        "codigo_ibge"
    ]
    .nunique()
)


if municipios_silver != 144:

    raise ValueError(
        f"Esperados 144 municípios, "
        f"mas encontrados {municipios_silver}."
    )




competencias_silver = (
    silver[
        "competencia"
    ]
    .nunique()
)


if competencias_silver != 12:

    raise ValueError(
        f"Esperadas 12 competências, "
        f"mas encontradas {competencias_silver}."
    )




silver.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)




total_confirmado_calculado = (
    silver["dengue"].sum()
    +
    silver[
        "dengue_sinais_alarme"
    ].sum()
    +
    silver[
        "dengue_grave"
    ].sum()
)


if (
    total_confirmado_calculado
    != silver[
        "casos_confirmados"
    ].sum()
):

    raise ValueError(
        "Inconsistência no total de casos confirmados."
    )



print(
    "\n========================================"
)

print(
    "RESUMO DA SILVER - SINAN"
)

print(
    "========================================"
)

print(
    "Carga Bronze utilizada:",
    manifesto["load_id"]
)

print(
    "Registros Bronze lidos:",
    total_lido
)

print(
    "Registros de residentes do Pará:",
    total_para
)

print(
    f"Registros com sintomas em {ANO}:",
    total_ano
)

print(
    "Municípios:",
    municipios_silver
)

print(
    "Competências:",
    competencias_silver
)

print(
    "Linhas da Silver:",
    len(silver)
)

print(
    "\n--- Classificação epidemiológica ---"
)

print(
    "Notificações:",
    silver[
        "notificacoes"
    ].sum()
)

print(
    "Casos prováveis:",
    silver[
        "casos_provaveis"
    ].sum()
)

print(
    "Casos confirmados:",
    silver[
        "casos_confirmados"
    ].sum()
)

print(
    "  Dengue:",
    silver[
        "dengue"
    ].sum()
)

print(
    "  Dengue com sinais de alarme:",
    silver[
        "dengue_sinais_alarme"
    ].sum()
)

print(
    "  Dengue grave:",
    silver[
        "dengue_grave"
    ].sum()
)

print(
    "Casos inconclusivos:",
    silver[
        "casos_inconclusivos"
    ].sum()
)

print(
    "Casos descartados:",
    silver[
        "casos_descartados"
    ].sum()
)

print(
    "Chikungunya:",
    silver[
        "chikungunya"
    ].sum()
)

print(
    "Classificações ausentes:",
    silver[
        "classificacoes_ausentes"
    ].sum()
)

print(
    "Outras classificações:",
    silver[
        "outras_classificacoes"
    ].sum()
)

print(
    "\n--- Qualidade ---"
)

print(
    "Registros sem município/data:",
    quantidade_quarentena
)

print(
    "Classificações desconhecidas:",
    quantidade_classificacao_desconhecida
)

print(
    "Órfãos no JOIN com IBGE:",
    len(orfaos)
)

print(
    "Duplicatas na chave:",
    duplicatas
)

print(
    "\nArquivo Silver:",
    ARQUIVO_SAIDA
)

print(
    "========================================"
)