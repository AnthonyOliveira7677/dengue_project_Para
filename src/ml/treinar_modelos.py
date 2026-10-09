import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ANO = 2024

ARQUIVO_DATASET = Path(
    f"data/ml/dataset_ml_{ANO}.csv"
)

PASTA_RESULTADOS = Path(
    "data/ml/resultados"
)

PASTA_RESULTADOS.mkdir(
    parents=True,
    exist_ok=True
)

ARQUIVO_RESULTADOS = (
    PASTA_RESULTADOS
    / f"comparacao_modelos_{ANO}.csv"
)

ARQUIVO_PREVISOES = (
    PASTA_RESULTADOS
    / f"previsoes_teste_{ANO}.csv"
)

ARQUIVO_RESUMO = (
    PASTA_RESULTADOS
    / f"resumo_modelos_{ANO}.json"
)

ARQUIVO_IMPORTANCIAS = (
    PASTA_RESULTADOS
    / f"importancia_features_{ANO}.csv"
)


FEATURES = [
    "incidencia_lag1",

    "precipitacao_total_mm_lag1",
    "precipitacao_total_mm_lag2",

    "temperatura_media_c_lag1",
    "temperatura_media_c_lag2",

    "umidade_media_pct_lag1",
    "umidade_media_pct_lag2",

    "log_populacao",

    "mes_sin",
    "mes_cos"
]

TARGET = "incidencia_100mil"


if not ARQUIVO_DATASET.exists():
    raise FileNotFoundError(
        "Dataset de ML não encontrado."
    )


df = pd.read_csv(
    ARQUIVO_DATASET,
    dtype={
        "codigo_ibge": "string",
        "municipio": "string",
        "competencia": "string",
        "split": "string"
    }
)


train = df[
    df["split"] == "train"
].copy()

validation = df[
    df["split"] == "validation"
].copy()

test = df[
    df["split"] == "test"
].copy()


print(
    "Treino:",
    len(train)
)

print(
    "Validação:",
    len(validation)
)

print(
    "Teste:",
    len(test)
)


X_train = train[
    FEATURES
]

y_train = train[
    TARGET
]


X_validation = validation[
    FEATURES
]

y_validation = validation[
    TARGET
]


X_test = test[
    FEATURES
]

y_test = test[
    TARGET
]


def calcular_metricas(
    y_real,
    y_pred
):

    mae = mean_absolute_error(
        y_real,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_real,
            y_pred
        )
    )

    r2 = r2_score(
        y_real,
        y_pred
    )

    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2)
    }


resultados_validacao = []


pred_baseline_validation = validation[
    "incidencia_lag1"
].to_numpy()


metricas_baseline = calcular_metricas(
    y_validation,
    pred_baseline_validation
)


resultados_validacao.append(
    {
        "modelo": "Baseline Persistencia",
        **metricas_baseline
    }
)


modelo_linear = Pipeline(
    [
        (
            "scaler",
            StandardScaler()
        ),

        (
            "modelo",
            LinearRegression()
        )
    ]
)


modelo_linear.fit(
    X_train,
    y_train
)


pred_linear_validation = modelo_linear.predict(
    X_validation
)


metricas_linear = calcular_metricas(
    y_validation,
    pred_linear_validation
)


resultados_validacao.append(
    {
        "modelo": "Regressao Linear",
        **metricas_linear
    }
)


modelo_rf = RandomForestRegressor(
    n_estimators=300,
    max_depth=8,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1
)


modelo_rf.fit(
    X_train,
    y_train
)


pred_rf_validation = modelo_rf.predict(
    X_validation
)


metricas_rf = calcular_metricas(
    y_validation,
    pred_rf_validation
)


resultados_validacao.append(
    {
        "modelo": "Random Forest",
        **metricas_rf
    }
)


comparacao = pd.DataFrame(
    resultados_validacao
)


comparacao = comparacao.sort_values(
    "MAE",
    ascending=True
).reset_index(
    drop=True
)


print(
    "\n========================================"
)

print(
    "RESULTADOS - VALIDACAO"
)

print(
    "========================================"
)

print(
    comparacao.to_string(
        index=False
    )
)


melhor_modelo_nome = comparacao.iloc[
    0
][
    "modelo"
]


print(
    "\nMelhor modelo pela validação:",
    melhor_modelo_nome
)


