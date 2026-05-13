import streamlit as st
from datetime import datetime, timedelta
import pytz

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
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }
    .card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ---------- Componentes ----------
def exibir_card(guia):
    qtd_esp = guia.get('num_especie', 'N/A')
    st.markdown(f"""
    <div class="card">
        <p><b>📄 Número da guia:</b> {guia['numero']}</p>
        <p><b>📅 Data de emissão:</b> {guia['data_emissao'][:10]}</p>
        <p><b>🚗 Placa:</b> {guia['placa']}</p>
        <p><b>🌱 Quantidade de Espécies:</b> {qtd_esp}</p>
        <p><b>📌 Situação:</b> {guia['situacao']}</p>
        <a href="{guia['link']}" target="_blank">🔗 Visualizar PDF</a>
    </div>
    """, unsafe_allow_html=True)

def obter_ultima_atualizacao():
    """
    Busca o registro mais recente baseado na coluna de criação
    """

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
            # converte a string para datetime
            dt_utc = datetime.fromisoformat(data_str.replace("Z", "+00:00"))

            fuso_br = pytz.timezone("America/Sao_Paulo")
            dt_brasilia = dt_utc.astimezone(fuso_br)

            return dt_brasilia
    
    except Exception:
        return None
    return None

def aba_busca_por_placa():
    if "atualizacao_guias" not in st.session_state:
        st.session_state["atualizacao_guias"] = None

    if st.session_state["atualizacao_guias"]:
        horario_local = st.session_state["atualizacao_guias"] - timedelta(hours=3)
        st.caption(f"🕓 Última atualização: {horario_local.strftime('%d/%m/%Y %H:%M:%S')}")

    placa_input = st.text_input("Digite a placa (ex: ABC1234):")

    if placa_input:
        placa_formatada = placa_input.replace("-", "").upper()

        resposta = (
            supabase.table("guias_florestais") \
            .select("numero, data_emissao, situacao, placa, link") \
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
    st.subheader("⭐ Veículos com Rota Tocantins")

    # colunas para filtros
    col1, col2 = st.columns(2)

    with col1:
        data_selecionada = st.date_input("Selecione o Mês/Ano", datetime.today())

    with col2:
        # filtro de quantidade mínima de espécies
        min_especies = st.number_input("Mínimo de Esécies", min_value=0, value=5, step=1)
    
    mes = data_selecionada.month
    ano = data_selecionada.year

    data_inicio = f"{ano}-{mes:02d}-01"
    if mes == 12:
        data_fim = f"{ano + 1}-01-01"
    else:
        data_fim = f"{ano}-{mes + 1:02d}-01"

    # construção da query com os filtros
    query = (
        supabase.table("guias_florestais")
        .select("numero, data_emissao, situacao, placa, link, num_especie")
        .eq("relevante", True)
        .gte("data_emissao", data_inicio)
        .lt("data_emissao", data_fim)
    )
    
    # aplica filtro de quantidade de espécie
    if min_especies > 0:
        query = query.gte("num_especie", min_especies)

    # ordenação da mais recente para a mais antiga
    resposta = query.order("data_emissao", desc=True).execute()
    guias = resposta.data

    if guias:
        st.info(f"📋 Mostrando {len(guias)} guias encontradas.")
        for guia in guias:
            exibir_card(guia)
    else:
        st.warning("🚫 Nenhuma guia relevante encontrada para o mês selecionado.")


# ---------- Interface principal ----------
st.title("🌳 Consulta de Guias Florestais")
tabs = st.tabs(["🔎 Busca por Placa", "⭐ Guias Relevantes"])

# status global de atualização
ultima_att = obter_ultima_atualizacao()
if ultima_att:
    st.markdown(f"""
        <div style='text-align: right; color: gray; font-size: 0.8rem;'>
            Atualizado em: {ultima_att.strftime('%d/%m/%Y %H:%M')}
        </div>
    """, unsafe_allow_html=True)

with tabs[0]:
    aba_busca_por_placa()

with tabs[1]:
    aba_veiculos_interesse()