import json
from pathlib import Path

import pandas as pd



ANO = 2024

PASTA_BRONZE = Path(
    "data/bronze/nasa_power"
)

PASTA_SILVER = Path(
    "data/silver/nasa_power"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/nasa_power"
)

ARQUIVO_IBGE = Path(
    "data/silver/ibge/municipios_para_coordenadas.csv"
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
    / f"clima_para_{ANO}_silver.csv"
)

ARQUIVO_QUARENTENA = (
    PASTA_QUARENTENA
    / f"registros_invalidos_silver_{ANO}.csv"
)


manifestos = list(
    PASTA_BRONZE.glob(
        f"manifest_{ANO}_*.json"
    )
)

if not manifestos:

    raise FileNotFoundError(
        "Nenhum manifesto Bronze da NASA POWER foi encontrado."
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
        f"Arquivo Bronze não encontrado: "
        f"{arquivo_bronze}"
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



if not ARQUIVO_IBGE.exists():

    raise FileNotFoundError(
        "Arquivo de municípios/coordenadas "
        "do IBGE não encontrado."
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


if len(df_ibge) != 144:

    raise ValueError(
        f"Esperados 144 municípios no IBGE, "
        f"mas encontrados {len(df_ibge)}."
    )


print(
    "\nMunicípios IBGE:",
    len(df_ibge)
)



def limpar_valor(
    valor
):

    if valor is None:

        return None


    try:

        numero = float(
            valor
        )

    except (
        ValueError,
        TypeError
    ):

        return None


    # Valores sentinela utilizados para
    # indicar ausência em produtos meteorológicos.
    if numero <= -900:

        return None


    return numero



registros_diarios = []

registros_invalidos = []

municipios_lidos = 0


with arquivo_bronze.open(
    "r",
    encoding="utf-8"
) as arquivo:

    for numero_linha, linha in enumerate(
        arquivo,
        start=1
    ):

        linha = linha.strip()

        if not linha:

            continue


        try:

            registro = json.loads(
                linha
            )


            codigo_ibge = str(
                registro[
                    "codigo_ibge"
                ]
            )


            municipio = registro[
                "municipio"
            ]


            latitude = float(
                registro[
                    "latitude_consulta"
                ]
            )


            longitude = float(
                registro[
                    "longitude_consulta"
                ]
            )


            resposta = registro[
                "response"
            ]


            parametros = (
                resposta
                .get(
                    "properties",
                    {}
                )
                .get(
                    "parameter",
                    {}
                )
            )


            t2m = parametros.get(
                "T2M"
            )


            rh2m = parametros.get(
                "RH2M"
            )


            precipitacao = parametros.get(
                "PRECTOTCORR"
            )


            if not t2m:

                raise ValueError(
                    "T2M ausente."
                )


            if not rh2m:

                raise ValueError(
                    "RH2M ausente."
                )


            if not precipitacao:

                raise ValueError(
                    "PRECTOTCORR ausente."
                )


            

            datas = sorted(
                set(
                    t2m.keys()
                )
                |
                set(
                    rh2m.keys()
                )
                |
                set(
                    precipitacao.keys()
                )
            )


            for data_texto in datas:

                data = pd.to_datetime(
                    data_texto,
                    format="%Y%m%d",
                    errors="coerce"
                )


                if pd.isna(
                    data
                ):

                    continue


                if data.year != ANO:

                    continue


                temperatura = limpar_valor(
                    t2m.get(
                        data_texto
                    )
                )


                umidade = limpar_valor(
                    rh2m.get(
                        data_texto
                    )
                )


                chuva = limpar_valor(
                    precipitacao.get(
                        data_texto
                    )
                )


            

                if (
                    temperatura is not None
                    and (
                        temperatura < -50
                        or temperatura > 60
                    )
                ):

                    temperatura = None


                if (
                    umidade is not None
                    and (
                        umidade < 0
                        or umidade > 100
                    )
                ):

                    umidade = None


                if (
                    chuva is not None
                    and chuva < 0
                ):

                    chuva = None


                registros_diarios.append(
                    {
                        "codigo_ibge": codigo_ibge,

                        "municipio": municipio,

                        "latitude": latitude,

                        "longitude": longitude,

                        "data": data,

                        "temperatura_media_c": temperatura,

                        "umidade_media_pct": umidade,

                        "precipitacao_mm": chuva
                    }
                )


            municipios_lidos += 1


        except Exception as erro:

            registros_invalidos.append(
                {
                    "numero_linha": numero_linha,

                    "codigo_ibge": registro.get(
                        "codigo_ibge",
                        None
                    )
                    if "registro" in locals()
                    else None,

                    "erro": str(
                        erro
                    )
                }
            )



df_diario = pd.DataFrame(
    registros_diarios
)


if df_diario.empty:

    raise ValueError(
        "Nenhum dado diário válido foi encontrado."
    )


print(
    "\nMunicípios lidos da Bronze:",
    municipios_lidos
)

print(
    "Registros diários:",
    len(df_diario)
)



duplicatas_diarias = df_diario.duplicated(
    subset=[
        "codigo_ibge",
        "data"
    ]
).sum()


print(
    "Duplicatas município/dia:",
    duplicatas_diarias
)


if duplicatas_diarias > 0:

    raise ValueError(
        "Existem duplicatas na chave "
        "codigo_ibge + data."
    )



df_diario[
    "competencia"
] = (
    df_diario[
        "data"
    ]
    .dt.to_period(
        "M"
    )
    .astype(
        "string"
    )
)


silver_clima = (
    df_diario
    .groupby(
        [
            "codigo_ibge",
            "municipio",
            "latitude",
            "longitude",
            "competencia"
        ],
        as_index=False
    )
    .agg(

        temperatura_media_c=(
            "temperatura_media_c",
            "mean"
        ),

        umidade_media_pct=(
            "umidade_media_pct",
            "mean"
        ),

        precipitacao_total_mm=(
            "precipitacao_mm",
            lambda serie: serie.sum(
                min_count=1
            )
        ),

        dias_temperatura_validos=(
            "temperatura_media_c",
            "count"
        ),

        dias_umidade_validos=(
            "umidade_media_pct",
            "count"
        ),

        dias_precipitacao_validos=(
            "precipitacao_mm",
            "count"
        )
    )
)



periodos = pd.PeriodIndex(
    silver_clima[
        "competencia"
    ],
    freq="M"
)


silver_clima[
    "dias_esperados"
] = (
    periodos.days_in_month
)



silver_clima[
    "cobertura_temperatura_pct"
] = (
    silver_clima[
        "dias_temperatura_validos"
    ]
    /
    silver_clima[
        "dias_esperados"
    ]
    * 100
)


silver_clima[
    "cobertura_umidade_pct"
] = (
    silver_clima[
        "dias_umidade_validos"
    ]
    /
    silver_clima[
        "dias_esperados"
    ]
    * 100
)


silver_clima[
    "cobertura_precipitacao_pct"
] = (
    silver_clima[
        "dias_precipitacao_validos"
    ]
    /
    silver_clima[
        "dias_esperados"
    ]
    * 100
)



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
        "uf",
        "latitude",
        "longitude"
    ]
].copy()


