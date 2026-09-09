from src.pipeline import atualizar_guias
from src.utils import buscar_num_especies, passa_pelo_tocantins, extrair_nomes_especies_pdf
from src.pipeline import BASE_API_SEMAS
from src.supabase_client import supabase
import time

if __name__ == "__main__":
    print("🔄 Iniciando atualização automática via GitHub Actions...")
    novas_guias = atualizar_guias()
    if not novas_guias:
        print("✅ Nenhuma nova guia encontrada. Tudo atualizado!")
    else:
        for guia in novas_guias:
            numero = guia['numero']
            tipo = guia['tipo']
            url_pdf = guia['link']

            # pega as espécies via API
            qtd_especies = buscar_num_especies(BASE_API_SEMAS, numero, tipo)

            # verifica a rota baixando e lendo o texto ao PDF
            rota_to = passa_pelo_tocantins(url_pdf)

            # Extrai a lista de nomes das espécies
            lista_nomes_especies = extrair_nomes_especies_pdf(url_pdf)

            # é relevante ?
            is_relevante = rota_to

            print(f"Guia {numero} | Espécies: {qtd_especies} | Nomes: {len(lista_nomes_especies)} extraídos | Passa no TO: {rota_to}")

            # Atualiza o banco de dados com as novas informações
            try:
                supabase.table('guias_florestais') \
                    .update({
                        'num_especie': qtd_especies,
                        'relevante': is_relevante,
                        'nomes_especies': lista_nomes_especies
                    }) \
                    .eq('numero', numero) \
                    .execute()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar os dados enriquecidos da guia {numero} no banco: {e}")
            
            # Pequena pausa para não sobrecarregar a API de consulta de espécies
            time.sleep(1)
            
        print(f"✅ Atualização concluída. Novos registros: {novas_guias}")
