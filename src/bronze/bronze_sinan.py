import csv
import gzip
import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

ANO = 2024

SOURCE_SYSTEM = "SINAN"
SOURCE_OBJECT = f"Sinan Dengue Brasil {ANO}"

URL = (
    "https://s3.sa-east-1.amazonaws.com/"
    "ckan.saude.gov.br/SINAN/Dengue/csv/"
    f"DENGBR{str(ANO)[-2:]}.csv.zip"
)

load_id = str(uuid.uuid4())

ingestion_timestamp = datetime.now(
    timezone.utc
)

data_particao = ingestion_timestamp.strftime(
    "%Y-%m-%d"
)


# ============================================================
# 2. PASTAS
# ============================================================

pasta_base = Path(
    "data/bronze/sinan"
)

pasta_raw = (
    pasta_base
    / "raw"
    / f"ano={ANO}"
    / f"ingestion_date={data_particao}"
)

pasta_records = (
    pasta_base
    / "records"
    / f"ano={ANO}"
    / f"ingestion_date={data_particao}"
)

pasta_quarentena = Path(
    "data/quarantine/sinan"
)

pasta_raw.mkdir(
    parents=True,
    exist_ok=True
)

pasta_records.mkdir(
    parents=True,
    exist_ok=True
)

pasta_quarentena.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. RETRY + BACKOFF
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


# ============================================================
# 4. DOWNLOAD DO ARQUIVO BRUTO
# ============================================================

print("Iniciando Bronze do SINAN...")

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
    pasta_raw
    / f"DENGBR{str(ANO)[-2:]}_{load_id}.csv.zip"
)

hash_arquivo = hashlib.sha256()


try:

    with session.get(
        URL,
        stream=True,
        timeout=180
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
        "Erro ao baixar o SINAN:"
    )

    print(erro)

    raise


raw_sha256 = hash_arquivo.hexdigest()


print(
    "\nArquivo bruto salvo em:"
)

print(
    arquivo_zip
)

print(
    "SHA-256 do arquivo bruto:",
    raw_sha256
)


# ============================================================
# 5. ABRE O ZIP
# ============================================================

with zipfile.ZipFile(
    arquivo_zip,
    "r"
) as zip_sinan:

    arquivos = zip_sinan.namelist()

    csvs = [
        nome
        for nome in arquivos
        if nome.lower().endswith(
            ".csv"
        )
    ]

    if not csvs:

        raise ValueError(
            "Nenhum CSV foi encontrado no ZIP."
        )

    nome_csv = csvs[0]

    print(
        "\nCSV encontrado:"
    )

    print(
        nome_csv
    )


# ============================================================
# 6. CAMINHO DA BRONZE POR REGISTRO
# ============================================================

arquivo_bronze = (
    pasta_records
    / (
        f"DENGBR{str(ANO)[-2:]}"
        f"_bronze_{load_id}.csv.gz"
    )
)

arquivo_quarentena = (
    pasta_quarentena
    / (
        f"sinan_linhas_invalidas_"
        f"{ANO}_{load_id}.csv"
    )
)


# ============================================================
# 7. PROCESSA O CSV EM STREAMING
# ============================================================

print(
    "\nCriando registros Bronze..."
)

print(
    "Isso pode levar alguns minutos."
)


METADADOS = [
    "_ingestion_timestamp",
    "_source_system",
    "_source_object",
    "_load_id",
    "_record_hash"
]


quantidade_registros = 0
quantidade_invalidos = 0
duplicados_hash = 0

hashes_encontrados = set()


