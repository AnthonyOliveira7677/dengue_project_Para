# Primeiras tentativas de ingestão

## IBGE — API de Localidades

Foi realizada uma primeira ingestão utilizando a API REST de Localidades do IBGE.

A consulta buscou os municípios pertencentes ao estado do Pará e retornou:

- 144 municípios;
- código IBGE de cada município;
- nome do município.

A resposta da API foi recebida em formato JSON e convertida para um DataFrame utilizando Pandas.

### Resultado

A ingestão foi executada com sucesso.

Exemplo de registros obtidos:

| codigo_ibge | municipio |
|---|---|
| 1500107 | Abaetetuba |
| 1500131 | Abel Figueiredo |
| 1500206 | Acará |
| 1500305 | Afuá |
| 1500347 | Água Azul do Norte |

## Ministério da Saúde — SINAN/Dengue

Foi realizada uma primeira consulta à API pública de arboviroses do Ministério da Saúde.

A requisição retornou:

- status HTTP 200;
- resposta em formato JSON;
- 100 registros na página inicial;
- 196 campos disponíveis por registro.

Entre os campos identificados estão informações relacionadas a:
- ano da notificação;
- município;
- data de notificação;
- semana epidemiológica;
- características do caso.

A ingestão inicial foi executada com sucesso.

Nesta etapa ainda não foram aplicados filtros específicos para o estado do Pará.

## INMET — Dados meteorológicos

Foi realizada uma primeira ingestão dos dados históricos do INMET referentes ao ano de 2025.

O arquivo anual foi obtido em formato ZIP diretamente do portal do INMET.

### Resultado da ingestão

- Status HTTP: 200
- Tamanho do arquivo ZIP: aproximadamente 86,69 MB
- Quantidade total de arquivos no ZIP: 595
- Arquivos identificados para o estado do Pará: 33
- Estação utilizada no teste: A201 — Belém
- Quantidade de registros no CSV testado: 8.760
- Quantidade de colunas identificadas: 20

Entre as variáveis encontradas estão:

- precipitação;
- temperatura;
- umidade;
- pressão atmosférica;
- radiação global;
- velocidade e direção do vento.

O arquivo utiliza separador `;`, encoding `latin1` e vírgula como separador decimal.

A primeira leitura do arquivo foi realizada com sucesso utilizando Pandas.