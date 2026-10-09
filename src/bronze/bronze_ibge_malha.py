import hashlib
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import shapefile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



ANO = 2024

SOURCE_SYSTEM = "IBGE"
SOURCE_OBJECT = f"Malha Municipal do Para {ANO}"

# URL construída em partes apenas para facilitar manutenção
URL = (
    "https://"
    + "geoftp.ibge.gov.br"
    + "/organizacao_do_territorio/"
    + "malhas_territoriais/malhas_municipais/"
    + f"municipio_{ANO}/UFs/PA/"
    + f"PA_Municipios_{ANO}.zip"
)

load_id = str(uuid.uuid4())

ingestion_timestamp = datetime.now(
    timezone.utc
)

data_particao = ingestion_timestamp.strftime(
    "%Y-%m-%d"
)



PASTA_BASE = Path(
    "data/bronze/ibge_malha"
)

PASTA_RAW = (
    PASTA_BASE
    / "raw"
    / f"ano={ANO}"
    / f"ingestion_date={data_particao}"
)

PASTA_EXTRAIDA = (
    PASTA_RAW
    / "extracted"
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

PASTA_EXTRAIDA.mkdir(
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
    "Iniciando Bronze da malha municipal do IBGE..."
)

print(
    "Load ID:",
    load_id
)

print(
    "Ano:",
    ANO
)

print(
    "Fonte:",
    URL
)


arquivo_zip = (
    PASTA_RAW
    / f"PA_Municipios_{ANO}_{load_id}.zip"
)


hash_arquivo = hashlib.sha256()


try:

    with session.get(
        URL,
        stream=True,
        timeout=120
    ) as resposta:

        print(
            "Status HTTP:",
            resposta.status_code
        )

        resposta.raise_for_status()

        with arquivo_zip.open(
            "wb"
        ) as arquivo:

            for bloco in resposta.iter_content(
                chunk_size=1024 * 1024
            ):

                if not bloco:
                    continue

                arquivo.write(
                    bloco
                )

                hash_arquivo.update(
                    bloco
                )

except requests.exceptions.RequestException as erro:

    print(
        "Erro ao baixar a malha municipal:"
    )

    print(erro)

    raise


zip_sha256 = hash_arquivo.hexdigest()


print(
    "\nArquivo ZIP salvo em:"
)

print(
    arquivo_zip
)

print(
    "SHA-256 do ZIP:",
    zip_sha256
)



if not zipfile.is_zipfile(
    arquivo_zip
):

    raise ValueError(
        "O arquivo recebido não é um ZIP válido."
    )



with zipfile.ZipFile(
    arquivo_zip,
    "r"
) as arquivo:

    arquivos_zip = arquivo.namelist()

    print(
        "\nArquivos encontrados dentro do ZIP:"
    )

    for nome in arquivos_zip:
        print(
            "-",
            nome
        )

    arquivo.extractall(
        PASTA_EXTRAIDA
    )



arquivos_shp = list(
    PASTA_EXTRAIDA.glob(
        "**/*.shp"
    )
)


if not arquivos_shp:

    raise FileNotFoundError(
        "Nenhum arquivo .shp foi encontrado."
    )


if len(arquivos_shp) > 1:

    print(
        "\nAviso: mais de um SHP encontrado."
    )


arquivo_shp = arquivos_shp[0]


print(
    "\nShapefile encontrado:"
)

print(
    arquivo_shp
)



arquivo_cpg = arquivo_shp.with_suffix(
    ".cpg"
)


encoding = "latin1"


if arquivo_cpg.exists():

    valor_cpg = (
        arquivo_cpg
        .read_text(
            encoding="ascii",
            errors="ignore"
        )
        .strip()
        .upper()
    )

    mapa_encoding = {
        "UTF-8": "utf-8",
        "UTF8": "utf-8",
        "1252": "cp1252",
        "CP1252": "cp1252",
        "ISO-8859-1": "latin1",
        "LATIN1": "latin1"
    }

    encoding = mapa_encoding.get(
        valor_cpg,
        valor_cpg.lower()
    )


print(
    "Encoding utilizado:",
    encoding
)



try:

    leitor = shapefile.Reader(
        str(
            arquivo_shp
        ),
        encoding=encoding
    )

except Exception:

    print(
        "Falha com encoding informado. "
        "Tentando latin1..."
    )

    leitor = shapefile.Reader(
        str(
            arquivo_shp
        ),
        encoding="latin1"
    )



campos = [
    campo[0]
    for campo in leitor.fields
    if campo[0]
    != "DeletionFlag"
]


print(
    "\nCampos encontrados:"
)

print(
    campos
)



def gerar_hash(
    propriedades,
    geometria
):

    conteudo = {
        "properties": propriedades,
        "geometry": geometria
    }

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



arquivo_records = (
    PASTA_RECORDS
    / f"malha_para_{ANO}_{load_id}.jsonl"
)


quantidade_registros = 0

hashes = set()

hashes_duplicados = 0


with arquivo_records.open(
    "w",
    encoding="utf-8"
) as saida:

    for shape_record in leitor.iterShapeRecords():


        valores = list(
            shape_record.record
        )

        propriedades = dict(
            zip(
                campos,
                valores
            )
        )



        geometria = (
            shape_record
            .shape
            .__geo_interface__
        )



        record_hash = gerar_hash(
            propriedades,
            geometria
        )


        if record_hash in hashes:

            hashes_duplicados += 1

        else:

            hashes.add(
                record_hash
            )



        registro_bronze = {
            "type": "Feature",
            "properties": propriedades,
            "geometry": geometria,

            "_ingestion_timestamp": (
                ingestion_timestamp.isoformat()
            ),

            "_source_system": (
                SOURCE_SYSTEM
            ),

            "_source_object": (
                SOURCE_OBJECT
            ),

            "_source_file": (
                arquivo_shp.name
            ),

            "_load_id": (
                load_id
            ),

            "_record_hash": (
                record_hash
            )
        }


        saida.write(
            json.dumps(
                registro_bronze,
                ensure_ascii=False
            )
            + "\n"
        )


        quantidade_registros += 1


leitor.close()



manifesto = {
    "load_id": load_id,

    "ingestion_timestamp": (
        ingestion_timestamp.isoformat()
    ),

    "source_system": SOURCE_SYSTEM,

    "source_object": SOURCE_OBJECT,

    "source_url": URL,

    "ano": ANO,

    "raw_sha256": (
        zip_sha256
    ),

    "raw_file": str(
        arquivo_zip
    ),

    "extracted_folder": str(
        PASTA_EXTRAIDA
    ),

    "source_shapefile": str(
        arquivo_shp
    ),

    "encoding": encoding,

    "fields": campos,

    "records_processed": (
        quantidade_registros
    ),

    "duplicate_hashes_in_load": (
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
    "RESUMO DA BRONZE - MALHA IBGE"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Registros/geometrias processados:",
    quantidade_registros
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
    "SHA-256 do ZIP:",
    zip_sha256
)

print(
    "Arquivo ZIP:",
    arquivo_zip
)

print(
    "Shapefile:",
    arquivo_shp
)

print(
    "Arquivo Bronze:",
    arquivo_records
)

print(
    "Manifesto:",
    arquivo_manifesto
)

print(
    "========================================"
)