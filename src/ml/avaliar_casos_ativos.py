from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
import numpy as np


ANO = 2024

ARQUIVO = Path(
    f"data/ml/resultados/previsoes_teste_{ANO}.csv"
)


if not ARQUIVO.exists():
    raise FileNotFoundError(
        "Arquivo de previsões não encontrado."
    )


df = pd.read_csv(
    ARQUIVO
)


REAL = "incidencia_100mil"
PREV = "incidencia_prevista"


def metricas(
    dados,
    nome
):

    if len(dados) == 0:

        return {
            "grupo": nome,
            "observacoes": 0,
            "MAE": None,
            "RMSE": None,
            "R2": None
        }


    mae = mean_absolute_error(
        dados[REAL],
        dados[PREV]
    )


    rmse = np.sqrt(
        mean_squared_error(
            dados[REAL],
            dados[PREV]
        )
    )


    if len(dados) > 1:

        r2 = r2_score(
            dados[REAL],
            dados[PREV]
        )

    else:

        r2 = None


    return {
        "grupo": nome,
        "observacoes": len(dados),
        "MAE": round(
            mae,
            3
        ),
        "RMSE": round(
            rmse,
            3
        ),
        "R2": (
            round(
                r2,
                4
            )
            if r2 is not None
            else None
        )
    }


resultado = []


resultado.append(
    metricas(
        df,
        "Todos"
    )
)


resultado.append(
    metricas(
        df[
            df[REAL] == 0
        ],
        "Incidencia zero"
    )
)


resultado.append(
    metricas(
        df[
            df[REAL] > 0
        ],
        "Incidencia maior que zero"
    )
)


resultado.append(
    metricas(
        df[
            df[REAL] >= 50
        ],
        "Incidencia >= 50 por 100 mil"
    )
)


resultado.append(
    metricas(
        df[
            df[REAL] >= 100
        ],
        "Incidencia >= 100 por 100 mil"
    )
)


tabela = pd.DataFrame(
    resultado
)


zeros_reais = int(
    (
        df[REAL] == 0
    ).sum()
)


zeros_previstos = int(
    (
        df[PREV] == 0
    ).sum()
)


zero_zero = int(
    (
        (df[REAL] == 0)
        &
        (df[PREV] == 0)
    ).sum()
)


grandes_erros = df[
    (
        df[REAL]
        -
        df[PREV]
    ).abs() >= 50
].copy()


print(
    "\n========================================"
)

print(
    "AVALIAÇÃO EM CASOS ATIVOS"
)

print(
    "========================================"
)


print(
    "\nMétricas por grupo:"
)

print(
    tabela.to_string(
        index=False
    )
)


print(
    "\nDiagnóstico de zeros:"
)

print(
    "Incidência real zero:",
    zeros_reais
)

print(
    "Previsão zero:",
    zeros_previstos
)

print(
    "Real zero e previsão zero:",
    zero_zero
)


print(
    "\nErros absolutos >= 50 por 100 mil:",
    len(grandes_erros)
)


if not grandes_erros.empty:

    print(
        "\nMaiores erros:"
    )

    print(
        grandes_erros[
            [
                "municipio",
                "competencia",
                REAL,
                PREV,
                "erro_absoluto"
            ]
        ]
        .sort_values(
            "erro_absoluto",
            ascending=False
        )
        .head(
            15
        )
        .to_string(
            index=False
        )
    )


print(
    "========================================"
)