with zipfile.ZipFile(
    arquivo_zip,
    "r"
) as zip_sinan:

    with zip_sinan.open(
        nome_csv,
        "r"
    ) as arquivo_binario:

        arquivo_texto = io.TextIOWrapper(
            arquivo_binario,
            encoding="latin1",
            newline=""
        )

        leitor = csv.reader(
            arquivo_texto,
            delimiter=","
        )

        cabecalho = next(
            leitor
        )

        quantidade_colunas_originais = len(
            cabecalho
        )

        print(
            "Colunas originais:",
            quantidade_colunas_originais
        )


        # --------------------------------------------
        # ARQUIVO BRONZE
        # --------------------------------------------

        with gzip.open(
            arquivo_bronze,
            "wt",
            encoding="utf-8",
            newline=""
        ) as saida:

            escritor = csv.writer(
                saida
            )

            escritor.writerow(
                cabecalho
                + METADADOS
            )


            # ----------------------------------------
            # QUARENTENA
            # ----------------------------------------

            with arquivo_quarentena.open(
                "w",
                encoding="utf-8",
                newline=""
            ) as quarentena:

                escritor_quarentena = csv.writer(
                    quarentena
                )

                escritor_quarentena.writerow(
                    [
                        "numero_linha",
                        "motivo",
                        "quantidade_colunas",
                        "registro"
                    ]
                )


                # ------------------------------------
                # PERCORRE OS REGISTROS
                # ------------------------------------

                for numero_linha, linha in enumerate(
                    leitor,
                    start=2
                ):

                    # Validação puramente técnica.
                    # Não há regra de negócio aqui.

                    if len(linha) != quantidade_colunas_originais:

                        quantidade_invalidos += 1

                        escritor_quarentena.writerow(
                            [
                                numero_linha,
                                "quantidade_de_colunas_invalida",
                                len(linha),
                                json.dumps(
                                    linha,
                                    ensure_ascii=False
                                )
                            ]
                        )

                        continue


                    # Hash somente dos valores originais.
                    # Os metadados não participam do hash.

                    conteudo_hash = json.dumps(
                        linha,
                        ensure_ascii=False,
                        separators=(",", ":")
                    )

                    record_hash = hashlib.sha256(
                        conteudo_hash.encode(
                            "utf-8"
                        )
                    ).hexdigest()


                    if record_hash in hashes_encontrados:

                        duplicados_hash += 1

                    else:

                        hashes_encontrados.add(
                            record_hash
                        )


                    escritor.writerow(
                        linha
                        + [
                            ingestion_timestamp.isoformat(),
                            SOURCE_SYSTEM,
                            SOURCE_OBJECT,
                            load_id,
                            record_hash
                        ]
                    )


                    quantidade_registros += 1


                    # Progresso para arquivos grandes

                    if (
                        quantidade_registros
                        % 100000
                        == 0
                    ):

                        print(
                            "Registros processados:",
                            quantidade_registros
                        )


# ============================================================
# 8. REMOVE QUARENTENA VAZIA
# ============================================================

if quantidade_invalidos == 0:

    arquivo_quarentena.unlink(
        missing_ok=True
    )


# ============================================================
# 9. MANIFESTO DA CARGA
# ============================================================

manifesto = {
    "load_id": load_id,
    "ingestion_timestamp": (
        ingestion_timestamp.isoformat()
    ),
    "source_system": SOURCE_SYSTEM,
    "source_object": SOURCE_OBJECT,
    "source_url": URL,
    "ano": ANO,
    "raw_sha256": raw_sha256,
    "original_columns": (
        quantidade_colunas_originais
    ),
    "records_processed": (
        quantidade_registros
    ),
    "invalid_records": (
        quantidade_invalidos
    ),
    "duplicate_hashes_in_load": (
        duplicados_hash
    ),
    "raw_file": str(
        arquivo_zip
    ),
    "bronze_file": str(
        arquivo_bronze
    )
}


arquivo_manifesto = (
    pasta_base
    / (
        f"manifest_{ANO}_"
        f"{load_id}.json"
    )
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
# 10. RESUMO
# ============================================================

print(
    "\n========================================"
)

print(
    "RESUMO DA BRONZE - SINAN"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Colunas originais:",
    quantidade_colunas_originais
)

print(
    "Registros processados:",
    quantidade_registros
)

print(
    "Registros tecnicamente inválidos:",
    quantidade_invalidos
)

print(
    "Hashes duplicados na carga:",
    duplicados_hash
)

print(
    "Load ID:",
    load_id
)

print(
    "SHA-256 do ZIP:",
    raw_sha256
)

print(
    "Arquivo bruto:",
    arquivo_zip
)

print(
    "Arquivo Bronze:",
    arquivo_bronze
)

print(
    "Manifesto:",
    arquivo_manifesto
)

if quantidade_invalidos > 0:

    print(
        "Quarentena:",
        arquivo_quarentena
    )

else:

    print(
        "Quarentena: nenhum registro técnico inválido"
    )

print(
    "========================================"
)