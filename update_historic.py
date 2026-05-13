import time, requests
from src.supabase_client import supabase
from src.pipeline import BASE_API_SEMAS
from src.utils import passa_pelo_tocantins # Importe a função que lê o PDF


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
            tentativas += 1 # CORRIGIDO: de == 1 para += 1
            continue

        if response.status_code == 200:
            print('✅ Número de espécies encontrado via API.')
            return response.json().get('total', 0)
        
        return None
    return None

def atualizar_especies_pendentes():
    print("Buscando guias pendentes de atualização no Supabase...")

    # Consulta os registros onde num_especie é nulo.
    # ADICIONADO: a coluna 'link' no select para baixar o PDF
    resposta = (
        supabase.table('guias_florestais')
        .select('id, numero, tipo, link') 
        .is_('num_especie', 'null')
        .order('data_emissao', desc=True)
        .execute()
    )

    guias_pendentes = resposta.data

    if not guias_pendentes:
        print("✅ Nenhuma guia pendente! Todas já possuem o número de espécies.")
        return
    
    total = len(guias_pendentes)
    print(f"Encontradas {total} guias para atualizar. Iniciando processo...\n")

    for index, guia in enumerate(guias_pendentes, start=1):
        guia_id = guia['id']
        numero = guia['numero']
        tipo = guia['tipo']
        url_pdf = guia['link']

        print(f"[{index}/{total}] Processando Guia: {numero} (Tipo: {tipo})...")

        # Busca a quantidade de espécies via API
        qtd_especies = buscar_num_especies(BASE_API_SEMAS, numero, tipo)

        # Verifica a rota lendo o texto do PDF
        rota_to = passa_pelo_tocantins(url_pdf)

        # Prepara os dados para salvar
        dados_atualizacao = {'relevante': rota_to}
        if qtd_especies is not None:
            dados_atualizacao['num_especie'] = qtd_especies

        # Atualiza o registro no Supabase
        try:
            supabase.table('guias_florestais') \
            .update(dados_atualizacao) \
            .eq('id', guia_id) \
            .execute()

            print(f"   -> Sucesso! Espécies: {qtd_especies} | Passa no TO (Relevante): {rota_to}")
        except Exception as e:
            print(f"   -> Erro ao atualizar guia {numero}: {e}")

        time.sleep(1)  # Para evitar sobrecarga na API

    print("\n🎉 Atualização em lote finalizada!")

if __name__ == "__main__":
    atualizar_especies_pendentes()