import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ANO = 2024

SOURCE_SYSTEM = "NASA POWER"
SOURCE_OBJECT = f"Daily Point Meteorology {ANO}"

BASE_URL = (
    "https://power.larc.nasa.gov/"
    "api/temporal/daily/point"
)


PARAMETROS = [
    "T2M",          
    "RH2M",         # Umidade
    "PRECTOTCORR"   
]

COMUNIDADE = "AG"

ARQUIVO_COORDENADAS = Path(
    "data/silver/ibge/municipios_para_coordenadas.csv"
)

load_id = str(
    uuid.uuid4()
)

ingestion_timestamp = datetime.now(
    timezone.utc
)

data_particao = ingestion_timestamp.strftime(
    "%Y-%m-%d"
)



PASTA_BASE = Path(
    "data/bronze/nasa_power"
)

PASTA_RAW = (
    PASTA_BASE
    / "raw"
    / f"ano={ANO}"
    / f"ingestion_date={data_particao}"
)

PASTA_RECORDS = (
    PASTA_BASE
    / "records"
    / f"ano={ANO}"
    / f"ingestion_date={data_particao}"
)

PASTA_QUARENTENA = Path(
    "data/quarantine/nasa_power"
)

PASTA_RAW.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_RECORDS.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_QUARENTENA.mkdir(
    parents=True,
    exist_ok=True
)



if not ARQUIVO_COORDENADAS.exists():

    raise FileNotFoundError(
        "Arquivo de coordenadas não encontrado. "
        "Execute primeiro silver_ibge_coordenadas.py."
    )


municipios = pd.read_csv(
    ARQUIVO_COORDENADAS,
    dtype={
        "codigo_ibge": "string",
        "codigo_ibge_6": "string",
        "municipio": "string"
    }
)


if len(municipios) != 144:

    raise ValueError(
        f"Esperados 144 municípios, "
        f"mas foram encontrados {len(municipios)}."
    )


if (
    municipios["latitude"].isna().any()
    or municipios["longitude"].isna().any()
):

    raise ValueError(
        "Existem municípios sem latitude ou longitude."
    )


duplicatas_municipio = municipios.duplicated(
    subset=[
        "codigo_ibge"
    ]
).sum()


if duplicatas_municipio > 0:

    raise ValueError(
        "Existem códigos IBGE duplicados "
        "no arquivo de coordenadas."
    )


print(
    "Municípios que serão consultados:",
    len(municipios)
)



retry = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504
    ],
    allowed_methods=[
        "GET"
    ]
)


session = requests.Session()


session.mount(
    "https://",
    HTTPAdapter(
        max_retries=retry
    )
)



arquivo_records = (
    PASTA_RECORDS
    / f"nasa_power_{ANO}_{load_id}.jsonl"
)


arquivo_erros = (
    PASTA_QUARENTENA
    / f"falhas_nasa_power_{ANO}_{load_id}.csv"
)



def gerar_hash(
    conteudo
):

    texto = json.dumps(
        conteudo,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        texto.encode(
            "utf-8"
        )
    ).hexdigest()



data_inicio = f"{ANO}0101"
data_fim = f"{ANO}1231"



sucessos = 0
falhas = 0

hashes = set()
hashes_duplicados = 0

erros = []


PARAMETROS_ESPERADOS = set(
    PARAMETROS
)




print(
    "\nIniciando consultas à NASA POWER..."
)

print(
    "Load ID:",
    load_id
)

print(
    "Parâmetros:",
    ", ".join(
        PARAMETROS
    )
)


