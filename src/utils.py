import requests, time, io, pdfplumber, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
