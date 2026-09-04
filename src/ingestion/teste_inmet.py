# Teste inicial de ingestão de dados do INMET
import requests
import zipfile
import io
import pandas as pd
from pathlib import Path


# Arquivo oficial de dados históricos do INMET - 2025
url = "https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip"

# Pasta local para os dados
pasta_destino = Path("data/inmet/2025")
pasta_destino.mkdir(parents=True, exist_ok=True)

print("Baixando arquivo do INMET...")

resposta = requests.get(url, timeout=120)
print("Status da requisição:", resposta.status_code)

resposta.raise_for_status()

print("Download concluído.")
print("Tamanho do arquivo:", round(len(resposta.content) / 1024 / 1024, 2), "MB")


# Abre o ZIP diretamente em memória
with zipfile.ZipFile(io.BytesIO(resposta.content)) as zip_inmet:

    arquivos = zip_inmet.namelist()

    print("\nQuantidade de arquivos no ZIP:", len(arquivos))

    # Procura arquivos de estações do Pará
    arquivos_para = [
        arquivo
        for arquivo in arquivos
        if "_PA_" in arquivo.upper() and arquivo.upper().endswith(".CSV")
    ]

    print("Arquivos encontrados do Pará:", len(arquivos_para))

    if len(arquivos_para) == 0:
        print("Nenhum arquivo do Pará foi encontrado.")
        exit()

    # Usa a primeira estação apenas para o teste inicial
    primeiro_arquivo = arquivos_para[0]

    print("\nArquivo escolhido para teste:")
    print(primeiro_arquivo)

    zip_inmet.extract(primeiro_arquivo, pasta_destino)


caminho_csv = pasta_destino / primeiro_arquivo

# Dados do INMET usam ; como separador
# As primeiras linhas contêm metadados da estação
df = pd.read_csv(
    caminho_csv,
    sep=";",
    encoding="latin1",
    skiprows=8,
    decimal=","
)

print("\nIngestão do CSV realizada com sucesso!")

print("\nPrimeiros registros:")
print(df.head())

print("\nQuantidade de linhas:", len(df))

print("\nColunas encontradas:")
print(df.columns.tolist())
