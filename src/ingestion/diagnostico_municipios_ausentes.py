from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

arquivo_sinan = Path(
    "data/sinan/2024/DENGBR24.csv"
)

municipios_ausentes = {
    "150100": "Aveiro",
    "150160": "Bonito",
    "150276": "Cumaru do Norte",
    "150563": "Piçarra",
    "150640": "Santa Cruz do Arari",
    "150745": "São Geraldo do Araguaia"
}


# ============================================================
# 2. COLUNAS NECESSÁRIAS
# ============================================================

colunas = [
    "SG_UF",
    "ID_MN_RESI",
    "DT_SIN_PRI",
    "CLASSI_FIN"
]


# ============================================================
# 3. LEITURA DO SINAN
# ============================================================

print("Lendo SINAN 2024...")

df = pd.read_csv(
    arquivo_sinan,
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


# ============================================================
# 4. PADRONIZAÇÃO
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

df["DT_SIN_PRI"] = pd.to_datetime(
    df["DT_SIN_PRI"],
    errors="coerce",
    dayfirst=True
)


# ============================================================
# 5. FILTRA PARÁ
# ============================================================

df_pa = df[
    df["SG_UF"] == "15"
].copy()


# ============================================================
# 6. ANALISA CADA MUNICÍPIO AUSENTE
# ============================================================

resultados = []

for codigo, nome in municipios_ausentes.items():

    dados_municipio = df_pa[
        df_pa["ID_MN_RESI"] == codigo
    ].copy()

    total_notificacoes = len(
        dados_municipio
    )

    casos_dengue = dados_municipio[
        dados_municipio["CLASSI_FIN"].isin(
            [10, 11, 12]
        )
    ]

    total_dengue = len(
        casos_dengue
    )

    dengue_com_data = (
        casos_dengue[
            casos_dengue[
                "DT_SIN_PRI"
            ].notna()
        ]
    )

    total_dengue_com_data = len(
        dengue_com_data
    )

    classificacao_ausente = (
        dados_municipio[
            "CLASSI_FIN"
        ]
        .isna()
        .sum()
    )

    resultados.append(
        {
            "codigo": codigo,
            "municipio": nome,
            "notificacoes_totais": total_notificacoes,
            "casos_dengue": total_dengue,
            "dengue_com_data_valida": total_dengue_com_data,
            "classificacao_ausente": classificacao_ausente
        }
    )


# ============================================================
# 7. RESULTADO
# ============================================================

resultado = pd.DataFrame(
    resultados
)

print("\n==========================================")
print("DIAGNÓSTICO DOS MUNICÍPIOS AUSENTES")
print("==========================================")

print(
    resultado.to_string(
        index=False
    )
)


# ============================================================
# 8. CLASSIFICAÇÕES ENCONTRADAS
# ============================================================

for codigo, nome in municipios_ausentes.items():

    dados_municipio = df_pa[
        df_pa["ID_MN_RESI"] == codigo
    ]

    print(
        f"\nClassificações encontradas em {nome}:"
    )

    print(
        dados_municipio[
            "CLASSI_FIN"
        ]
        .value_counts(
            dropna=False
        )
        .sort_index()
    )