municipios[
    "_join"
] = 1

competencias[
    "_join"
] = 1


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


print(
    "\nLinhas esperadas no painel:",
    144 * 12
)

print(
    "Linhas criadas:",
    len(painel)
)



colunas_clima = [
    "codigo_ibge",
    "competencia",
    "temperatura_media_c",
    "umidade_media_pct",
    "precipitacao_total_mm",
    "dias_temperatura_validos",
    "dias_umidade_validos",
    "dias_precipitacao_validos",
    "dias_esperados",
    "cobertura_temperatura_pct",
    "cobertura_umidade_pct",
    "cobertura_precipitacao_pct"
]


resultado = painel.merge(
    silver_clima[
        colunas_clima
    ],
    on=[
        "codigo_ibge",
        "competencia"
    ],
    how="left",
    validate="one_to_one"
)



sem_clima = resultado[
    resultado[
        "temperatura_media_c"
    ].isna()
    |
    resultado[
        "umidade_media_pct"
    ].isna()
    |
    resultado[
        "precipitacao_total_mm"
    ].isna()
].copy()



duplicatas = resultado.duplicated(
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


if len(resultado) != 1728:

    raise ValueError(
        f"Esperadas 1728 linhas, "
        f"encontradas {len(resultado)}."
    )


if (
    resultado[
        "codigo_ibge"
    ].nunique()
    != 144
):

    raise ValueError(
        "A Silver não contém os 144 municípios."
    )


if (
    resultado[
        "competencia"
    ].nunique()
    != 12
):

    raise ValueError(
        "A Silver não contém as 12 competências."
    )



for coluna in [
    "temperatura_media_c",
    "umidade_media_pct",
    "precipitacao_total_mm",
    "cobertura_temperatura_pct",
    "cobertura_umidade_pct",
    "cobertura_precipitacao_pct"
]:

    resultado[
        coluna
    ] = (
        resultado[
            coluna
        ]
        .round(
            3
        )
    )



resultado = resultado.sort_values(
    [
        "codigo_ibge",
        "competencia"
    ]
).reset_index(
    drop=True
)



resultado.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)



