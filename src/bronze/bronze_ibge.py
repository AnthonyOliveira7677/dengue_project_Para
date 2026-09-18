import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

SOURCE_SYSTEM = "IBGE"
SOURCE_OBJECT = "API Localidades - Municipios do Para"

URL = (
    "https://servicodados.ibge.gov.br/"
    "api/v1/localidades/estados/15/municipios"
)

# Identificador único desta execução
load_id = str(uuid.uuid4())

# Horário UTC da ingestão
ingestion_timestamp = datetime.now(timezone.utc)

data_particao = ingestion_timestamp.strftime("%Y-%m-%d")

# Pastas da Bronze
pasta_base = Path(
    "data/bronze/ibge"
)

pasta_raw = (
    pasta_base
    / "raw"
    / f"ingestion_date={data_particao}"
)

pasta_records = (
    pasta_base
    / "records"
    / f"ingestion_date={data_particao}"
)

pasta_raw.mkdir(
    parents=True,
    exist_ok=True
)

pasta_records.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. CONFIGURA RETRY + BACKOFF
# ============================================================

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

adapter = HTTPAdapter(
    max_retries=retry
)

session = requests.Session()

session.mount(
    "https://",
    adapter
)

session.mount(
    "http://",
    adapter
)


# ============================================================
# 3. FAZ A REQUISIÇÃO
# ============================================================

print("Iniciando ingestao Bronze do IBGE...")

print(
    "Load ID:",
    load_id
)

print(
    "Fonte:",
    URL
)

try:

    resposta = session.get(
        URL,
        timeout=30
    )

    print(
        "Status HTTP:",
        resposta.status_code
    )

    resposta.raise_for_status()

except requests.exceptions.RequestException as erro:

    print(
        "Erro ao acessar a API do IBGE:"
    )

    print(erro)

    raise


# ============================================================
# 4. SALVA A RESPOSTA BRUTA
# ============================================================

arquivo_raw = (
    pasta_raw
    / f"municipios_para_{load_id}.json"
)

arquivo_raw.write_bytes(
    resposta.content
)

print(
    "\nArquivo bruto salvo em:"
)

print(
    arquivo_raw
)


# ============================================================
# 5. CONVERTE RESPOSTA PARA JSON
# ============================================================

dados = resposta.json()

print(
    "\nRegistros recebidos:",
    len(dados)
)


# ============================================================
# 6. FUNÇÃO DE HASH
# ============================================================

def gerar_hash(registro):

    # Serialização determinística:
    # mesma entrada -> mesmo hash
    registro_json = json.dumps(
        registro,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        registro_json.encode("utf-8")
    ).hexdigest()


# ============================================================
# 7. ADICIONA METADADOS DA BRONZE
# ============================================================

registros_bronze = []

for registro_original in dados:

    registro = dict(
        registro_original
    )

    registro[
        "_ingestion_timestamp"
    ] = ingestion_timestamp.isoformat()

    registro[
        "_source_system"
    ] = SOURCE_SYSTEM

    registro[
        "_source_object"
    ] = SOURCE_OBJECT

    registro[
        "_load_id"
    ] = load_id

    registro[
        "_record_hash"
    ] = gerar_hash(
        registro_original
    )

    registros_bronze.append(
        registro
    )


# ============================================================
# 8. VALIDA HASHES DA CARGA
# ============================================================

hashes = [
    registro["_record_hash"]
    for registro in registros_bronze
]

duplicados = (
    len(hashes)
    - len(set(hashes))
)

print(
    "Hashes duplicados dentro da carga:",
    duplicados
)


# ============================================================
# 9. SALVA BRONZE COMO JSONL
# ============================================================

arquivo_bronze = (
    pasta_records
    / f"municipios_para_{load_id}.jsonl"
)

with arquivo_bronze.open(
    "w",
    encoding="utf-8"
) as arquivo:

    for registro in registros_bronze:

        arquivo.write(
            json.dumps(
                registro,
                ensure_ascii=False
            )
            + "\n"
        )


print(
    "\nBronze salva em:"
)

print(
    arquivo_bronze
)


# ============================================================
# 10. SALVA MANIFESTO DA CARGA
# ============================================================

manifesto = {
    "load_id": load_id,
    "ingestion_timestamp": (
        ingestion_timestamp.isoformat()
    ),
    "source_system": SOURCE_SYSTEM,
    "source_object": SOURCE_OBJECT,
    "source_url": URL,
    "http_status": resposta.status_code,
    "record_count": len(
        registros_bronze
    ),
    "duplicate_hashes_in_load": duplicados,
    "raw_file": str(
        arquivo_raw
    ),
    "bronze_file": str(
        arquivo_bronze
    )
}

arquivo_manifesto = (
    pasta_base
    / f"manifest_{load_id}.json"
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


# ============================================================
# 11. RESUMO
# ============================================================

print(
    "\n========================================"
)

print(
    "RESUMO DA BRONZE - IBGE"
)

print(
    "========================================"
)

print(
    "Registros recebidos:",
    len(registros_bronze)
)

print(
    "Hashes duplicados:",
    duplicados
)

print(
    "Load ID:",
    load_id
)

print(
    "Data de ingestao:",
    ingestion_timestamp.isoformat()
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