with arquivo_records.open(
    "w",
    encoding="utf-8"
) as saida:

    for indice, municipio in municipios.iterrows():

        numero = indice + 1

        codigo_ibge = str(
            municipio["codigo_ibge"]
        )

        nome = str(
            municipio["municipio"]
        )

        latitude = float(
            municipio["latitude"]
        )

        longitude = float(
            municipio["longitude"]
        )


        print(
            f"[{numero}/144] "
            f"{codigo_ibge} - {nome}"
        )


        parametros_request = {

            "parameters": ",".join(
                PARAMETROS
            ),

            "community": COMUNIDADE,

            "longitude": longitude,

            "latitude": latitude,

            "start": data_inicio,

            "end": data_fim,

            "format": "JSON",

            "time-standard": "UTC"
        }


        try:

            

            resposta = session.get(
                BASE_URL,
                params=parametros_request,
                timeout=90
            )


            resposta.raise_for_status()


            

            dados = resposta.json()


           

            parametros_resposta = (
                dados
                .get(
                    "properties",
                    {}
                )
                .get(
                    "parameter",
                    {}
                )
            )


            parametros_recebidos = set(
                parametros_resposta.keys()
            )


            faltantes = (
                PARAMETROS_ESPERADOS
                - parametros_recebidos
            )


            if faltantes:

                raise ValueError(
                    "Parâmetros ausentes na resposta: "
                    + ", ".join(
                        sorted(
                            faltantes
                        )
                    )
                )


            

            for parametro in PARAMETROS:

                serie = parametros_resposta.get(
                    parametro,
                    {}
                )

                if not serie:

                    raise ValueError(
                        f"Parâmetro {parametro} "
                        "foi retornado sem dados."
                    )



            arquivo_raw = (
                PASTA_RAW
                / (
                    f"{codigo_ibge}_"
                    f"{load_id}.json"
                )
            )


            with arquivo_raw.open(
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    dados,
                    arquivo,
                    ensure_ascii=False,
                    indent=2
                )


            

            record_hash = gerar_hash(
                dados
            )


            if record_hash in hashes:

                hashes_duplicados += 1

            else:

                hashes.add(
                    record_hash
                )


            

            registro_bronze = {

                "codigo_ibge": codigo_ibge,

                "municipio": nome,

                "latitude_consulta": latitude,

                "longitude_consulta": longitude,

                "ano": ANO,

                "parameters": PARAMETROS,

                "community": COMUNIDADE,

                "response": dados,

                "_ingestion_timestamp": (
                    ingestion_timestamp.isoformat()
                ),

                "_source_system": (
                    SOURCE_SYSTEM
                ),

                "_source_object": (
                    SOURCE_OBJECT
                ),

                "_source_url": (
                    resposta.url
                ),

                "_load_id": (
                    load_id
                ),

                "_record_hash": (
                    record_hash
                ),

                "_raw_file": (
                    str(
                        arquivo_raw
                    )
                )
            }


            saida.write(
                json.dumps(
                    registro_bronze,
                    ensure_ascii=False
                )
                + "\n"
            )


            sucessos += 1


        except Exception as erro:

            falhas += 1


            print(
                "   ERRO:",
                erro
            )


            erros.append(
                {
                    "codigo_ibge": codigo_ibge,

                    "municipio": nome,

                    "latitude": latitude,

                    "longitude": longitude,

                    "erro": str(
                        erro
                    )
                }
            )


        

        time.sleep(
            0.5
        )


###

if erros:

    pd.DataFrame(
        erros
    ).to_csv(
        arquivo_erros,
        index=False,
        encoding="utf-8"
    )


###

if sucessos + falhas != 144:

    raise ValueError(
        "A soma de sucessos e falhas não corresponde "
        "aos 144 municípios."
    )


###

manifesto = {

    "load_id": load_id,

    "ingestion_timestamp": (
        ingestion_timestamp.isoformat()
    ),

    "source_system": SOURCE_SYSTEM,

    "source_object": SOURCE_OBJECT,

    "base_url": BASE_URL,

    "ano": ANO,

    "parameters": PARAMETROS,

    "community": COMUNIDADE,

    "time_standard": "UTC",

    "municipalities_requested": (
        len(municipios)
    ),

    "successful_requests": (
        sucessos
    ),

    "failed_requests": (
        falhas
    ),

    "duplicate_response_hashes": (
        hashes_duplicados
    ),

    "bronze_file": str(
        arquivo_records
    )
}


arquivo_manifesto = (
    PASTA_BASE
    / f"manifest_{ANO}_{load_id}.json"
)


with arquivo_manifesto.open(
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        manifesto,
        arquivo,
        ensure_ascii=False,
        indent=4
    )



print(
    "\n========================================"
)

print(
    "RESUMO DA BRONZE - NASA POWER"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Parâmetros:",
    ", ".join(
        PARAMETROS
    )
)

print(
    "Municípios solicitados:",
    len(municipios)
)

print(
    "Consultas com sucesso:",
    sucessos
)

print(
    "Consultas com falha:",
    falhas
)

print(
    "Hashes de resposta duplicados:",
    hashes_duplicados
)

print(
    "Load ID:",
    load_id
)

print(
    "Arquivo Bronze:",
    arquivo_records
)

print(
    "Manifesto:",
    arquivo_manifesto
)


if falhas > 0:

    print(
        "Quarentena:",
        arquivo_erros
    )

else:

    print(
        "Quarentena: nenhuma falha"
    )


print(
    "========================================"
)