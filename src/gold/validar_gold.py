from pathlib import Path

import pandas as pd


ANO = 2024

ARQUIVO_GOLD = Path(
    f"data/gold/dengue_clima_para_{ANO}_gold.csv"
)

ARQUIVO_SINAN = Path(
    f"data/silver/sinan/dengue_para_{ANO}_silver.csv"
)

ARQUIVO_CLIMA = Path(
    f"data/silver/nasa_power/clima_para_{ANO}_silver.csv"
)

ARQUIVO_POPULACAO = Path(
    f"data/silver/ibge/populacao_para_{ANO}_silver.csv"
)

PASTA_DOCS = Path(
    "docs"
)

PASTA_DOCS.mkdir(
    parents=True,
    exist_ok=True
)

ARQUIVO_RELATORIO = (
    PASTA_DOCS
    / f"validacao_gold_{ANO}.md"
)


for arquivo in [
    ARQUIVO_GOLD,
    ARQUIVO_SINAN,
    ARQUIVO_CLIMA,
    ARQUIVO_POPULACAO
]:

    if not arquivo.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado: {arquivo}"
        )


gold = pd.read_csv(
    ARQUIVO_GOLD,
    dtype={
        "codigo_ibge": "string",
        "competencia": "string"
    }
)

sinan = pd.read_csv(
    ARQUIVO_SINAN,
    dtype={
        "codigo_ibge": "string",
        "competencia": "string"
    }
)

clima = pd.read_csv(
    ARQUIVO_CLIMA,
    dtype={
        "codigo_ibge": "string",
        "competencia": "string"
    }
)

populacao = pd.read_csv(
    ARQUIVO_POPULACAO,
    dtype={
        "codigo_ibge": "string"
    }
)


resultados = {}


resultados["linhas_gold"] = len(
    gold
)

resultados["municipios"] = (
    gold["codigo_ibge"]
    .nunique()
)

resultados["competencias"] = (
    gold["competencia"]
    .nunique()
)

resultados["duplicatas"] = (
    gold.duplicated(
        subset=[
            "codigo_ibge",
            "competencia"
        ]
    )
    .sum()
)

resultados["valores_nulos"] = int(
    gold.isna().sum().sum()
)

resultados["populacao_invalida"] = int(
    (
        gold["populacao"] <= 0
    ).sum()
)

resultados["incidencia_negativa"] = int(
    (
        gold["incidencia_100mil"] < 0
    ).sum()
)

resultados["confirmados_maior_provaveis"] = int(
    (
        gold["casos_confirmados"]
        >
        gold["casos_provaveis"]
    ).sum()
)

resultados["provaveis_maior_notificacoes"] = int(
    (
        gold["casos_provaveis"]
        >
        gold["notificacoes"]
    ).sum()
)


resultados["temperatura_fora_faixa"] = int(
    (
        (gold["temperatura_media_c"] < -50)
        |
        (gold["temperatura_media_c"] > 60)
    ).sum()
)

resultados["umidade_fora_faixa"] = int(
    (
        (gold["umidade_media_pct"] < 0)
        |
        (gold["umidade_media_pct"] > 100)
    ).sum()
)

resultados["chuva_negativa"] = int(
    (
        gold["precipitacao_total_mm"] < 0
    ).sum()
)


casos_gold = int(
    gold["casos_provaveis"].sum()
)

casos_sinan = int(
    sinan["casos_provaveis"].sum()
)

confirmados_gold = int(
    gold["casos_confirmados"].sum()
)

confirmados_sinan = int(
    sinan["casos_confirmados"].sum()
)


resultados[
    "casos_gold"
] = casos_gold

resultados[
    "casos_sinan"
] = casos_sinan

resultados[
    "confirmados_gold"
] = confirmados_gold

resultados[
    "confirmados_sinan"
] = confirmados_sinan


resultado_esperado = {
    "linhas_gold": 1728,
    "municipios": 144,
    "competencias": 12,
    "duplicatas": 0,
    "valores_nulos": 0,
    "populacao_invalida": 0,
    "incidencia_negativa": 0,
    "confirmados_maior_provaveis": 0,
    "provaveis_maior_notificacoes": 0,
    "temperatura_fora_faixa": 0,
    "umidade_fora_faixa": 0,
    "chuva_negativa": 0
}


