import requests, time, io, pdfplumber, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def contem_palavra_pdf(url, palavra):
    try:
        response = requests.get(url, timeout=10)
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texto = ''.join([p.extract_text() or '' for p in pdf.pages])
            return palavra.lower() in texto.lower()
    except Exception as e:
        print(f'Erro PDF: {e}')
        return False

def buscar_num_especies(url_base, numero, tipo):
    tentativas = 0
    max_tentativas = 5
    url = f"{url_base}especies?page=1&id={numero}&tipo={tipo}"

    while tentativas < max_tentativas:
        response = requests.get(url)

        if response.status_code == 429:
            tempo_espera = 60
            print(f"⚠️ Erro 429. Aguardando {(tentativas+1)*tempo_espera}s...")
            time.sleep(tempo_espera)
            tentativas += 1
            continue

        if response.status_code == 200:
            dados = response.json()
            # o tempo total traz a quantidade de intes cadastradas
            return dados.get('total', 0)
        
        # se der outro erro (500, 404), sai do loop
        print(f"⚠️ Erro {response.status_code} ao buscar espécies.")
        return 0
    
    return 0

def passa_pelo_tocantins(url_pdf):
    try:
        response = requests.get(url_pdf, timeout=15)
        if response.status_code != 200:
            return False
        
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                # extrai o texto, ignorando a renderização de tabelas
                texto = page.extract_text()
                if texto:
                    texto_completo += texto.lower() + "\n"

            # palavras-chave que indicam rota ou destino para o TO
            palavras_chave = ['tocantins', '/to\n', 'uf:to', 'uf: to', 'to-', '-to']

            return any(palavra in texto_completo for palavra in palavras_chave)
        
    except Exception as e:
        print(f"Erro ao ler PDF da guia: {e}")
        return False