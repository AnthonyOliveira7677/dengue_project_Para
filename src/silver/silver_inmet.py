import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ANO = 2024

PASTA_BRONZE = Path(
    "data/bronze/inmet"
)

PASTA_SILVER = Path(
    "data/silver/inmet"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/inmet"
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
    / f"inmet_para_{ANO}_estacao_mensal.csv"
)

ARQUIVO_SEM_MATCH = (
    PASTA_QUARENTENA
    / f"estacoes_inmet_sem_match_ibge_{ANO}.csv"
)



def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor)

    valor = unicodedata.normalize(
        "NFKD",
        valor
    )

    valor = "".join(
        caractere
        for caractere in valor
        if not unicodedata.combining(
            caractere
        )
    )

    valor = valor.upper()

    valor = re.sub(
        r"[^A-Z0-9]+",
        " ",
        valor
    )

    return " ".join(
        valor.split()
    )


def converter_numero(valor):

    if pd.isna(valor):
        return None

    valor = str(valor).strip()

    if valor == "":
        return None

    valor = valor.replace(
        ",",
        "."
    )

    try:
        numero = float(valor)

    except ValueError:
        return None

    # Sentinelas comuns de ausência
    if numero in [
        9999,
        9999.0,
        -9999,
        -9999.0
    ]:
        return None

    return numero


def parsear_metadados(
    linhas_metadados
):

    resultado = {}

    for linha in linhas_metadados:

        if ":" not in linha:
            continue

        chave, valor = linha.split(
            ":",
            1
        )

        chave = normalizar_texto(
            chave
        )

        valor = (
            valor
            .strip()
            .rstrip(";")
            .strip()
        )

        resultado[chave] = valor

    return resultado


def encontrar_coluna(
    colunas,
    obrigatorios,
    proibidos=None
):

    if proibidos is None:
        proibidos = []

    for coluna in colunas:

        normalizada = normalizar_texto(
            coluna
        )

        if not all(
            termo in normalizada
            for termo in obrigatorios
        ):
            continue

        if any(
            termo in normalizada
            for termo in proibidos
        ):
            continue

        return coluna

    return None



manifestos = list(
    PASTA_BRONZE.glob(
        f"manifest_{ANO}_*.json"
    )
)

