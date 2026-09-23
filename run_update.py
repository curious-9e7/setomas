import time, logging

from src.pipeline import atualizar_guias, BASE_API_SEMAS
from src.supabase_client import supabase
from src.utils import buscar_num_especies, processar_pdf_guia

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    logging.info("🔄 Iniciando atualização automática via GitHub Actions...")
    novas_guias = atualizar_guias()

    if not novas_guias:
        logging.info("✅ Nenhuma nova guia encontrada. Tudo atualizado!")
    else:
        for guia in novas_guias:
            numero = guia['numero']
            tipo = guia['tipo']
            url_pdf = guia['link']

            # Filtro 1: processar apenas guias com rota fora do PARÁ (GF3I)
            # if tipo != 'GF3I':
            #     logging.info(f"⏭️ Guia {numero} ignorada (Tipo: {tipo} não é GF3I).")
            #     continue

            # Filtro 2: verificar se já possui os dados enriquecidos (segurança para o pipeline)
            # OBS: como são guias novas recém-buscadas na API, geralmente não terão esses campos ainda
            tem_relevante = guia.get('relevante') is not None
            tem_rotas = guia.get('rotas_estados') is not None
            tem_especies = guia.get('nomes_especies') is not None

            if tem_relevante and tem_rotas and tem_especies:
                logging.info(f"⏭️ Guia {numero} ignorada (Já possui os dados enriquecidos).")
                continue

            # Processamento das guias usando a nova função unificada
            estados_da_rota, lista_nomes = processar_pdf_guia(url_pdf)
            rota_to = 'TO' in estados_da_rota
            qtd_especies = buscar_num_especies(BASE_API_SEMAS, numero, tipo)

            logging.info(f"Guia {numero} | Espécies: {qtd_especies} | Estados: {estados_da_rota} | TO: {rota_to}")

            try:
                supabase.table('guias_florestais') \
                    .update({
                        'num_especie': qtd_especies,
                        'relevante': rota_to,
                        'rotas_estados': estados_da_rota,
                        'nomes_especies': lista_nomes if lista_nomes else []
                    }) \
                    .eq('numero', numero) \
                    .execute()
            except Exception as e:
                logging.error(f"⚠️ Erro ao atualizar os dados da guia {numero} no banco: {e}") 

            time.sleep(1)
            
        logging.info(f"✅ Atualização concluída. Total de novos registros crus iterados: {len(novas_guias)}")


