import streamlit as st
from datetime import datetime, timedelta

from src.supabase_client import supabase
from src.pipeline import atualizar_dados, atualizar_guias
from src.db_handle import inserir_novos_dados, listar_guias


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


# ---------- Funções ----------
def exibir_card(guia):
    st.markdown(f"""
    <div class="card">
        <p><b>📄 Número da guia:</b> {guia['numero']}</p>
        <p><b>📅 Data de emissão:</b> {guia['data_emissao'][:10]}</p>
        <p><b>🚗 Placa:</b> {guia['placa']}</p>
        <p><b>📌 Situação:</b> {guia['situacao']}</p>
        <a href="{guia['link']}" target="_blank">🔗 Visualizar PDF</a>
    </div>
    """, unsafe_allow_html=True)


def consultar_por_placa():
    placa_input = st.text_input("Digite a placa (ex: ABC1234):")

    if placa_input:
        placa_formatada = placa_input.replace("-", "").upper()

        resposta = supabase.table("guias_florestais") \
            .select("numero, data_emissao, situacao, placa, link") \
            .ilike("placa", f"%{placa_formatada}%") \
            .order("data_emissao", desc=True) \
            .execute()

        guias = resposta.data

        if guias:
            #st.success(f"🔍 {len(guias)} guia(s) encontradas para a placa {placa_formatada}:")

            for guia in guias:
                exibir_card(guia)
        else:
            st.warning("🚫 Nenhuma guia encontrada para essa placa.")


def consultar_relevantes_por_mes():
    st.subheader("📆 Consultar guias relevantes por mês")

    data_selecionada = st.date_input("Selecione o mês", datetime.today())
    mes = data_selecionada.month
    ano = data_selecionada.year

    data_inicio = f"{ano}-{mes:02d}-01"
    if mes == 12:
        data_fim = f"{ano + 1}-01-01"
    else:
        data_fim = f"{ano}-{mes + 1:02d}-01"

    resposta = supabase.table("guias_florestais") \
        .select("numero, data_emissao, situacao, placa, link") \
        .eq("relevante", True) \
        .gte("data_emissao", data_inicio) \
        .lt("data_emissao", data_fim) \
        .order("data_emissao", desc=True) \
        .execute()

    guias = resposta.data

    if guias:
        for guia in guias:
            exibir_card(guia)
    else:
        st.warning("🚫 Nenhuma guia relevante encontrada para o mês selecionado.")


# ---------- Interface principal ----------
st.title("🌳 Consulta de Guias Florestais")
tabs = st.tabs(["🔎 Busca por Placa", "⭐ Guias Relevantes"])

with tabs[0]:
    # Se você quiser manter isso fora da função e entre sessões:
    if "atualizacao_guias" not in st.session_state:
        st.session_state["atualizacao_guias"] = None

    if st.button('🔄 Atualizar guias'):
        with st.spinner("⏳ Atualizando dados, aguarde...", show_time=True):
            novos = atualizar_guias()

        if novos:
            st.success(f"{len(novos)} novos registros adicionados.")
        else:
            st.info("Nenhum novo dado encontrado.")

        # ⏰ Atualiza o horário da última execução
        st.session_state["atualizacao_guias"] = datetime.now()

    # 🕓 Exibe horário da última atualização
    if st.session_state["atualizacao_guias"]:
        horario_str = st.session_state["atualizacao_guias"] - timedelta(hours=3)
        horario = horario_str.strftime("%d/%m/%Y %H:%M:%S")
        st.caption(f"🕓 Última atualização: {horario}")

    consultar_por_placa()

with tabs[1]:
    consultar_relevantes_por_mes()