if not manifestos:

    raise FileNotFoundError(
        "Nenhum manifesto Bronze do INMET foi encontrado."
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
                manifesto_lido[
                    "ingestion_timestamp"
                ],
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


print(
    "Carga Bronze selecionada:"
)

print(
    "Load ID:",
    manifesto["load_id"]
)

print(
    "Data:",
    manifesto["ingestion_timestamp"]
)

print(
    "Arquivos processados na Bronze:",
    manifesto["files_processed"]
)



if not ARQUIVO_IBGE.exists():

    raise FileNotFoundError(
        "Silver do IBGE não encontrada."
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


df_ibge[
    "municipio_normalizado"
] = (
    df_ibge[
        "municipio"
    ]
    .apply(
        normalizar_texto
    )
)



estacoes_para = []


for arquivo_info in manifesto["files"]:

    metadados = parsear_metadados(
        arquivo_info[
            "station_metadata"
        ]
    )

    uf = (
        metadados.get(
            "UF",
            ""
        )
        .strip()
        .upper()
    )


    # Também usamos o nome do arquivo
    # como checagem complementar.

    source_file = arquivo_info[
        "source_file"
    ]


    arquivo_indica_pa = (
        "_PA_"
        in source_file.upper()
    )


    if (
        uf == "PA"
        or arquivo_indica_pa
    ):

        estacoes_para.append(
            (
                arquivo_info,
                metadados
            )
        )


print(
    "\nEstações/arquivos identificados no Pará:",
    len(estacoes_para)
)


# ============================================================
# 6. PROCESSA CADA ESTAÇÃO
# ============================================================

resultados = []

estacoes_processadas = 0
estacoes_com_erro = 0


for indice, (
    arquivo_info,
    metadados
) in enumerate(
    estacoes_para,
    start=1
):

    arquivo_bronze = Path(
        arquivo_info[
            "bronze_file"
        ]
    )


    if not arquivo_bronze.exists():

        print(
            "Arquivo não encontrado:",
            arquivo_bronze
        )

        estacoes_com_erro += 1

        continue


    nome_estacao = (
        metadados.get(
            "ESTACAO"
        )
        or metadados.get(
            "ESTACAO METEOROLOGICA"
        )
        or Path(
            arquivo_info[
                "source_file"
            ]
        ).stem
    )


    codigo_estacao = (
        metadados.get(
            "CODIGO WMO"
        )
        or metadados.get(
            "CODIGO OMM"
        )
        or ""
    )


    latitude = converter_numero(
        metadados.get(
            "LATITUDE"
        )
    )

    longitude = converter_numero(
        metadados.get(
            "LONGITUDE"
        )
    )

    altitude = converter_numero(
        metadados.get(
            "ALTITUDE"
        )
    )


    print(
        f"[{indice}/{len(estacoes_para)}] "
        f"{codigo_estacao} - {nome_estacao}"
    )


    # ========================================================
    # 6.1 LÊ BRONZE DA ESTAÇÃO
    # ========================================================

    df = pd.read_csv(
        arquivo_bronze,
        compression="gzip",
        dtype="string",
        low_memory=False
    )


    colunas = list(
        df.columns
    )


    # ========================================================
    # 6.2 IDENTIFICA COLUNAS
    # ========================================================

    coluna_data = encontrar_coluna(
        colunas,
        [
            "DATA"
        ]
    )


    coluna_precipitacao = encontrar_coluna(
        colunas,
        [
            "PRECIPITACAO",
            "TOTAL",
            "HORARIO"
        ]
    )


    coluna_temperatura = encontrar_coluna(
        colunas,
        [
            "TEMPERATURA",
            "BULBO",
            "SECO",
            "HORARIA"
        ]
    )


    coluna_umidade = encontrar_coluna(
        colunas,
        [
            "UMIDADE",
            "RELATIVA",
            "AR",
            "HORARIA"
        ],
        proibidos=[
            "MAX",
            "MIN"
        ]
    )


    faltantes = []


    if coluna_data is None:
        faltantes.append(
            "data"
        )

    if coluna_precipitacao is None:
        faltantes.append(
            "precipitacao"
        )

    if coluna_temperatura is None:
        faltantes.append(
            "temperatura"
        )

    if coluna_umidade is None:
        faltantes.append(
            "umidade"
        )


    if faltantes:

        print(
            "  Colunas não encontradas:",
            faltantes
        )

        estacoes_com_erro += 1

        continue


    # ========================================================
    # 6.3 CONVERSÃO DA DATA
    # ========================================================

    data = pd.to_datetime(
        df[
            coluna_data
        ],
        errors="coerce",
        format="%Y/%m/%d"
    )


    # Caso algum arquivo utilize hífen
    falhas_data = data.isna()


    if falhas_data.any():

        data_alternativa = pd.to_datetime(
            df.loc[
                falhas_data,
                coluna_data
            ],
            errors="coerce",
            format="%Y-%m-%d"
        )

        data.loc[
            falhas_data
        ] = data_alternativa


    df[
        "_data"
    ] = data


    # ========================================================
    # 6.4 FILTRA ANO
    # ========================================================

    df = df[
        df[
            "_data"
        ].dt.year == ANO
    ].copy()


    if df.empty:

        continue


    # ========================================================
    # 6.5 CONVERTE VARIÁVEIS NUMÉRICAS
    # ========================================================

    df[
        "_precipitacao"
    ] = (
        df[
            coluna_precipitacao
        ]
        .apply(
            converter_numero
        )
    )


    df[
        "_temperatura"
    ] = (
        df[
            coluna_temperatura
        ]
        .apply(
            converter_numero
        )
    )


    df[
        "_umidade"
    ] = (
        df[
            coluna_umidade
        ]
        .apply(
            converter_numero
        )
    )


    # ========================================================
    # 6.6 VALIDAÇÕES DE DOMÍNIO
    # ========================================================

    # Precipitação negativa não faz sentido
    df.loc[
        df[
            "_precipitacao"
        ] < 0,
        "_precipitacao"
    ] = pd.NA


    # Umidade relativa deve estar
    # entre 0 e 100 %
    df.loc[
        (
            df[
                "_umidade"
            ] < 0
        )
        |
        (
            df[
                "_umidade"
            ] > 100
        ),
        "_umidade"
    ] = pd.NA


    # Limite físico/técnico conservador
    # apenas para capturar sentinelas
    # ou erros grosseiros.

    df.loc[
        (
            df[
                "_temperatura"
            ] < -50
        )
        |
        (
            df[
                "_temperatura"
            ] > 60
        ),
        "_temperatura"
    ] = pd.NA


    # ========================================================
    # 6.7 COMPETÊNCIA
    # ========================================================

    df[
        "competencia"
    ] = (
        df[
            "_data"
        ]
        .dt.to_period(
            "M"
        )
        .astype(
            "string"
        )
    )


    # ========================================================
    # 6.8 AGREGAÇÃO MENSAL
    # ========================================================

    mensal = (
        df
        .groupby(
            "competencia",
            as_index=False
        )
        .agg(
            precipitacao_total_mm=(
                "_precipitacao",
                lambda x: x.sum(
                    min_count=1
                )
            ),

            temperatura_media_c=(
                "_temperatura",
                "mean"
            ),

            umidade_media_pct=(
                "_umidade",
                "mean"
            ),

            observacoes_horarias=(
                "_data",
                "count"
            ),

            observacoes_precipitacao=(
                "_precipitacao",
                "count"
            ),

            observacoes_temperatura=(
                "_temperatura",
                "count"
            ),

            observacoes_umidade=(
                "_umidade",
                "count"
            )
        )
    )


    # ========================================================
    # 6.9 HORAS ESPERADAS
    # ========================================================

    periodo = pd.PeriodIndex(
        mensal[
            "competencia"
        ],
        freq="M"
    )


    mensal[
        "horas_esperadas"
    ] = (
        periodo.days_in_month
        * 24
    )


    mensal[
        "cobertura_temperatura_pct"
    ] = (
        mensal[
            "observacoes_temperatura"
        ]
        /
        mensal[
            "horas_esperadas"
        ]
        * 100
    )


    mensal[
        "cobertura_umidade_pct"
    ] = (
        mensal[
            "observacoes_umidade"
        ]
        /
        mensal[
            "horas_esperadas"
        ]
        * 100
    )


    mensal[
        "cobertura_precipitacao_pct"
    ] = (
        mensal[
            "observacoes_precipitacao"
        ]
        /
        mensal[
            "horas_esperadas"
        ]
        * 100
    )


    # ========================================================
    # 6.10 METADADOS DA ESTAÇÃO
    # ========================================================

    mensal[
        "codigo_estacao"
    ] = codigo_estacao


    mensal[
        "estacao"
    ] = nome_estacao


    mensal[
        "estacao_normalizada"
    ] = normalizar_texto(
        nome_estacao
    )


    mensal[
        "latitude"
    ] = latitude


    mensal[
        "longitude"
    ] = longitude


    mensal[
        "altitude"
    ] = altitude


    mensal[
        "source_file"
    ] = arquivo_info[
        "source_file"
    ]


    resultados.append(
        mensal
    )


    estacoes_processadas += 1


# ============================================================
# 7. CONSOLIDA ESTAÇÕES
# ============================================================

if not resultados:

    raise ValueError(
        "Nenhuma estação do Pará foi processada."
    )


silver = pd.concat(
    resultados,
    ignore_index=True
)


# ============================================================
# 8. TENTA ASSOCIAR ESTAÇÃO AO MUNICÍPIO IBGE
# ============================================================

silver = silver.merge(
    df_ibge[
        [
            "codigo_ibge",
            "codigo_ibge_6",
            "municipio",
            "municipio_normalizado"
        ]
    ],
    left_on=(
        "estacao_normalizada"
    ),
    right_on=(
        "municipio_normalizado"
    ),
    how="left"
)


silver[
    "match_ibge"
] = (
    silver[
        "codigo_ibge"
    ].notna()
)


# ============================================================
# 9. ESTAÇÕES SEM MATCH
# ============================================================

sem_match = (
    silver[
        ~silver[
            "match_ibge"
        ]
    ][
        [
            "codigo_estacao",
            "estacao",
            "latitude",
            "longitude",
            "source_file"
        ]
    ]
    .drop_duplicates()
)


if not sem_match.empty:

    sem_match.to_csv(
        ARQUIVO_SEM_MATCH,
        index=False,
        encoding="utf-8"
    )


# ============================================================
# 10. VALIDA CHAVE DA SILVER
# ============================================================

duplicatas = silver.duplicated(
    subset=[
        "codigo_estacao",
        "competencia"
    ]
).sum()


if duplicatas > 0:

    raise ValueError(
        "Existem duplicatas na chave "
        "codigo_estacao + competencia."
    )


# ============================================================
# 11. ORDENA COLUNAS
# ============================================================

silver = silver[
    [
        "codigo_estacao",
        "estacao",
        "latitude",
        "longitude",
        "altitude",
        "codigo_ibge",
        "codigo_ibge_6",
        "municipio",
        "competencia",
        "precipitacao_total_mm",
        "temperatura_media_c",
        "umidade_media_pct",
        "observacoes_horarias",
        "horas_esperadas",
        "cobertura_precipitacao_pct",
        "cobertura_temperatura_pct",
        "cobertura_umidade_pct",
        "match_ibge",
        "source_file"
    ]
]


silver = silver.sort_values(
    [
        "codigo_estacao",
        "competencia"
    ]
).reset_index(
    drop=True
)


# ============================================================
# 12. SALVA SILVER
# ============================================================

silver.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)


# ============================================================
# 13. RESUMO
# ============================================================

estacoes_unicas = silver[
    "codigo_estacao"
].nunique()


estacoes_com_match = (
    silver[
        silver[
            "match_ibge"
        ]
    ][
        "codigo_estacao"
    ]
    .nunique()
)


municipios_cobertos = (
    silver[
        "codigo_ibge"
    ]
    .dropna()
    .nunique()
)


print(
    "\n========================================"
)

print(
    "RESUMO DA SILVER - INMET"
)

print(
    "========================================"
)

print(
    "Carga Bronze utilizada:",
    manifesto["load_id"]
)

print(
    "Estações/arquivos do Pará:",
    len(estacoes_para)
)

print(
    "Estações processadas:",
    estacoes_processadas
)

print(
    "Estações com erro:",
    estacoes_com_erro
)

print(
    "Estações únicas na Silver:",
    estacoes_unicas
)

print(
    "Linhas estação/mês:",
    len(silver)
)

print(
    "Estações com match direto no IBGE:",
    estacoes_com_match
)

print(
    "Estações sem match direto:",
    len(sem_match)
)

print(
    "Municípios cobertos diretamente:",
    municipios_cobertos
)

print(
    "Duplicatas na chave:",
    duplicatas
)

print(
    "Arquivo Silver:",
    ARQUIVO_SAIDA
)

if not sem_match.empty:

    print(
        "Arquivo de estações sem match:",
        ARQUIVO_SEM_MATCH
    )

print(
    "========================================"
)