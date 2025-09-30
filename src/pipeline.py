import requests, time, datetime, logging
from datetime import timedelta, datetime

from src.supabase_client import supabase


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_API_SEMAS = 'http://portaldatransparencia.semas.pa.gov.br/portal-da-transparencia-api/api/v1/guia-florestal/'


def buscar_guias(session, url_base, data_inicio, data_fim, page=1, max_tentativas=8):
    '''
    Busca guias florestais para um período de datas, com tratamento de erro 429 (Too Many Requests).
    '''

    tentativas = 0

    logging.info(f"Buscando guias entre {data_inicio} e {data_fim}...")

    guias = {}

    while True:
        url = f'{url_base}?page={page}&data_inicio={data_inicio}&data_fim={data_fim}'
        response = session.get(url)

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


def atualizar_dados():
    # 01. buscar últimos registros do banco (filtrado pela data mais recente)
    data_inicio, registros = listar_guias_data_recente()

    if registros:
        data_inicio = data_inicio
    else:
        data_inicio = data_inicio_padrao
    
    #data_fim = '2025-07-21'
    data_fim = datetime.date.today().isoformat()

    # 02. buscar novas guias da API
    novos = buscar_guias(base_api_semas, data_inicio, data_fim)
    if not novos:
        return []
    
    # 03. coletar ids das guias existentes no banco (da data mais recente)
    ids_existentes = {r['numero'] for r in registros}
    
    guias_processadas = []
    
    for guia in novos:
        if guia['numero'] not in ids_existentes:
            print(f"📥 Processando nova guia ID {guia['numero']}")

            guia['placa'] = (guia.get('placa','') or '').replace('-','')
            guia['link'] = 'https://monitoramento.semas.pa.gov.br/sisflora2/sisflora.api/Gf/VisualizarPdf/' + guia['numero']
            guia['relevante'] = False

            if guia['situacao'] != 'RECEBIDO':
                total_especies = buscar_num_especies(base_api_semas, guia['numero'], guia['tipo'])
                guia['num_especie'] = total_especies

                if total_especies is not None and total_especies >= 4:
                    guia['relevante'] = contem_palavra_pdf(guia['link'], 'tocantins')
            else:
                guia['num_especie'] = 0
            
            if guia['num_especie'] > 20:
                guia['num_especie'] = 19

            inserir_novos_dados([guia])
            guias_processadas.append(guia)

    
    return guias_processadas

#def atualizar_relevantes

def atualizar_guias():
    """
    Atualiza guias florestais buscando da API e comparando com os registros já salvos no Supabase.
    """
    qtde = 0
    # buscar a data da guia mais recente salva no banco de dados
    query = (
        supabase.table("guias_florestais") \
        .select("data_emissao") \
        .order("data_emissao", desc=True) \
        .limit(1)\
        .execute()
    )
    last_date_db = query.data[0]["data_emissao"]

    # definir período de busca: 5 dias anteriores a data do passo anterior até o dia de hoje
    backup_days = 5
    start_date = datetime.strptime(last_date_db, "%Y-%m-%d") - timedelta(days=backup_days)
    end_date = datetime.now()

    # start_date_str = '2025-09-23'
    # start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    # end_date_str = '2025-09-24'
    # end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    logging.info(f"Buscando guias de {start_date.date()} até {end_date.date()}")

    with requests.Session() as session:
        # percorre cada dia individualmente
        for i in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")

            logging.info(f"📅 Processando dia {date_str}")

            # buscar guias já salvas no banco para esse dia
            query_by_day = (
                supabase.table("guias_florestais")
                .select("numero")
                .eq("data_emissao", date_str)
                .execute()
            )
            guias_salvas = {row["numero"] for row in query_by_day.data}

            # buscar guias na API para esse dia {numero: dados}
            guias_buscadas = buscar_guias(session, BASE_API_SEMAS, current_date, current_date)

            # filtrar só as que ainda não estão no banco
            guias_para_salvar = [guias_buscadas[numero] for numero in guias_buscadas.keys() if numero not in guias_salvas]
            qtde += len(guias_para_salvar)

            # normalizar placas e adicionar o link
            link = 'https://monitoramento.semas.pa.gov.br/sisflora2/sisflora.api/Gf/VisualizarPdf/'
            for guia in guias_para_salvar:
                if (guia['placa'] is not None) and ('-' in guia['placa']):
                    guia['placa'].replace('-','')

                guia['link'] = link + guia['numero']

            if guias_para_salvar:
                supabase.table("guias_florestais").upsert(guias_para_salvar, on_conflict="numero").execute()
                logging.info(f"✅ {len(guias_para_salvar)} guias salvas para {date_str}")
            else:
                logging.info(f"ℹ️ Nenhuma nova guia para {date_str}")

    logging.info("Atualização concluída")
    return qtde

        
if __name__ == '__main__':

    data = atualizar_guias()
