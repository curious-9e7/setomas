import time, requests
from src.supabase_client import supabase
from src.pipeline import BASE_API_SEMAS
from src.utils import passa_pelo_tocantins, extrair_nomes_especies_pdf # Importe a função que lê o PDF


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


def atualizar_especies_por_data(data_alvo=None):
    """
    Atualiza guias pendentes. Se data_alvo for passada (ex: '2026-05-13'), 
    filtra apenas as guias emitidas nesse dia.
    """
    if data_alvo:
        print(f"Buscando guias pendentes para a data {data_alvo} no Supabase...")
    else:
        print("Buscando guias pendentes de atualização no Supabase (todo o histórico)...")

    # 1. Constrói a query base (seleciona as colunas e filtra onde espécies é nulo)
    query = (
        supabase.table('guias_florestais')
        .select('id, numero, tipo, link')
        #.is_('num_especie', 'null')
    )

    # 2. Se uma data foi informada, adiciona o filtro de data na query
    if data_alvo:
        # Usa .like caso a coluna tenha timestamp embutido (ex: 2026-05-13T10:00:00)
        # Se for apenas DATE, .eq('data_emissao', data_alvo) também funcionaria.
        inicio_dia = f"{data_alvo}T00:00:00"
        fim_dia = f"{data_alvo}T23:59:59"
        
        query = query.gte('data_emissao', inicio_dia).lte('data_emissao', fim_dia)

    # 3. Adiciona a ordenação e executa
    resposta = query.order('data_emissao', desc=True).execute()

    guias_pendentes = resposta.data

    if not guias_pendentes:
        if data_alvo:
            print(f"✅ Nenhuma guia pendente encontrada para o dia {data_alvo}.")
        else:
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


def limpar_falsos_positivos():
    print("Iniciando limpeza de falsos positivos...")

    # 1. busca apenas os registros que estão como True para reavaliação
    resposta = (
        supabase.table('guias_florestais')
        .select('id, numero, link')
        .eq('relevante', True)
        .order('data_emissao', desc=True)
        .execute()
    )

    guias_suspeitas = resposta.data

    if not guias_suspeitas:
        print("✅ Nenhuma guia marcada como relevante para reavaliação.")
        return
    
    total = len(guias_suspeitas)
    print(f"Encontradas {total} guias para reavaliar com a nova regra de 2 palavras-chave.\n")

    falsos_positivos_encontrados = 0

    for index, guia in enumerate(guias_suspeitas, start=1):
        guia_id = guia['id']
        numero = guia['numero']
        url_pdf = guia['link']

        print(f"[{index}/{total}] Reavaliando Guia: {numero}...")

        # 2. passa a nova função que exige pelo menos 2 elementos no PDF
        ainda_valido = passa_pelo_tocantins(url_pdf)

        if not ainda_valido:
            # 3. se retornar False, significa que era um falso positivo da função antiga

            try:
                supabase.table('guias_florestais') \
                .update({'relevante': False}) \
                .eq('id', guia_id) \
                .execute()

                falsos_positivos_encontrados += 1
                print(f"   -> 🛑 Falso positivo detectado! Flag atualizada para FALSE.")
            except Exception as e:
                print(f"   -> Erro ao atualizar guia {numero}: {e}")
        else:
            print(f"   ->  Confirmado! A guia realmente passa pelo Tocantins.")
        
        # pausa curta para evitar bloqueios on download do PDF
        time.sleep(1)
    
    print(f"\n🎉 Varredura concluída!")
    print(f"Total de guias analisadas: {total}")
    print(f"Falsos positivos corrigidos: {falsos_positivos_encontrados}")


