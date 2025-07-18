import streamlit as st
from datetime import datetime
from src.supabase_client import supabase


from src.pipeline import atualizar_dados
from src.db_handle import inserir_novos_dados, listar_guias






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
            st.success(f"🔍 {len(guias)} guia(s) encontradas para a placa {placa_formatada}:")

            for guia in guias:
                st.markdown("---")
                st.markdown(f"📄 **Número da guia:** `{guia['numero']}`")
                st.markdown(f"📅 **Data de emissão:** `{guia['data_emissao'][:10]}`")
                st.markdown(f"🚗 **Placa:** `{guia['placa']}`")
                st.markdown(f"📌 **Situação:** `{guia['situacao']}`")
                st.markdown(f"[🔗 Visualizar PDF]({guia['link']})", unsafe_allow_html=True)
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
        st.success(f"🎯 {len(guias)} guias relevantes encontradas para {mes:02d}/{ano}:")

        for guia in guias:
            st.markdown("---")
            st.markdown(f"📄 **Número da guia:** `{guia['numero']}`")
            st.markdown(f"📅 **Data de emissão:** `{guia['data_emissao'][:10]}`")
            st.markdown(f"🚗 **Placa:** `{guia['placa']}`")
            st.markdown(f"📌 **Situação:** `{guia['situacao']}`")
            st.markdown(f"[🔗 Visualizar PDF]({guia['link']})", unsafe_allow_html=True)
    else:
        st.warning("🚫 Nenhuma guia relevante encontrada para o mês selecionado.")



# 📱 Interface principal com abas
st.set_page_config(page_title="Consulta de Guias", layout="centered")
st.title("🌳 Sistema de Consulta de Guias Florestais")


# Se você quiser manter isso fora da função e entre sessões:
if "ultima_atualizacao" not in st.session_state:
    st.session_state["ultima_atualizacao"] = None

#if st.button('🔄 Atualizar Dados'):
    #novos = atualizar_dados()

    #if novos:
        #st.success(f"{len(novos)} novos registros adicionados.")
    #else:
        #st.info("Nenhum novo dado encontrado.")

    # ⏰ Atualiza o horário da última execução
    #st.session_state["ultima_atualizacao"] = datetime.now()

# 🕓 Exibe horário da última atualização
#if st.session_state["ultima_atualizacao"]:
    #horario = st.session_state["ultima_atualizacao"].strftime("%d/%m/%Y %H:%M:%S")
    #st.caption(f"🕓 Última atualização: {horario}")


tabs = st.tabs(["🔎 Por Placa", "⭐ Relevantes do Mês"])

with tabs[0]:
    consultar_por_placa()

with tabs[1]:
    consultar_relevantes_por_mes()
