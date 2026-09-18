import io
import zipfile
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

url_sinan = (
    "https://s3.sa-east-1.amazonaws.com/"
    "ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR24.csv.zip"
)

url_ibge = (
    "https://servicodados.ibge.gov.br/"
    "api/v1/localidades/estados/15/municipios"
)

pasta_sinan = Path("data/sinan/2024")
pasta_sinan.mkdir(parents=True, exist_ok=True)

pasta_saida = Path("data/silver/sinan")
pasta_saida.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. DOWNLOAD DO SINAN
# ============================================================

print("Baixando SINAN Dengue 2024...")

resposta = requests.get(
    url_sinan,
    timeout=180
)

print("Status da requisição:", resposta.status_code)

resposta.raise_for_status()

print("Download concluído.")

tamanho_mb = len(resposta.content) / 1024 / 1024

print(
    "Tamanho do arquivo:",
    round(tamanho_mb, 2),
    "MB"
)


# ============================================================
# 3. EXTRAÇÃO DO ZIP
# ============================================================

with zipfile.ZipFile(
    io.BytesIO(resposta.content)
) as arquivo_zip:

    arquivos = arquivo_zip.namelist()

    print("\nArquivos dentro do ZIP:")
    print(arquivos)

    nome_csv = next(
        nome
        for nome in arquivos
        if nome.lower().endswith(".csv")
    )

    arquivo_zip.extract(
        nome_csv,
        pasta_sinan
    )


caminho_csv = pasta_sinan / nome_csv

print("\nArquivo extraído:")
print(caminho_csv)


# ============================================================
# 4. COLUNAS UTILIZADAS
# ============================================================

colunas = [
    "SG_UF",
    "ID_MN_RESI",
    "DT_SIN_PRI",
    "CLASSI_FIN"
]


# ============================================================
# 5. LEITURA DO CSV
# ============================================================

print("\nLendo dados do SINAN...")

df = pd.read_csv(
    caminho_csv,
    sep=",",
    encoding="latin1",
    usecols=colunas,
    dtype={
        "SG_UF": "string",
        "ID_MN_RESI": "string",
        "CLASSI_FIN": "string"
    },
    low_memory=False
)

print("\nLeitura concluída.")

print(
    "Quantidade total de registros:",
    len(df)
)


# ============================================================
# 6. PADRONIZAÇÃO
# ============================================================

df["SG_UF"] = (
    df["SG_UF"]
    .str.strip()
    .str.zfill(2)
)

df["ID_MN_RESI"] = (
    df["ID_MN_RESI"]
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(6)
)

df["CLASSI_FIN"] = pd.to_numeric(
    df["CLASSI_FIN"],
    errors="coerce"
)


# ============================================================
# 7. FILTRA RESIDENTES DO PARÁ
# ============================================================

# Código da UF do Pará = 15

df_pa = df[
    df["SG_UF"] == "15"
].copy()

print(
    "\nRegistros de residentes do Pará:",
    len(df_pa)
)


# ============================================================
# 8. FILTRA CASOS CLASSIFICADOS COMO DENGUE
# ============================================================

# 10 = Dengue
# 11 = Dengue com sinais de alarme
# 12 = Dengue grave

classificacoes_dengue = [
    10,
    11,
    12
]

df_pa = df_pa[
    df_pa["CLASSI_FIN"].isin(
        classificacoes_dengue
    )
].copy()

print(
    "Casos classificados como dengue no Pará:",
    len(df_pa)
)


# ============================================================
# 9. CONVERSÃO DA DATA
# ============================================================

df_pa["DT_SIN_PRI"] = pd.to_datetime(
    df_pa["DT_SIN_PRI"],
    errors="coerce",
    dayfirst=True
)


# ============================================================
# 10. VERIFICAÇÃO DE DADOS AUSENTES
# ============================================================

municipios_ausentes = (
    df_pa["ID_MN_RESI"]
    .isna()
    .sum()
)

datas_ausentes = (
    df_pa["DT_SIN_PRI"]
    .isna()
    .sum()
)

print(
    "\nMunicípio de residência ausente:",
    municipios_ausentes
)

print(
    "Data de início dos sintomas ausente:",
    datas_ausentes
)


# ============================================================
# 11. REMOVE REGISTROS INUTILIZÁVEIS
# ============================================================

df_pa = df_pa.dropna(
    subset=[
        "ID_MN_RESI",
        "DT_SIN_PRI"
    ]
).copy()


# ============================================================
# 12. CRIA COMPETÊNCIA
# ============================================================

df_pa["competencia"] = (
    df_pa["DT_SIN_PRI"]
    .dt.to_period("M")
    .astype("string")
)


# ============================================================
# 13. AGREGA CASOS POR MUNICÍPIO E MÊS
# ============================================================

casos_mensais = (
    df_pa
    .groupby(
        [
            "ID_MN_RESI",
            "competencia"
        ]
    )
    .size()
    .reset_index(
        name="casos_dengue"
    )
)

