from pathlib import Path

import pandas as pd


ANO = 2024

ARQUIVO = Path(
    f"data/ml/resultados/previsoes_teste_{ANO}.csv"
)

PASTA_DOCS = Path("docs")

PASTA_DOCS.mkdir(
    parents=True,
    exist_ok=True
)

ARQUIVO_RELATORIO = (
    PASTA_DOCS
    / f"analise_erros_ml_{ANO}.md"
)


if not ARQUIVO.exists():
    raise FileNotFoundError(
        "Arquivo de previsões de teste não encontrado."
    )


df = pd.read_csv(
    ARQUIVO,
    dtype={
        "codigo_ibge": "string",
        "municipio": "string",
        "competencia": "string"
    }
)


df["erro"] = (
    df["incidencia_prevista"]
    - df["incidencia_100mil"]
)


df["erro_absoluto"] = (
    df["erro"]
    .abs()
)


por_mes = (
    df
    .groupby(
        "competencia",
        as_index=False
    )
    .agg(
        observacoes=(
            "codigo_ibge",
            "count"
        ),

        incidencia_real_media=(
            "incidencia_100mil",
            "mean"
        ),

        incidencia_prevista_media=(
            "incidencia_prevista",
            "mean"
        ),

        MAE=(
            "erro_absoluto",
            "mean"
        )
    )
)


por_mes[
    "incidencia_real_media"
] = (
    por_mes[
        "incidencia_real_media"
    ].round(3)
)

por_mes[
    "incidencia_prevista_media"
] = (
    por_mes[
        "incidencia_prevista_media"
    ].round(3)
)

por_mes["MAE"] = (
    por_mes["MAE"]
    .round(3)
)


por_municipio = (
    df
    .groupby(
        [
            "codigo_ibge",
            "municipio"
        ],
        as_index=False
    )
    .agg(
        MAE=(
            "erro_absoluto",
            "mean"
        ),

        erro_medio=(
            "erro",
            "mean"
        )
    )
)


por_municipio = (
    por_municipio
    .sort_values(
        "MAE",
        ascending=False
    )
)


piores = (
    df
    .sort_values(
        "erro_absoluto",
        ascending=False
    )
    [
        [
            "municipio",
            "competencia",
            "incidencia_100mil",
            "incidencia_prevista",
            "erro",
            "erro_absoluto"
        ]
    ]
    .head(15)
)


superestimacoes = int(
    (df["erro"] > 0).sum()
)

subestimacoes = int(
    (df["erro"] < 0).sum()
)

acertos_exatos = int(
    (df["erro"] == 0).sum()
)


print(
    "\n========================================"
)

print(
    "ANÁLISE DE ERROS - MODELO FINAL"
)

print(
    "========================================"
)

print(
    "Observações de teste:",
    len(df)
)

print(
    "Superestimações:",
    superestimacoes
)

print(
    "Subestimações:",
    subestimacoes
)

print(
    "Acertos exatos:",
    acertos_exatos
)


print(
    "\nErro por mês:"
)

print(
    por_mes.to_string(
        index=False
    )
)


print(
    "\n15 maiores erros:"
)

print(
    piores.to_string(
        index=False
    )
)


print(
    "\nMunicípios com maior MAE:"
)

print(
    por_municipio.head(
        15
    ).to_string(
        index=False
    )
)


relatorio = f"""# Análise de erros do modelo - {ANO}

## Modelo selecionado

Baseline de persistência.

A previsão considera que a incidência do mês seguinte será igual à incidência observada no mês anterior.

## Conjunto de teste

- Observações: {len(df)}
- Superestimações: {superestimacoes}
- Subestimações: {subestimacoes}
- Acertos exatos: {acertos_exatos}

## Erro por competência

{por_mes.to_markdown(index=False)}

## Maiores erros individuais

{piores.to_markdown(index=False)}

## Municípios com maior erro médio

{por_municipio.head(15).to_markdown(index=False)}

## Interpretação

O baseline de persistência superou os modelos de Regressão Linear e Random Forest na validação temporal.

Isso indica que, com apenas os dados de 2024, a persistência temporal da incidência de dengue apresenta maior poder preditivo do que as variáveis climáticas utilizadas no experimento.

Os resultados não demonstram que fatores climáticos sejam irrelevantes. A análise de correlação mostrou associações, especialmente para precipitação com defasagem de um mês. Entretanto, essas relações não foram suficientes para superar o histórico recente da própria incidência na tarefa preditiva atual.

Uma limitação importante é a disponibilidade de apenas um ciclo anual para treinamento e avaliação temporal.
"""


ARQUIVO_RELATORIO.write_text(
    relatorio,
    encoding="utf-8"
)


print(
    "\nRelatório criado:"
)

print(
    ARQUIVO_RELATORIO
)

print(
    "========================================"
)