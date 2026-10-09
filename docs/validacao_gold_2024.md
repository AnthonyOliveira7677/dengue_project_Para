# Validação da Gold - 2024

## Status

**APROVADA**

## Estrutura

- Linhas: 1728
- Municípios: 144
- Competências mensais: 12
- Duplicatas em `codigo_ibge + competencia`: 0
- Valores nulos: 0

## Integridade epidemiológica

- Casos prováveis na Silver SINAN: 21033
- Casos prováveis na Gold: 21033
- Casos confirmados na Silver SINAN: 18217
- Casos confirmados na Gold: 18217
- Confirmados maiores que prováveis: 0
- Prováveis maiores que notificações: 0

## Qualidade das variáveis

- População inválida: 0
- Incidência negativa: 0
- Temperaturas fora da faixa de validação: 0
- Umidade fora de 0–100%: 0
- Precipitação negativa: 0

## Granularidade

Uma linha representa um município do Pará em uma competência mensal.

**Chave:** `codigo_ibge + competencia`

## Fontes integradas

- SINAN: casos de dengue
- NASA POWER: temperatura, umidade e precipitação
- IBGE: municípios, malha territorial e população

## Resultado

A Gold foi validada para uso nas etapas analíticas e de modelagem.
