import csv
import gzip
import hashlib
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

SOURCE_SYSTEM = "INMET"
SOURCE_OBJECT = f"Dados Historicos INMET {ANO}"

URL = (
    f"https://portal.inmet.gov.br/"
    f"uploads/dadoshistoricos/{ANO}.zip"
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
    "data/bronze/inmet"
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
    "data/quarantine/inmet"
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
# 4. DOWNLOAD DO ZIP
# ============================================================

print("Iniciando Bronze do INMET...")

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
    / f"INMET_{ANO}_{load_id}.zip"
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
        "Erro ao baixar dados do INMET:"
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
    "SHA-256 do ZIP:",
    raw_sha256
)


# ============================================================
# 5. LISTA ARQUIVOS DO ZIP
# ============================================================

with zipfile.ZipFile(
    arquivo_zip,
    "r"
) as zip_inmet:

    arquivos_csv = [
        nome
        for nome in zip_inmet.namelist()
        if nome.lower().endswith(".csv")
    ]


print(
    "\nArquivos CSV encontrados:",
    len(arquivos_csv)
)


# ============================================================
# 6. QUARENTENA
# ============================================================

arquivo_quarentena = (
    pasta_quarentena
    / f"inmet_linhas_invalidas_{ANO}_{load_id}.csv"
)

quarentena = arquivo_quarentena.open(
    "w",
    encoding="utf-8",
    newline=""
)

escritor_quarentena = csv.writer(
    quarentena
)

escritor_quarentena.writerow(
    [
        "source_file",
        "numero_linha",
        "motivo",
        "quantidade_colunas",
        "registro"
    ]
)


# ============================================================
# 7. PROCESSA CADA ESTAÇÃO
# ============================================================

total_registros = 0
total_invalidos = 0
arquivos_processados = 0

manifesto_arquivos = []


with zipfile.ZipFile(
    arquivo_zip,
    "r"
) as zip_inmet:

    for indice, nome_arquivo in enumerate(
        arquivos_csv,
        start=1
    ):

        print(
            f"[{indice}/{len(arquivos_csv)}] "
            f"{nome_arquivo}"
        )

        with zip_inmet.open(
            nome_arquivo,
            "r"
        ) as arquivo_binario:

            # O INMET usa latin1 nos históricos
            linhas = (
                linha.decode(
                    "latin1"
                )
                for linha in arquivo_binario
            )

            # As oito primeiras linhas são
            # metadados da estação.
            metadados_estacao = []

            for _ in range(8):

                try:

                    metadados_estacao.append(
                        next(linhas).rstrip(
                            "\r\n"
                        )
                    )

                except StopIteration:

                    break


            try:

                linha_cabecalho = next(
                    linhas
                )

            except StopIteration:

                total_invalidos += 1

                escritor_quarentena.writerow(
                    [
                        nome_arquivo,
                        0,
                        "arquivo_sem_cabecalho",
                        0,
                        ""
                    ]
                )

                continue


            leitor_cabecalho = csv.reader(
                [linha_cabecalho],
                delimiter=";"
            )

            cabecalho = next(
                leitor_cabecalho
            )

            quantidade_colunas = len(
                cabecalho
            )


            # --------------------------------------------
            # ARQUIVO BRONZE DA ESTAÇÃO
            # --------------------------------------------

            nome_seguro = (
                Path(nome_arquivo)
                .stem
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
            )

            arquivo_saida = (
                pasta_records
                / (
                    f"{nome_seguro}_"
                    f"{load_id}.csv.gz"
                )
            )


            METADADOS_TECNICOS = [
                "_ingestion_timestamp",
                "_source_system",
                "_source_object",
                "_source_file",
                "_load_id",
                "_record_hash"
            ]


            quantidade_estacao = 0
            invalidos_estacao = 0


            with gzip.open(
                arquivo_saida,
                "wt",
                encoding="utf-8",
                newline=""
            ) as saida:

                escritor = csv.writer(
                    saida
                )

                escritor.writerow(
                    cabecalho
                    + METADADOS_TECNICOS
                )


                leitor = csv.reader(
                    linhas,
                    delimiter=";"
                )


                for numero_linha, linha in enumerate(
                    leitor,
                    start=10
                ):

                    # Validação apenas estrutural/técnica.
                    if len(linha) != quantidade_colunas:

                        invalidos_estacao += 1
                        total_invalidos += 1

                        escritor_quarentena.writerow(
                            [
                                nome_arquivo,
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


                    escritor.writerow(
                        linha
                        + [
                            ingestion_timestamp.isoformat(),
                            SOURCE_SYSTEM,
                            SOURCE_OBJECT,
                            nome_arquivo,
                            load_id,
                            record_hash
                        ]
                    )


                    quantidade_estacao += 1
                    total_registros += 1


            arquivos_processados += 1


            manifesto_arquivos.append(
                {
                    "source_file": nome_arquivo,
                    "station_metadata": metadados_estacao,
                    "original_columns": quantidade_colunas,
                    "records_processed": quantidade_estacao,
                    "invalid_records": invalidos_estacao,
                    "bronze_file": str(
                        arquivo_saida
                    )
                }
            )


# ============================================================
# 8. FECHA QUARENTENA
# ============================================================

quarentena.close()


if total_invalidos == 0:

    arquivo_quarentena.unlink(
        missing_ok=True
    )


# ============================================================
# 9. MANIFESTO GERAL
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
    "csv_files_found": len(
        arquivos_csv
    ),
    "files_processed": (
        arquivos_processados
    ),
    "records_processed": (
        total_registros
    ),
    "invalid_records": (
        total_invalidos
    ),
    "raw_file": str(
        arquivo_zip
    ),
    "files": manifesto_arquivos
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
    "RESUMO DA BRONZE - INMET"
)

print(
    "========================================"
)

print(
    "Ano:",
    ANO
)

print(
    "Arquivos CSV encontrados:",
    len(arquivos_csv)
)

print(
    "Arquivos processados:",
    arquivos_processados
)

print(
    "Registros processados:",
    total_registros
)

print(
    "Registros tecnicamente inválidos:",
    total_invalidos
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
    "Manifesto:",
    arquivo_manifesto
)

if total_invalidos > 0:

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