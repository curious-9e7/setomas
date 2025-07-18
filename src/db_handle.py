from src.supabase_client import supabase

def inserir_novos_dados(dados):
    if dados:
        supabase.table('guias_florestais').upsert(dados, on_conflict='numero').execute()

def listar_guias():
    response = supabase.table('guias_florestais').select('*').execute()
    return response.data

def listar_guias_data_recente():
    
    res = supabase.table("guias_florestais") \
        .select("data_emissao") \
        .order("data_emissao", desc=True) \
        .limit(1) \
        .execute()
    
    if res.data:
        data_inicio = res.data[0]["data_emissao"]
    
    response = supabase.table('guias_florestais')\
        .select('numero')\
        .gte('data_emissao', data_inicio)\
        .execute()
    
    return data_inicio, response.data if response.data else []