def reavaliar_rotas_gf3i_por_data(data_alvo):
    print(f"Buscando guias do tipo GF3I para a data {data_alvo} no Supabase...")

    # Define o intervalo do dia inteiro para o filtro
    inicio_dia = f"{data_alvo}T00:00:00"
    fim_dia = f"{data_alvo}T23:59:59"

    # Constrói a query com os filtros de data e tipo
    resposta = (
        supabase.table('guias_florestais')
        .select('id, numero, link, relevante') 
        .eq('tipo', 'GF3I')
        .gte('data_emissao', inicio_dia)
        .lte('data_emissao', fim_dia)
        .order('data_emissao', desc=True)
        .execute()
    )

    guias = resposta.data

    if not guias:
        print(f"✅ Nenhuma guia GF3I encontrada para o dia {data_alvo}.")
        return

    total = len(guias)
    print(f"Encontradas {total} guias para reavaliar. Iniciando processo...\n")

    atualizadas = 0

    for index, guia in enumerate(guias, start=1):
        guia_id = guia['id']
        numero = guia['numero']
        url_pdf = guia['link']
        status_atual_banco = guia.get('relevante')

        print(f"[{index}/{total}] Reavaliando Guia: {numero}...")

        # Aplica a nova função que verifica se a palavra aparece pelo menos 3 vezes
        novo_status = passa_pelo_tocantins(url_pdf)

        # Só envia o update pro banco se o status realmente tiver mudado
        if novo_status != status_atual_banco:
            try:
                supabase.table('guias_florestais') \
                .update({'relevante': novo_status}) \
                .eq('id', guia_id) \
                .execute()
                
                atualizadas += 1
                print(f"   -> 🔄 Status alterado! De {status_atual_banco} para {novo_status}.")
            except Exception as e:
                print(f"   -> ⚠️ Erro ao atualizar a guia {numero}: {e}")
        else:
            print(f"   -> ✔️ Status mantido como {status_atual_banco}.")

        # Pausa para não sobrecarregar o servidor dos PDFs
        time.sleep(1)

    print(f"\n🎉 Varredura do dia {data_alvo} concluída!")
    print(f"Total de guias analisadas: {total}")
    print(f"Guias que tiveram a flag alterada: {atualizadas}")


def preencher_nomes_especies_por_data(data_alvo):
    print(f"Buscando guias sem os nomes das espécies para a data {data_alvo}...")

    # Define o intervalo do dia inteiro para o filtro de timestamp
    inicio_dia = f"{data_alvo}T00:00:00"
    fim_dia = f"{data_alvo}T23:59:59"

    # Constrói a query com os filtros de data e coluna nula
    resposta = (
        supabase.table('guias_florestais')
        .select('id, numero, link') 
        .is_('nomes_especies', 'null') # Atenção: confirme se 'nomes_especies' é o nome exato da coluna criada no Supabase
        .gte('data_emissao', inicio_dia)
        .lte('data_emissao', fim_dia)
        .order('data_emissao', desc=True)
        .execute()
    )

    guias_pendentes = resposta.data

    if not guias_pendentes:
        print(f"✅ Nenhuma guia pendente encontrada para o dia {data_alvo}.")
        return
    
    total = len(guias_pendentes)
    print(f"Encontradas {total} guias para processar no dia {data_alvo}. Iniciando...\n")

    for index, guia in enumerate(guias_pendentes, start=1):
        guia_id = guia['id']
        url_pdf = guia['link']
        numero = guia['numero']

        print(f"[{index}/{total}] Lendo PDF da Guia: {numero}...")

        # Chama a função de extração que criamos no utils.py
        lista_nomes = extrair_nomes_especies_pdf(url_pdf)

        # Se não extraiu nada, salva um array vazio para o script não tentar processar essa guia novamente amanhã
        if not lista_nomes:
            lista_nomes = [] 

        try:
            supabase.table('guias_florestais') \
            .update({'nomes_especies': lista_nomes}) \
            .eq('id', guia_id) \
            .execute()

            nomes_print = ", ".join(lista_nomes) if lista_nomes else "Nenhuma espécie identificada"
            print(f"   -> Sucesso! Espécies: {nomes_print}")
        except Exception as e:
            print(f"   -> ⚠️ Erro ao atualizar guia {numero}: {e}")

        # Pausa para evitar sobrecarga (HTTP 429) no monitoramento da SEMAS
        time.sleep(1)

    print(f"\n🎉 Preenchimento histórico do dia {data_alvo} finalizado!")


if __name__ == "__main__":
    for i in range(1, 10):
        dia = f"{i:02d}"
        data_alvo = f"2026-09-{dia}"
        
        # Chama a nova função passando a data do loop
        preencher_nomes_especies_por_data(data_alvo)
        
        print(f"Processamento para o dia {data_alvo} totalmente finalizado.\n")
        print("-" * 40) # Apenas um separador visual no terminal
