from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


ANO = 2024

ARQUIVO = Path(
    f"data/ml/dataset_ml_{ANO}.csv"
)


df = pd.read_csv(
    ARQUIVO
)


FEATURES_CLIMA = [
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


FEATURES_COMPLETO = [
    "incidencia_lag1"
] + FEATURES_CLIMA


TARGET = "incidencia_100mil"


train = df[
    df["split"] == "train"
].copy()


validation = df[
    df["split"] == "validation"
].copy()


def avaliar(
    nome,
    features
):

    modelo = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )


    modelo.fit(
        train[features],
        train[TARGET]
    )


    pred = modelo.predict(
        validation[features]
    )


    mae = mean_absolute_error(
        validation[TARGET],
        pred
    )


    rmse = np.sqrt(
        mean_squared_error(
            validation[TARGET],
            pred
        )
    )


    r2 = r2_score(
        validation[TARGET],
        pred
    )


    return {
        "modelo": nome,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }


resultados = []


resultados.append(
    avaliar(
        "Random Forest - clima",
        FEATURES_CLIMA
    )
)


resultados.append(
    avaliar(
        "Random Forest - clima + incidencia anterior",
        FEATURES_COMPLETO
    )
)


baseline = validation[
    "incidencia_lag1"
]


resultados.append(
    {
        "modelo": "Baseline persistencia",

        "MAE": mean_absolute_error(
            validation[TARGET],
            baseline
        ),

        "RMSE": np.sqrt(
            mean_squared_error(
                validation[TARGET],
                baseline
            )
        ),

        "R2": r2_score(
            validation[TARGET],
            baseline
        )
    }
)


resultado = pd.DataFrame(
    resultados
)


resultado = resultado.sort_values(
    "MAE"
)


print(
    "\n========================================"
)

print(
    "CONTRIBUIÇÃO DO CLIMA"
)

print(
    "========================================"
)

print(
    resultado.to_string(
        index=False
    )
)

print(
    "========================================"
)