casos_mensais = (
    casos_mensais
    .sort_values(
        [
            "ID_MN_RESI",
            "competencia"
        ]
    )
    .reset_index(drop=True)
)


print(
    "\nRegistros mensais gerados:",
    len(casos_mensais)
)

print(
    "Municípios presentes no SINAN:",
    casos_mensais["ID_MN_RESI"].nunique()
)


# ============================================================
# 14. SALVA RESULTADO MENSAL
# ============================================================

caminho_saida = (
    pasta_saida
    / "dengue_para_2024_mensal.csv"
)

casos_mensais.to_csv(
    caminho_saida,
    index=False,
    encoding="utf-8"
)

print(
    "\nArquivo mensal salvo em:"
)

print(caminho_saida)


# ============================================================
# 15. CONSULTA MUNICÍPIOS DO IBGE
# ============================================================

print("\nConsultando municípios do Pará no IBGE...")

resposta_ibge = requests.get(
    url_ibge,
    timeout=30
)

resposta_ibge.raise_for_status()

dados_ibge = resposta_ibge.json()

municipios_ibge = []

for municipio in dados_ibge:

    codigo_7 = str(
        municipio["id"]
    )

    municipios_ibge.append(
        {
            "codigo_ibge": codigo_7,
            "codigo_ibge_6": codigo_7[:6],
            "municipio": municipio["nome"]
        }
    )


df_ibge = pd.DataFrame(
    municipios_ibge
)

print(
    "Municípios encontrados no IBGE:",
    len(df_ibge)
)


# ============================================================
# 16. COMPARA CÓDIGOS DO SINAN COM IBGE
# ============================================================

codigos_sinan = set(
    casos_mensais[
        "ID_MN_RESI"
    ].astype(str)
)

codigos_ibge = set(
    df_ibge[
        "codigo_ibge_6"
    ].astype(str)
)


# Municípios existentes no IBGE
# que não apareceram no SINAN
codigos_ausentes = (
    codigos_ibge
    - codigos_sinan
)

municipios_sem_casos = (
    df_ibge[
        df_ibge[
            "codigo_ibge_6"
        ].isin(
            codigos_ausentes
        )
    ]
    .sort_values("municipio")
)


print("\n====================================")
print("MUNICÍPIOS AUSENTES NO SINAN")
print("====================================")

print(
    municipios_sem_casos[
        [
            "codigo_ibge",
            "codigo_ibge_6",
            "municipio"
        ]
    ]
)

print(
    "\nQuantidade de municípios ausentes:",
    len(municipios_sem_casos)
)


# ============================================================
# 17. VERIFICA CÓDIGOS DO SINAN NÃO ENCONTRADOS NO IBGE
# ============================================================

codigos_desconhecidos = (
    codigos_sinan
    - codigos_ibge
)

print(
    "\nCódigos do SINAN não encontrados no IBGE:"
)

print(
    sorted(
        codigos_desconhecidos
    )
)

print(
    "Quantidade:",
    len(codigos_desconhecidos)
)


# ============================================================
# 18. JUNTA NOME DO MUNICÍPIO AOS CASOS
# ============================================================

resultado = casos_mensais.merge(
    df_ibge[
        [
            "codigo_ibge",
            "codigo_ibge_6",
            "municipio"
        ]
    ],
    left_on="ID_MN_RESI",
    right_on="codigo_ibge_6",
    how="left"
)


resultado = resultado[
    [
        "codigo_ibge",
        "municipio",
        "competencia",
        "casos_dengue"
    ]
]


# ============================================================
# 19. SALVA RESULTADO COM MUNICÍPIO
# ============================================================

arquivo_resultado = (
    pasta_saida
    / "dengue_para_2024_mensal_ibge.csv"
)

resultado.to_csv(
    arquivo_resultado,
    index=False,
    encoding="utf-8"
)


# ============================================================
# 20. SALVA LISTA DOS MUNICÍPIOS AUSENTES
# ============================================================

arquivo_ausentes = (
    pasta_saida
    / "municipios_ausentes_sinan_2024.csv"
)

municipios_sem_casos.to_csv(
    arquivo_ausentes,
    index=False,
    encoding="utf-8"
)


# ============================================================
# 21. RESUMO FINAL
# ============================================================

print("\n====================================")
print("RESUMO FINAL")
print("====================================")

print(
    "Registros totais do SINAN:",
    len(df)
)

print(
    "Casos de dengue válidos do Pará:",
    len(df_pa)
)

print(
    "Registros município/mês:",
    len(casos_mensais)
)

print(
    "Municípios presentes no SINAN:",
    casos_mensais[
        "ID_MN_RESI"
    ].nunique()
)

print(
    "Municípios oficiais do Pará:",
    len(df_ibge)
)

print(
    "Municípios sem casos encontrados:",
    len(municipios_sem_casos)
)

print(
    "Códigos SINAN não reconhecidos:",
    len(codigos_desconhecidos)
)

print("====================================")

print(
    "\nResultado final salvo em:"
)

print(
    arquivo_resultado
)