# Teste inicial de ingestão de dados do SINAN
import requests
import pandas as pd

url = "https://apidadosabertos.saude.gov.br/arboviroses/dengue"

try:
    resposta = requests.get(url, timeout=30)

    print("Status da requisição:", resposta.status_code)

    resposta.raise_for_status()

    dados = resposta.json()

    print("\nTipo da resposta:")
    print(type(dados))

    if isinstance(dados, list):
        print("\nQuantidade de registros retornados:", len(dados))

        if len(dados) > 0:
            df = pd.DataFrame(dados)

            print("\nPrimeiros registros:")
            print(df.head())

            print("\nColunas encontradas:")
            print(df.columns.tolist())

    elif isinstance(dados, dict):
        print("\nChaves principais da resposta:")
        print(dados.keys())

        for chave, valor in dados.items():
            print("\nChave:", chave)

            if isinstance(valor, list):
                print("Quantidade de itens:", len(valor))

                if len(valor) > 0:
                    df = pd.DataFrame(valor)

                    print("\nPrimeiros registros:")
                    print(df.head())

                    print("\nColunas encontradas:")
                    print(df.columns.tolist())

                break

            else:
                print(valor)

    else:
        print("Formato inesperado de resposta.")

except requests.exceptions.RequestException as erro:
    print("Erro ao acessar a API do SINAN:")
    print(erro)

except ValueError as erro:
    print("A resposta não pôde ser convertida para JSON:")
    print(erro)
