import requests, time, io, pdfplumber, logging, re
from typing import List, Tuple, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# configurações
TIMEOUT_REQUEST = 15
MAX_TRY_API = 5
WAIT_TIME_API = 60

# Dicionário com todos os estados para varredura
ESTADOS_BR = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapá', 'AM': 'amazonas', 'BA': 'bahia',
    'CE': 'ceará', 'DF': 'distrito federal', 'ES': 'espírito santo', 'GO': 'goiás',
    'MA': 'maranhão', 'MT': 'mato grosso', 'MS': 'mato grosso do sul', 'MG': 'minas gerais',
    'PA': 'pará', 'PB': 'paraíba', 'PR': 'paraná', 'PE': 'pernambuco', 'PI': 'piauí',
    'RJ': 'rio de janeiro', 'RN': 'rio grande do norte', 'RS': 'rio grande do sul',
    'RO': 'rondônia', 'RR': 'roraima', 'SC': 'santa catarina', 'SP': 'são paulo',
    'SE': 'sergipe', 'TO': 'tocantins'
}


def buscar_num_especies(url_base, numero, tipo):
    """
    Busca a quantidade total de espécies cadastradas na guia via API.
    Utiliza backoff simples em caso de limite de requisições (HTTP 429).
    """
    tentativas = 0
    url = f"{url_base}especies?page=1&id={numero}&tipo={tipo}"

    while tentativas < MAX_TRY_API:
        try:
            response = requests.get(url, timeout=TIMEOUT_REQUEST)

            if response.status_code == 429:
                print(f"⚠️ Erro 429. Aguardando {(tentativas+1)*WAIT_TIME_API}s...")
                time.sleep(WAIT_TIME_API)
                tentativas += 1
                continue

            if response.status_code == 200:
                dados = response.json()
                return dados.get('total', 0)

            logging.warning(f"Erro {response.status_code} ao buscar espécies da guia {numero}.")
            return 0
        
        except requests.RequestException as e:
            logging.error(f"Falha de conexão na API de espécies: {e}")
            tentativas += 1
            time.sleep(WAIT_TIME_API)
    
    return 0


def processar_pdf_guia(url_pdf: str) -> Tuple[List[str], List[str]]:
    """
    Processa o PDF extraindo as rotas (usando Regex e Word Boundaries) 
    e os nomes das espécies de forma segura.
    """
    try:
        response = requests.get(url_pdf, timeout=15)
        if response.status_code != 200:
            logging.warning(f"Não foi possível acessar o PDF. Status: {response.status_code}")
            return [], []
        
        texto_completo = ""
        nomes_populares: Set[str] = set()

        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                
                # --- Tarefa 1: Extração de Texto ---
                texto = page.extract_text()
                if texto:
                    # Agora mantemos o texto original (com maiúsculas e acentos) para o Regex analisar
                    texto_completo += texto + "\n"

                # --- Tarefa 2: Extração de Tabelas ---
                tabelas = page.extract_tables()
                for tabela in tabelas:
                    if not tabela or not tabela[0]:
                        continue
                    
                    cabecalho_limpo = [str(col).replace('\n', ' ').strip() for col in tabela[0] if col]
                    
                    if "Nome Popular" in cabecalho_limpo:
                        indice = cabecalho_limpo.index("Nome Popular")
                        for linha in tabela[1:]:
                            if len(linha) > indice:
                                nome = str(linha[indice]).replace('\n', ' ').strip()
                                if nome and nome.lower() != "none":
                                    nomes_populares.add(nome)

        estados_encontrados = []
        
        # --- Tarefa 3: Varredura de Estados com Regex Seguro ---
        for uf, nome_estado in ESTADOS_BR.items():
            
            # 1. Busca o nome completo do estado exatamente como é (com acento se tiver)
            # O \b garante que é a palavra exata.
            padroes = [rf'\b{nome_estado}\b']
            
            # 2. Busca a sigla acompanhada de marcadores explícitos de localidade
            padroes.append(rf'\buf\s*:\s*{uf}\b')  # Ex: UF: PA, uf:pa
            padroes.append(rf'/\s*{uf}\b')         # Ex: /PA, / PA
            padroes.append(rf',\s*{uf}\b')         # Ex: , PA
            
            # 3. Busca a sigla com hífen
            # A regra do hífen é desativada APENAS para o Sergipe (SE)
            # para não gerar falso positivo com pronomes de verbos ("inicia-se")
            if uf != 'SE':
                padroes.append(rf'-\s*{uf}\b')     # Ex: -PA, - PA
                padroes.append(rf'\b{uf}\s*-')     # Ex: PA-, PA -
                
            # Compila todas as regras usando IGNORECASE (lida com maiúsculas/minúsculas sozinho)
            regex_estado = re.compile('|'.join(padroes), re.IGNORECASE)
            
            # Encontra e conta todas as ocorrências válidas
            ocorrencias = regex_estado.findall(texto_completo)
            
            if len(ocorrencias) >= 3:
                estados_encontrados.append(uf)
                
        return estados_encontrados, list(nomes_populares)
        
    except Exception as e:
        logging.error(f"Erro interno ao processar o PDF da guia: {e}")
        return [], []