import requests, time, datetime, logging, re, urllib3
from datetime import timedelta, datetime

from src.supabase_client import supabase


# suprime avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_API_SEMAS = 'https://portaldatransparencia.semas.pa.gov.br/portal-da-transparencia-api/api/v1/guia-florestal/'
LINK_PDF = "https://monitoramento.semas.pa.gov.br/sisflora2/sisflora.api/Gf/VisualizarPdf/"

# Colunas válidas na tabela guias_florestais
COLUNAS_VALIDAS = {
    'id', 'numero', 'data_emissao', 'situacao', 'origem_cpf_cnpj', 'destino_cpf_cnpj', 'origem_endereco', 'origem_bairro',
    'destino_endereco', 'destino_bairro', 'placa', 'autorizacoes', 'origem_nome', 'origem_municipio', 'origem_estado', 'origem_pais',
    'destino_nome', 'destino_municipio', 'destino_estado', 'destino_pais', 'origem_ceprof', 'destino_ceprof', 'tipo', 'codigo_controle', 'link',
    'num_especie', 'relevante'
}

def buscar_guias(session: requests.Session, data_inicio: datetime, data_fim: datetime, page: int =1, max_tentativas: int =8) -> dict:
    '''
    Busca guias florestais para um intervalo de datas
    retorna um dict {numero: dados}, com tratamento de erro 429 via backoff exponencial
    '''

    data_inicio_str = data_inicio.strftime('%Y-%m-%d')
    data_fim_str = data_fim.strftime('%Y-%m-%d')

    tentativas = 0
    guias = {}

    logging.info(f"Buscando guias entre {data_inicio_str} e {data_fim_str}...")
  
    while True:
        url = f'{BASE_API_SEMAS}?page={page}&data_inicio={data_inicio_str}&data_fim={data_fim_str}'
        
        try:
            response = session.get(url, verify=False)
        except requests.exceptions.SSLError as e:
            logging.error(f"Erro SSL ao acessar {url}: {e}")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão ao acessar {url}: {e}")
            break

        if response.status_code == 429:
            wait_time = 2 ** tentativas # backoff
            logging.warning(f"⚠️ Erro 429 - aguardando {wait_time} segundos...")
            time.sleep(wait_time)
            tentativas += 1
            if tentativas >= max_tentativas:
                logging.error("Número máximo de tentativas atingido.")
                break
            continue

        if response.status_code != 200:
            logging.error(f"Erro {response.status_code} ao acessar {url}")
            break

        tentativas = 0
        dados = response.json().get('data',[])
        if not dados:
            break
        
        for dado in dados:
            guias[dado['numero']] = dado

        logging.debug(f"Página {page} carregada com {len(guias)} guias.")
        page += 1
        time.sleep(0.5)  # respeitar API

    time.sleep(5)
    logging.info(f"Total coletado: {len(guias)} guias.")
    return guias

def _normalizar_guia(guia: dict) -> dict:
    """
    Remove hífens da placa, adiciona link e filtra colunas inválidas
    """
    placa = guia.get('placa')
    if placa:
        guia['placa'] = re.sub('-', '', placa)

    guia['link'] = LINK_PDF + guia['numero']

    return {k: v for k,v in guia.items() if k in COLUNAS_VALIDAS}

#def atualizar_relevantes

def atualizar_guias() -> int:
    """
    Busca guias novas na API da SEMAS e salva no Supabase
     - parte da data mais recente no banco, com 5 dias de margem para reprocessar guias que possam ter chegado depois
     - para cada dia do intervalo, compara com o que há existe no banco e insere apenas registros novos
    Retorna o total de guias inseridas
    """
    qtde = 0

    # busca a data da guia mais recente salva no banco de dados
    query = (
        supabase.table("guias_florestais") \
        .select("data_emissao") \
        .order("data_emissao", desc=True) \
        .limit(1)\
        .execute()
    )
    last_date_db = query.data[0]["data_emissao"]

    # período de busca: 5 dias anteriores a data mais recente
    backup_days = 5
    start_date = datetime.strptime(last_date_db, "%Y-%m-%d") - timedelta(days=backup_days)
    end_date = datetime.now()

    # start_date_str = '2025-02-01'
    # start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    # end_date_str = '2025-04-29'
    # end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    logging.info(f"Período de busca: {start_date.date()} -> {end_date.date()}")

    with requests.Session() as session:
        # percorre cada dia individualmente
        for i in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")

            logging.info(f"📅 Processando {date_str}")

            # guias já salvas para esse dia
            query_dia = (
                supabase.table("guias_florestais")
                .select("numero")
                .eq("data_emissao", date_str)
                .execute()
            )
            guias_salvas = {row["numero"] for row in query_dia.data}

            # guias disponíveis na API para esse dia {numero: dados}
            guias_buscadas = buscar_guias(session, current_date, current_date)

            # filtrar somente as que ainda não estão no banco
            novas = [_normalizar_guia(guia) for numero,guia in guias_buscadas.items() if numero not in guias_salvas]

            if novas:
                supabase.table("guias_florestais").upsert(novas, on_conflict="numero").execute()
                qtde += len(novas)
                logging.info(f"✅ {len(novas)} guias salvas para {date_str}")
                qtde += len(novas)
            else:
                logging.info(f"ℹ️ Nenhuma nova guia para {date_str}")

    logging.info(f"Atualização concluída. Total inserido: {qtde}")
    return qtde


if __name__ == '__main__':

    data = atualizar_guias()

