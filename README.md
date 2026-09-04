# dengue_project_Para
Projeto de Ciência de Dados da faculdade para análise do risco de dengue nos municípios do Pará.
# Projeto Integrador — Risco de Dengue no Pará

## Pergunta de pesquisa

Quais municípios do Pará apresentam maior risco de dengue e quais fatores estão associados a esse risco?

## Objetivo

Construir um pipeline de dados para analisar a ocorrência de dengue nos municípios do Pará e identificar fatores associados ao risco da doença.

O projeto utilizará dados epidemiológicos, meteorológicos e socioeconômicos provenientes de fontes públicas oficiais.

## Fontes de dados

### Ministério da Saúde — SINAN
Dados de notificações de dengue.

### INMET
Dados meteorológicos, incluindo:
- precipitação;
- temperatura;
- umidade.

### IBGE
Dados municipais, incluindo:
- população;
- abastecimento de água;
- esgotamento sanitário;
- coleta de lixo.

## Arquitetura

O projeto utilizará arquitetura Medalhão:

- Bronze: dados brutos provenientes das fontes.
- Silver: dados tratados, tipados, padronizados e validados.
- Gold: dados integrados e preparados para análise e modelagem.

## Granularidade inicial

A granularidade inicialmente proposta é:

Uma linha por município do Pará por mês.

A chave será baseada em:

codigo_ibge + ano + mes

## Decisão apoiada pelo projeto

O resultado deverá auxiliar órgãos de saúde pública a identificar municípios que devem receber maior prioridade em ações de prevenção e combate à dengue.

## Estrutura do repositório

- `src/ingestion`: códigos de ingestão dos dados
- `src/bronze`: processamento da camada Bronze
- `src/silver`: processamento da camada Silver
- `src/gold`: construção da camada Gold
- `src/ml`: modelagem e Machine Learning
- `notebooks`: análises exploratórias
- `docs`: documentação e dicionário de dados
- `config`: arquivos de configuração

## Dados

Os arquivos de dados não são armazenados neste repositório.

A pasta `data/` está incluída no `.gitignore`.

## Uso de Inteligência Artificial

Ferramentas de IA generativa poderão ser utilizadas como apoio ao desenvolvimento, documentação e explicação do código. O uso será documentado ao longo do projeto.
