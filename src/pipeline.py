import requests, time, datetime, pdfplumber, io

from src.db_handle import inserir_novos_dados, listar_guias_data_recente


base_api_semas = 'http://portaldatransparencia.semas.pa.gov.br/portal-da-transparencia-api/api/v1/guia-florestal/'
data_inicio_padrao = '2025-07-01'

def buscar_guias(url_base, data_inicio, data_fim):

    page = 1
    max_tentativas = 5
    tentativas = 0
    guias = []

    while True:
        url = f'{url_base}?page={page}&data_inicio={data_inicio}&data_fim={data_fim}'
        response = requests.get(url)

        if response.status_code == 429:
            time.sleep(60)
            print(f"⚠️ Erro 429 (muitas requisições na buscar_guias). Aguardando {time.sleep(60)}s...")
            tentativas += 1
            if tentativas >= max_tentativas:
                break
            continue
        elif response.status_code != 200:
            break

        tentativas = 0
        dados = response.json().get('data',[])
        if not dados:
            break

        guias.extend(dados)
        page += 1

    print(f'Quantidade de páginas pesquisadas:{page}')
    print(f'Quantidade de guias:{len(guias)}')

    return guias


def buscar_num_especies(url_base, numero, tipo):

    tentativas = 0
    max_tentativas = 5
    url = f'{url_base}especies?page=1&id={numero}&tipo={tipo}'
    
    while tentativas < max_tentativas:
        response = requests.get(url)

        if response.status_code == 429:
            tempo_espera = 60
            print(f"⚠️ Erro 429 (muitas requisições na buscar_num_especies). Aguardando {(tentativas+1)*tempo_espera}s...")
            time.sleep(tempo_espera)
            tentativas += 1
            continue

        if response.status_code == 200:
            return response.json().get('total',0)
        
        return None
    
    return None


def contem_palavra_pdf(url, palavra):
    try:
        response = requests.get(url, timeout=10)
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texto = ''.join([p.extract_text() or '' for p in pdf.pages])
            return palavra.lower() in texto.lower()
    except Exception as e:
        print(f'Erro PDF: {e}')
        return False



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
        

#atualizar_dados()