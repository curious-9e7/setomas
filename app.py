import streamlit as st
import json
from datetime import datetime, timedelta
import pytz, unicodedata

from src.supabase_client import supabase


# ---------- Configuração da página ----------
st.set_page_config(page_title="Consulta de Guias", layout="centered")


# ---------- CSS customizado ----------
st.markdown("""
<style>
    .stButton>button {
        background-color: #2E7D32; /* verde escuro */
        color: white;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 16px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #1B5E20; /* verde mais escuro */
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 8px;
        font-size: 16px;
    }
    .card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 5px solid #2E7D32;
    }
</style>
""", unsafe_allow_html=True)

def normalizar_texto(texto):
    """Remove acentos e converte para letras minúsculas."""
    if not texto:
        return ""
    texto_sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto_sem_acento.lower().strip()

# ---------- Componentes ----------
def exibir_card(guia):
    qtd_esp = guia.get('num_especie', 'N/A')
    
    # Formata a lista de espécies
    lista_esp = guia.get('nomes_especies')
    nomes_formatados = ", ".join(lista_esp) if lista_esp else "Não identificadas"

    # Formata a lista de estados da rota
    rotas = guia.get('rotas_estados')
    rotas_formatadas = ", ".join(rotas) if rotas else "Não identificada"

    st.markdown(f"""
    <div class="card">
        <p><b>📄 Número da guia:</b> {guia['numero']}</p>
        <p><b>📅 Data de emissão:</b> {guia['data_emissao'][:10]}</p>
        <p><b>🚗 Placa:</b> {guia['placa']}</p>
        <p><b>📍 Rotas Mapeadas:</b> {rotas_formatadas}</p>
        <p><b>🌱 Espécies ({qtd_esp}):</b> {nomes_formatados}</p>
        <p><b>📌 Situação:</b> {guia['situacao']}</p>
        <a href="{guia['link']}" target="_blank" style="color: #2E7D32; font-weight: bold;">🔗 Visualizar PDF</a>
    </div>
    """, unsafe_allow_html=True)

def obter_ultima_atualizacao():
    try:
        resposta = (
            supabase.table("guias_florestais")
            .select("created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resposta.data:
            data_str = resposta.data[0]["created_at"]
            dt_utc = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
            fuso_br = pytz.timezone("America/Sao_Paulo")
            return dt_utc.astimezone(fuso_br)
    except Exception:
        return None
    return None

def aba_busca_por_placa():
    if "atualizacao_guias" not in st.session_state:
        st.session_state["atualizacao_guias"] = None

    placa_input = st.text_input("Digite a placa (ex: ABC1234):")

    if placa_input:
        placa_formatada = placa_input.replace("-", "").upper()

        # Adicionado rotas_estados, num_especie e nomes_especies para o card funcionar corretamente
        resposta = (
            supabase.table("guias_florestais") \
            .select("numero, data_emissao, situacao, placa, link, rotas_estados, num_especie, nomes_especies") \
            .ilike("placa", f"%{placa_formatada}%") \
            .order("data_emissao", desc=True) \
            .execute()
        )

        guias = resposta.data
        if guias:
            for guia in guias:
                exibir_card(guia)
        else:
            st.warning("🚫 Nenhuma guia encontrada para essa placa.")

def aba_veiculos_interesse():
    st.subheader("⭐ Veículos com Rota Tocantins (Clássico)")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 3])

    with col1:
        meses = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, 
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, 
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        mes_atual = datetime.today().month
        mes_selecionado = st.selectbox("Mês", list(meses.keys()), index=mes_atual - 1)
        mes = meses[mes_selecionado]

    with col2:
        ano_atual = datetime.today().year
        ano = st.selectbox("Ano", [ano_atual, ano_atual - 1, ano_atual - 2])

    with col3:
        min_especies = st.number_input("Mín. Espécies", min_value=0, value=5, step=1)

    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano + 1}-01-01" if mes == 12 else f"{ano}-{mes + 1:02d}-01"

    # Adicionado rotas_estados
    query = (
        supabase.table("guias_florestais")
        .select("numero, data_emissao, situacao, placa, link, num_especie, nomes_especies, rotas_estados")
        .eq("relevante", True)
        .gte("data_emissao", data_inicio)
        .lt("data_emissao", data_fim)
    )
    
    if min_especies > 0:
        query = query.gte("num_especie", min_especies)

    resposta = query.order("data_emissao", desc=True).execute()
    guias = resposta.data

    if guias:
        st.info(f"📋 Mostrando {len(guias)} guias encontradas.")
        for guia in guias:
            exibir_card(guia)
    else:
        st.warning("🚫 Nenhuma guia relevante encontrada para os filtros selecionados.")

