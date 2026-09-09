# Documentação do Projeto: Monitoramento de Guias Florestais

## 1. Visão Geral do Sistema
O sistema foi desenhado para atuar como uma esteira automatizada de dados fiscais e florestais. O objetivo principal é extrair, normalizar, enriquecer e monitorar as Guias Florestais (GF3i) da SEMAS-PA, com ênfase na identificação de cargas de madeira cuja rota de transporte perpasse o Estado do Tocantins.

## 2. Arquitetura e Tecnologias
*   **Linguagem Base:** Python 3
*   **Banco de Dados:** PostgreSQL (gerenciado via Supabase)
*   **Interface Gráfica:** Streamlit (Dashboard interativo e responsivo)
*   **Processamento de PDF:** `pdfplumber` (leitura de PDFs em memória RAM)
*   **Automação:** GitHub Actions

## 3. Estrutura de Módulos (Backend)

### `pipeline.py` (Motor de Extração)
Responsável pelo ciclo de busca diária. Utiliza *Exponential Backoff* para contornar bloqueios HTTP 429 da API da SEMAS. A lógica verifica a data do último registro no banco e processa de forma incremental com uma margem de segurança de 5 dias retroativos.

### `utils.py` (Processamento e Enriquecimento)
Contém as regras de negócio vitais:
*   `passa_pelo_tocantins`: Converte o PDF binário da web para texto e analisa a ocorrência de padrões (`/to`, `tocantins`) para identificar rotas de interesse.
*   `buscar_num_especies`: Função tolerante a falhas que requisita a contagem de espécies vinculadas à guia.

### `run_update.py` e `update_historic.py` (Orquestração)
*   **`run_update.py`**: O *entrypoint* da automação. Encadeia o download de novas guias e aplica o enriquecimento imediatamente, salvando os dados limpos no banco.
*   **`update_historic.py`**: Atua na manutenção dos dados, permitindo limpar falsos positivos ou atualizar requisições retroativas do histórico da tabela.

### `supabase_client.py` e `db_handle.py` (Persistência)
Gerenciam a conexão com o Supabase utilizando credenciais seguras e fornecem funções abstraídas para consultas e comandos de *upsert*.

## 4. Interface de Apresentação (Frontend)

### `app.py` (Dashboard Streamlit)
A interface fornece as informações em duas abas:
1.  **Busca Específica:** Pesquisa por placa do veículo, normalizando entradas (removendo hifens da busca do usuário).
2.  **Filtro Analítico:** Exibe veículos de interesse (apenas guias com `relevante = True`) com base no mês e quantidade mínima de espécies.

*Nota técnica:* O painel identifica o fuso horário (UTC vs GMT) do banco de dados e aplica a correção automática (via biblioteca `pytz`) para exibir ao operador a última atualização garantindo o padrão do **Fuso Horário de Brasília**.

## 5. Fluxo de Dados Diário
1. O *script* `run_update.py` é disparado (GitHub Actions).
2. `pipeline.py` consome a API da SEMAS e identifica os novos registros (verificando o que já existe no Supabase).
3. `utils.py` enriquece a informação validando o trajeto via varredura do texto do PDF em memória.
4. Os dados atualizados são gravados via `supabase.upsert`.
5. O painel Streamlit reflete automaticamente os novos relatórios disponíveis.
