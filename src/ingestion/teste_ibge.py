# Teste inicial de ingestão da API do IBGE
import requests
import pandas as pd

# URL da API do IBGE para listar os municípios do Pará
url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/15/municipios"

# Faz a requisição para a API
resposta = requests.get(url)

# Verifica se a requisição funcionou
if resposta.status_code == 200:
    dados = resposta.json()

    # Seleciona apenas algumas informações importantes
    municipios = []

    for municipio in dados:
        municipios.append({
            "codigo_ibge": municipio["id"],
            "municipio": municipio["nome"]
        })

    # Converte para DataFrame
    df = pd.DataFrame(municipios)

    print("Ingestão realizada com sucesso!")
    print()
    print(df.head())
    print()
    print("Quantidade de municípios encontrados:", len(df))

else:
    print("Erro na requisição.")
    print("Código do erro:", resposta.status_code)