def aba_busca_avancada():
    st.subheader("⚙️ Busca Avançada")
    st.markdown("Filtre guias combinando o **Estado da Rota**, **Quantidade** e **Nome da Espécie**.")

    # Linha 1: Filtros de Data e Estado
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        meses = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, 
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, 
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        mes_atual = datetime.today().month
        mes_selecionado = st.selectbox("Mês", list(meses.keys()), index=mes_atual - 1, key="mes_avancado")
        mes = meses[mes_selecionado]

    with col2:
        ano_atual = datetime.today().year
        ano = st.selectbox("Ano", [ano_atual, ano_atual - 1, ano_atual - 2], key="ano_avancado")

    with col3:
        lista_estados = ["Todos", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
        estado_filtro = st.selectbox("Filtrar por Estado (Rota)", lista_estados, index=0)

    # Linha 2: Filtros de Espécie
    col4, col5 = st.columns([4, 3])
    
    with col4:
        especie_filtro = st.text_input("Nome da Espécie", placeholder="Ex: cupiuba (deixe vazio para ignorar)")
        
    with col5:
        qtd_min_especies = st.number_input("Mínimo de Espécies Diferentes", min_value=0, value=0, step=1, key="qtd_esp_avancado")

    # Botão de ação para evitar sobrecarga no banco enquanto o usuário digita
    if st.button("Buscar Guias", use_container_width=True):
        data_inicio = f"{ano}-{mes:02d}-01"
        data_fim = f"{ano + 1}-01-01" if mes == 12 else f"{ano}-{mes + 1:02d}-01"

        # Query Base
        query = (
            supabase.table("guias_florestais")
            .select("numero, data_emissao, situacao, placa, link, num_especie, nomes_especies, rotas_estados, relevante")
            .gte("data_emissao", data_inicio)
            .lt("data_emissao", data_fim)
        )
        
        # Filtro DB: Quantidade de Espécies
        if qtd_min_especies > 0:
            query = query.gte("num_especie", qtd_min_especies)
            
        # Filtro DB: Busca em coluna JSONB usando .contains()
        if estado_filtro != "Todos":
            # Formata explicitamente como uma string JSON (ex: '["BA"]')
            filtro_json = f'["{estado_filtro}"]'
            query = query.contains("rotas_estados", filtro_json)

        resposta = query.order("data_emissao", desc=True).execute()
        guias = resposta.data
        
        guias_filtradas = []

        # Filtro Python: Busca de texto dentro da lista de espécies
        if especie_filtro:
            termo_busca = normalizar_texto(especie_filtro)

            for guia in guias:
                nomes_raw = guia.get('nomes_especies')
                
                if isinstance(nomes_raw, str):
                    try:
                        lista_especies = json.loads(nomes_raw)
                    except json.JSONDecodeError:
                        lista_especies = []
                elif isinstance(nomes_raw, list):
                    lista_especies = nomes_raw
                else:
                    lista_especies = []
                
                if any(termo_busca in normalizar_texto(esp) for esp in lista_especies):
                    guias_filtradas.append(guia)
        else:
            # Se não digitou nome de espécie, exibe todas que passaram pelos filtros de banco
            guias_filtradas = guias

        # Renderização dos resultados
        if guias_filtradas:
            st.success(f"🔎 Encontradas {len(guias_filtradas)} guias correspondentes.")
            for guia in guias_filtradas:
                exibir_card(guia)
        else:
            st.warning("🚫 Nenhuma guia encontrada com essa combinação de filtros no período.")

# ---------- Interface principal ----------
st.title("🌳 Consulta de Guias Florestais")
tabs = st.tabs(["🔎 Busca por Placa", "⭐ Guias (Tocantins)", "⚙️ Busca Avançada"])

# status global de atualização
ultima_att = obter_ultima_atualizacao()
if ultima_att:
    st.markdown(f"""
        <div style='text-align: right; color: gray; font-size: 0.8rem;'>
            Último registro inserido no banco: {ultima_att.strftime('%d/%m/%Y %H:%M')}
        </div>
    """, unsafe_allow_html=True)

with tabs[0]:
    aba_busca_por_placa()

with tabs[1]:
    aba_veiculos_interesse()

with tabs[2]:
    aba_busca_avancada()