if melhor_modelo_nome == "Baseline Persistencia":

    pred_test = test[
        "incidencia_lag1"
    ].to_numpy()

    melhor_modelo = None


elif melhor_modelo_nome == "Regressao Linear":

    treino_final = pd.concat(
        [
            train,
            validation
        ],
        ignore_index=True
    )

    X_treino_final = treino_final[
        FEATURES
    ]

    y_treino_final = treino_final[
        TARGET
    ]

    melhor_modelo = Pipeline(
        [
            (
                "scaler",
                StandardScaler()
            ),

            (
                "modelo",
                LinearRegression()
            )
        ]
    )

    melhor_modelo.fit(
        X_treino_final,
        y_treino_final
    )

    pred_test = melhor_modelo.predict(
        X_test
    )


else:

    treino_final = pd.concat(
        [
            train,
            validation
        ],
        ignore_index=True
    )

    X_treino_final = treino_final[
        FEATURES
    ]

    y_treino_final = treino_final[
        TARGET
    ]

    melhor_modelo = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )

    melhor_modelo.fit(
        X_treino_final,
        y_treino_final
    )

    pred_test = melhor_modelo.predict(
        X_test
    )


metricas_teste = calcular_metricas(
    y_test,
    pred_test
)


print(
    "\n========================================"
)

print(
    "RESULTADO FINAL - TESTE"
)

print(
    "========================================"
)

print(
    "Modelo:",
    melhor_modelo_nome
)

print(
    "MAE:",
    round(
        metricas_teste["MAE"],
        3
    )
)

print(
    "RMSE:",
    round(
        metricas_teste["RMSE"],
        3
    )
)

print(
    "R²:",
    round(
        metricas_teste["R2"],
        4
    )
)


previsoes = test[
    [
        "codigo_ibge",
        "municipio",
        "competencia",
        TARGET
    ]
].copy()


previsoes[
    "incidencia_prevista"
] = pred_test


previsoes[
    "erro_absoluto"
] = (
    previsoes[
        TARGET
    ]
    -
    previsoes[
        "incidencia_prevista"
    ]
).abs()


previsoes[
    "incidencia_prevista"
] = (
    previsoes[
        "incidencia_prevista"
    ]
    .clip(
        lower=0
    )
    .round(
        3
    )
)


previsoes[
    "erro_absoluto"
] = (
    previsoes[
        "erro_absoluto"
    ]
    .round(
        3
    )
)


previsoes.to_csv(
    ARQUIVO_PREVISOES,
    index=False,
    encoding="utf-8"
)


comparacao.to_csv(
    ARQUIVO_RESULTADOS,
    index=False,
    encoding="utf-8"
)


if (
    melhor_modelo_nome
    == "Random Forest"
):

    importancias = pd.DataFrame(
        {
            "feature": FEATURES,

            "importancia": (
                melhor_modelo
                .feature_importances_
            )
        }
    )

    importancias = (
        importancias
        .sort_values(
            "importancia",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    importancias[
        "importancia"
    ] = (
        importancias[
            "importancia"
        ]
        .round(
            4
        )
    )


    importancias.to_csv(
        ARQUIVO_IMPORTANCIAS,
        index=False,
        encoding="utf-8"
    )


    print(
        "\nImportância das features:"
    )

    print(
        importancias.to_string(
            index=False
        )
    )


resumo = {
    "ano": ANO,

    "features": FEATURES,

    "target": TARGET,

    "treino_linhas": int(
        len(train)
    ),

    "validacao_linhas": int(
        len(validation)
    ),

    "teste_linhas": int(
        len(test)
    ),

    "melhor_modelo_validacao": (
        melhor_modelo_nome
    ),

    "metricas_teste": {
        "MAE": round(
            metricas_teste["MAE"],
            4
        ),

        "RMSE": round(
            metricas_teste["RMSE"],
            4
        ),

        "R2": round(
            metricas_teste["R2"],
            4
        )
    }
}


with ARQUIVO_RESUMO.open(
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        resumo,
        arquivo,
        ensure_ascii=False,
        indent=4
    )


print(
    "\nArquivos gerados:"
)

print(
    "-",
    ARQUIVO_RESULTADOS
)

print(
    "-",
    ARQUIVO_PREVISOES
)

print(
    "-",
    ARQUIVO_RESUMO
)

if (
    melhor_modelo_nome
    == "Random Forest"
):

    print(
        "-",
        ARQUIVO_IMPORTANCIAS
    )