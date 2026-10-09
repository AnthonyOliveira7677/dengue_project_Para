# Análise de erros do modelo - 2024

## Modelo selecionado

Baseline de persistência.

A previsão considera que a incidência do mês seguinte será igual à incidência observada no mês anterior.

## Conjunto de teste

- Observações: 288
- Superestimações: 75
- Subestimações: 75
- Acertos exatos: 138

## Erro por competência

| competencia   |   observacoes |   incidencia_real_media |   incidencia_prevista_media |    MAE |
|:--------------|--------------:|------------------------:|----------------------------:|-------:|
| 2024-11       |           144 |                  14.828 |                       7.514 | 11.099 |
| 2024-12       |           144 |                  13.697 |                      14.828 |  6.984 |

## Maiores erros individuais

| municipio           | competencia   |   incidencia_100mil |   incidencia_prevista |     erro |   erro_absoluto |
|:--------------------|:--------------|--------------------:|----------------------:|---------:|----------------:|
| Pau D'Arco          | 2024-11       |             561.952 |               233.004 | -328.948 |         328.948 |
| Novo Progresso      | 2024-11       |             282.053 |                 2.738 | -279.315 |         279.315 |
| Novo Progresso      | 2024-12       |              79.413 |               282.053 |  202.64  |         202.64  |
| Trairão             | 2024-11       |             160.061 |                 0     | -160.061 |         160.061 |
| Rio Maria           | 2024-11       |             292.749 |               188.196 | -104.553 |         104.553 |
| Ourilândia do Norte | 2024-11       |              80.218 |                 8.595 |  -71.623 |          71.623 |
| Inhangapi           | 2024-11       |              92.989 |                27.897 |  -65.092 |          65.092 |
| Colares             | 2024-11       |              22.18  |                81.325 |   59.145 |          59.145 |
| Trairão             | 2024-12       |             217.684 |               160.061 |  -57.623 |          57.623 |
| Inhangapi           | 2024-12       |              37.195 |                92.989 |   55.794 |          55.794 |
| Itaituba            | 2024-12       |              53.858 |                 2.992 |  -50.866 |          50.866 |
| Mojuí dos Campos    | 2024-12       |               0     |                47.408 |   47.408 |          47.408 |
| Tucumã              | 2024-11       |              44.727 |                 2.354 |  -42.373 |          42.373 |
| Pau D'Arco          | 2024-12       |             603.07  |               561.952 |  -41.118 |          41.118 |
| Mojuí dos Campos    | 2024-11       |              47.408 |                 7.901 |  -39.507 |          39.507 |

## Municípios com maior erro médio

|   codigo_ibge | municipio           |      MAE |   erro_medio |
|--------------:|:--------------------|---------:|-------------:|
|       1505031 | Novo Progresso      | 240.977  |     -38.3375 |
|       1505551 | Pau D'Arco          | 185.033  |    -185.033  |
|       1508050 | Trairão             | 108.842  |    -108.842  |
|       1506161 | Rio Maria           |  65.346  |     -65.346  |
|       1503408 | Inhangapi           |  60.443  |      -4.649  |
|       1504752 | Mojuí dos Campos    |  43.4575 |       3.9505 |
|       1505437 | Ourilândia do Norte |  37.244  |     -37.244  |
|       1502608 | Colares             |  36.9655 |      22.1795 |
|       1508084 | Tucumã              |  29.4255 |     -12.9475 |
|       1503804 | Jacundá             |  28.653  |      -7.814  |
|       1506708 | Santana do Araguaia |  26.828  |     -11.047  |
|       1503606 | Itaituba            |  26.555  |     -26.555  |
|       1508407 | Xinguara            |  23.6845 |      -4.3865 |
|       1501253 | Bannach             |  23.518  |       0      |
|       1505700 | Ponta de Pedras     |  21.3445 |       1.9405 |

## Interpretação

O baseline de persistência superou os modelos de Regressão Linear e Random Forest na validação temporal.

Isso indica que, com apenas os dados de 2024, a persistência temporal da incidência de dengue apresenta maior poder preditivo do que as variáveis climáticas utilizadas no experimento.

Os resultados não demonstram que fatores climáticos sejam irrelevantes. A análise de correlação mostrou associações, especialmente para precipitação com defasagem de um mês. Entretanto, essas relações não foram suficientes para superar o histórico recente da própria incidência na tarefa preditiva atual.

Uma limitação importante é a disponibilidade de apenas um ciclo anual para treinamento e avaliação temporal.