problemas = []


if registros_invalidos:

    problemas.extend(
        registros_invalidos
    )


if not sem_clima.empty:

    for _, linha in sem_clima.iterrows():

        problemas.append(
            {
                "codigo_ibge": (
                    linha[
                        "codigo_ibge"
                    ]
                ),

                "municipio": (
                    linha[
                        "municipio"
                    ]
                ),

                "competencia": (
                    linha[
                        "competencia"
                    ]
                ),

                "erro": (
                    "dados_climaticos_ausentes"
                )
            }
        )


if problemas:

    pd.DataFrame(
        problemas
    ).to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )


cobertura_temp_min = resultado[
    "cobertura_temperatura_pct"
].min()


cobertura_umid_min = resultado[
    "cobertura_umidade_pct"
].min()


cobertura_chuva_min = resultado[
    "cobertura_precipitacao_pct"
].min()



print(
    "\n========================================"
)

print(
    "RESUMO DA SILVER - NASA POWER"
)

print(
    "========================================"
)

print(
    "Carga Bronze utilizada:",
    manifesto["load_id"]
)

print(
    "Municípios lidos:",
    municipios_lidos
)

print(
    "Registros diários:",
    len(df_diario)
)

print(
    "Duplicatas município/dia:",
    duplicatas_diarias
)

print(
    "Municípios:",
    resultado[
        "codigo_ibge"
    ].nunique()
)

print(
    "Competências:",
    resultado[
        "competencia"
    ].nunique()
)

print(
    "Linhas da Silver:",
    len(resultado)
)

print(
    "Registros município/mês sem clima:",
    len(sem_clima)
)

print(
    "Duplicatas na chave:",
    duplicatas
)

print(
    "\nCobertura mínima de temperatura:",
    round(
        cobertura_temp_min,
        2
    ),
    "%"
)

print(
    "Cobertura mínima de umidade:",
    round(
        cobertura_umid_min,
        2
    ),
    "%"
)

print(
    "Cobertura mínima de precipitação:",
    round(
        cobertura_chuva_min,
        2
    ),
    "%"
)

print(
    "\nArquivo Silver:",
    ARQUIVO_SAIDA
)

if problemas:

    print(
        "Quarentena:",
        ARQUIVO_QUARENTENA
    )

else:

    print(
        "Quarentena: nenhum problema"
    )

print(
    "========================================"
)