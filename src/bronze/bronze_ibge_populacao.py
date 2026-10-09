import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



ANO = 2024

SOURCE_SYSTEM = "IBGE SIDRA"
SOURCE_OBJECT = "Tabela 6579 - Populacao residente estimada"


URL = (
    "https://apisidra.ibge.gov.br/"
    "values/t/6579/"
    "n6/in%20n3%2015/"
    f"p/{ANO}/"
    "v/9324"
    "?formato=json"
)

load_id = str(uuid.uuid4())

ingestion_timestamp = datetime.now(
    timezone.utc
)

data_particao = ingestion_timestamp.strftime(
    "%Y-%m-%d"
)



PASTA_BASE = Path(
    "data/bronze/ibge_populacao"
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

PASTA_RAW.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_RECORDS.mkdir(
    parents=True,
    exist_ok=True
)



retry = Retry(
    total=5,
    backoff_factor=1,
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



print(
    "Iniciando Bronze da população IBGE..."
)

print(
    "Fonte:",
    URL
)

resposta = session.get(
    URL,
    timeout=60
)

print(
    "Status HTTP:",
    resposta.status_code
)

resposta.raise_for_status()


dados = resposta.json()


if not isinstance(
    dados,
    list
):

    raise ValueError(
        "A resposta do SIDRA não veio como lista."
    )


if len(dados) < 2:

    raise ValueError(
        "A API não retornou registros de população."
    )




arquivo_raw = (
    PASTA_RAW
    / f"populacao_para_{ANO}_{load_id}.json"
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



cabecalho = dados[0]

registros_originais = dados[1:]


print(
    "\nRegistros recebidos:",
    len(registros_originais)
)

print(
    "\nCabeçalho retornado pelo SIDRA:"
)

print(
    json.dumps(
        cabecalho,
        ensure_ascii=False,
        indent=2
    )
)




def gerar_hash(
    registro
):

    texto = json.dumps(
        registro,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        texto.encode(
            "utf-8"
        )
    ).hexdigest()




arquivo_bronze = (
    PASTA_RECORDS
    / f"populacao_para_{ANO}_{load_id}.jsonl"
)


hashes = set()

hashes_duplicados = 0


with arquivo_bronze.open(
    "w",
    encoding="utf-8"
) as arquivo:

    for registro_original in registros_originais:

        record_hash = gerar_hash(
            registro_original
        )


        if record_hash in hashes:

            hashes_duplicados += 1

        else:

            hashes.add(
                record_hash
            )


        registro_bronze = dict(
            registro_original
        )


        registro_bronze[
            "_ingestion_timestamp"
        ] = ingestion_timestamp.isoformat()


        registro_bronze[
            "_source_system"
        ] = SOURCE_SYSTEM


        registro_bronze[
            "_source_object"
        ] = SOURCE_OBJECT


        registro_bronze[
            "_source_url"
        ] = URL


        registro_bronze[
            "_load_id"
        ] = load_id


        registro_bronze[
            "_record_hash"
        ] = record_hash


        arquivo.write(
            json.dumps(
                registro_bronze,
                ensure_ascii=False
            )
            + "\n"
        )



manifesto = {

    "load_id": load_id,

    "ingestion_timestamp": (
        ingestion_timestamp.isoformat()
    ),

    "source_system": SOURCE_SYSTEM,

    "source_object": SOURCE_OBJECT,

    "source_url": URL,

    "table": 6579,

    "variable": 9324,

    "ano": ANO,

    "reference_date": (
        f"{ANO}-07-01"
    ),

    "record_count": (
        len(registros_originais)
    ),

    "duplicate_hashes_in_load": (
        hashes_duplicados
    ),

    "sidra_header": (
        cabecalho
    ),

    "raw_file": str(
        arquivo_raw
    ),

    "bronze_file": str(
        arquivo_bronze
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
    "RESUMO DA BRONZE - POPULAÇÃO IBGE"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Tabela SIDRA:",
    6579
)

print(
    "Variável:",
    9324
)

print(
    "Registros recebidos:",
    len(registros_originais)
)

print(
    "Hashes duplicados:",
    hashes_duplicados
)

print(
    "Load ID:",
    load_id
)

print(
    "Arquivo bruto:",
    arquivo_raw
)

print(
    "Arquivo Bronze:",
    arquivo_bronze
)

print(
    "Manifesto:",
    arquivo_manifesto
)

print(
    "========================================"
)