import json
from pathlib import Path

import pandas as pd
from shapely.geometry import shape



ANO = 2024

PASTA_BRONZE = Path(
    "data/bronze/ibge_malha"
)

PASTA_SILVER = Path(
    "data/silver/ibge"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/ibge"
)

ARQUIVO_MUNICIPIOS = (
    PASTA_SILVER
    / "municipios_para_silver.csv"
)

ARQUIVO_SAIDA = (
    PASTA_SILVER
    / "municipios_para_coordenadas.csv"
)

ARQUIVO_QUARENTENA = (
    PASTA_QUARENTENA
    / "geometrias_invalidas_2024.csv"
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
        "Nenhum manifesto da malha IBGE foi encontrado."
    )


cargas = []

for arquivo_manifesto in manifestos:

    with arquivo_manifesto.open(
        "r",
        encoding="utf-8"
    ) as f:

        manifesto = json.load(f)

    cargas.append(
        (
            pd.to_datetime(
                manifesto["ingestion_timestamp"],
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
    manifesto["bronze_file"]
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




features = []

with arquivo_bronze.open(
    "r",
    encoding="utf-8"
) as arquivo:

    for linha in arquivo:

        linha = linha.strip()

        if not linha:
            continue

        features.append(
            json.loads(
                linha
            )
        )


print(
    "\nFeatures lidas:",
    len(features)
)


if len(features) == 0:

    raise ValueError(
        "Nenhuma geometria foi encontrada."
    )



propriedades_exemplo = features[0].get(
    "properties",
    {}
)

campos_disponiveis = list(
    propriedades_exemplo.keys()
)


print(
    "\nCampos disponíveis:"
)

print(
    campos_disponiveis
)



candidatos_codigo = [
    "CD_MUN",
    "CD_GEOCMU",
    "CODAREA",
    "GEOCODIGO",
    "COD_MUN",
    "ID_MUNICIP"
]


campo_codigo = None

for candidato in candidatos_codigo:

    if candidato in campos_disponiveis:

        campo_codigo = candidato
        break


if campo_codigo is None:

    raise ValueError(
        "Não foi possível identificar o campo "
        "de código municipal. Campos encontrados: "
        + str(campos_disponiveis)
    )


print(
    "\nCampo identificado como código municipal:",
    campo_codigo
)



registros = []
invalidos = []


for feature in features:

    propriedades = feature.get(
        "properties",
        {}
    )

    geometria_json = feature.get(
        "geometry"
    )

    codigo_original = propriedades.get(
        campo_codigo
    )


    try:

    

        if codigo_original is None:

            raise ValueError(
                "Código IBGE ausente."
            )


        codigo_ibge = (
            str(
                codigo_original
            )
            .strip()
            .replace(
                ".0",
                ""
            )
            .zfill(7)
        )


    

        if geometria_json is None:

            raise ValueError(
                "Geometria ausente."
            )


        geometria = shape(
            geometria_json
        )


        if geometria.is_empty:

            raise ValueError(
                "Geometria vazia."
            )



        ponto = geometria.representative_point()


        latitude = float(
            ponto.y
        )

        longitude = float(
            ponto.x
        )



        if not (
            -90
            <= latitude
            <= 90
        ):

            raise ValueError(
                f"Latitude inválida: {latitude}"
            )


        if not (
            -180
            <= longitude
            <= 180
        ):

            raise ValueError(
                f"Longitude inválida: {longitude}"
            )


        registros.append(
            {
                "codigo_ibge": codigo_ibge,
                "latitude": latitude,
                "longitude": longitude
            }
        )


    except Exception as erro:

        invalidos.append(
            {
                "codigo_original": codigo_original,
                "erro": str(erro)
            }
        )



df_coord = pd.DataFrame(
    registros
)


print(
    "\nCoordenadas extraídas:",
    len(df_coord)
)



duplicatas_coord = df_coord.duplicated(
    subset=[
        "codigo_ibge"
    ]
).sum()


if duplicatas_coord > 0:

    raise ValueError(
        f"Foram encontrados "
        f"{duplicatas_coord} códigos duplicados."
    )



if not ARQUIVO_MUNICIPIOS.exists():

    raise FileNotFoundError(
        "Silver dos municípios não encontrada. "
        "Execute primeiro silver_ibge.py."
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


print(
    "Municípios na Silver IBGE:",
    len(df_municipios)
)



resultado = df_municipios.merge(
    df_coord,
    on="codigo_ibge",
    how="left",
    validate="one_to_one"
)



sem_coordenada = resultado[
    resultado[
        "latitude"
    ].isna()
    |
    resultado[
        "longitude"
    ].isna()
].copy()



if len(resultado) != 144:

    raise ValueError(
        f"Esperados 144 municípios, "
        f"encontrados {len(resultado)}."
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


if not sem_coordenada.empty:

    sem_coordenada.to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )

    raise ValueError(
        f"{len(sem_coordenada)} municípios "
        "ficaram sem coordenadas."
    )



resultado = resultado[
    [
        "codigo_ibge",
        "codigo_ibge_6",
        "municipio",
        "codigo_uf",
        "uf",
        "latitude",
        "longitude"
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


if invalidos:

    pd.DataFrame(
        invalidos
    ).to_csv(
        ARQUIVO_QUARENTENA,
        index=False,
        encoding="utf-8"
    )



print(
    "\n========================================"
)

print(
    "RESUMO - COORDENADAS DOS MUNICÍPIOS"
)

print(
    "========================================"
)

print(
    "Geometrias Bronze:",
    len(features)
)

print(
    "Coordenadas extraídas:",
    len(df_coord)
)

print(
    "Municípios:",
    len(resultado)
)

print(
    "Municípios com coordenadas:",
    resultado[
        "latitude"
    ].notna().sum()
)

print(
    "Municípios sem coordenadas:",
    len(sem_coordenada)
)

print(
    "Geometrias inválidas:",
    len(invalidos)
)

print(
    "Duplicatas:",
    duplicatas
)

print(
    "Arquivo:",
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