erros = []


for teste, esperado in resultado_esperado.items():

    encontrado = resultados[
        teste
    ]

    if encontrado != esperado:

        erros.append(
            f"{teste}: esperado {esperado}, "
            f"encontrado {encontrado}"
        )


if casos_gold != casos_sinan:

    erros.append(
        "Total de casos prováveis da Gold "
        "não bate com a Silver do SINAN."
    )


if confirmados_gold != confirmados_sinan:

    erros.append(
        "Total de casos confirmados da Gold "
        "não bate com a Silver do SINAN."
    )


if len(clima) != len(gold):

    erros.append(
        "Quantidade de linhas da Silver climática "
        "não bate com a Gold."
    )


if len(populacao) != 144:

    erros.append(
        "Tabela de população não possui "
        "144 municípios."
    )


status = (
    "APROVADA"
    if len(erros) == 0
    else "REPROVADA"
)


print(
    "\n========================================"
)

print(
    "VALIDAÇÃO FINAL DA GOLD"
)

print(
    "========================================"
)

print(
    "Status:",
    status
)

print(
    "Linhas:",
    resultados["linhas_gold"]
)

print(
    "Municípios:",
    resultados["municipios"]
)

print(
    "Competências:",
    resultados["competencias"]
)

print(
    "Duplicatas:",
    resultados["duplicatas"]
)

print(
    "Valores nulos:",
    resultados["valores_nulos"]
)

print(
    "Casos prováveis Gold/SINAN:",
    casos_gold,
    "/",
    casos_sinan
)

print(
    "Casos confirmados Gold/SINAN:",
    confirmados_gold,
    "/",
    confirmados_sinan
)


if erros:

    print(
        "\nProblemas encontrados:"
    )

    for erro in erros:

        print(
            "-",
            erro
        )

else:

    print(
        "\nNenhum problema encontrado."
    )


relatorio = f"""# Validação da Gold - {ANO}

## Status

**{status}**

## Estrutura

- Linhas: {resultados["linhas_gold"]}
- Municípios: {resultados["municipios"]}
- Competências mensais: {resultados["competencias"]}
- Duplicatas em `codigo_ibge + competencia`: {resultados["duplicatas"]}
- Valores nulos: {resultados["valores_nulos"]}

## Integridade epidemiológica

- Casos prováveis na Silver SINAN: {casos_sinan}
- Casos prováveis na Gold: {casos_gold}
- Casos confirmados na Silver SINAN: {confirmados_sinan}
- Casos confirmados na Gold: {confirmados_gold}
- Confirmados maiores que prováveis: {resultados["confirmados_maior_provaveis"]}
- Prováveis maiores que notificações: {resultados["provaveis_maior_notificacoes"]}

## Qualidade das variáveis

- População inválida: {resultados["populacao_invalida"]}
- Incidência negativa: {resultados["incidencia_negativa"]}
- Temperaturas fora da faixa de validação: {resultados["temperatura_fora_faixa"]}
- Umidade fora de 0–100%: {resultados["umidade_fora_faixa"]}
- Precipitação negativa: {resultados["chuva_negativa"]}

## Granularidade

Uma linha representa um município do Pará em uma competência mensal.

**Chave:** `codigo_ibge + competencia`

## Fontes integradas

- SINAN: casos de dengue
- NASA POWER: temperatura, umidade e precipitação
- IBGE: municípios, malha territorial e população

## Resultado

A Gold foi validada para uso nas etapas analíticas e de modelagem.
"""


if erros:

    relatorio += "\n## Problemas encontrados\n\n"

    for erro in erros:

        relatorio += (
            f"- {erro}\n"
        )


ARQUIVO_RELATORIO.write_text(
    relatorio,
    encoding="utf-8"
)


print(
    "\nRelatório criado em:"
)

print(
    ARQUIVO_RELATORIO
)

print(
    "========================================"
)