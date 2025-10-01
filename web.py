from src.supabase_client import supabase


link = 'https://monitoramento.semas.pa.gov.br/sisflora2/sisflora.api/Gf/VisualizarPdf/'
query = (
    supabase.table("guias_florestais") \
    .select("*")
    .is_("link", None)
    .execute()
)

guias = query.data

for guia in guias:
    guia['link'] = link + guia['numero']
    print(guia)

print(len(guias))
if guias:
    supabase.table('guias_florestais') \
        .upsert(guias, on_conflict='numero') \
        .execute()