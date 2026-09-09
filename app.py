import streamlit as st
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

def normalizar_texto(texto):
    """Remove acentos e converte para letras minúsculas."""
    if not texto:
        return ""
    # Normaliza os caracteres (separa letras de acentos) e remove os acentos
    texto_sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto_sem_acento.lower().strip()

# ---------- Componentes ----------
def exibir_card(guia):
    qtd_esp = guia.get('num_especie', 'N/A')
    
    # Formata a lista de espécies para exibição no card
    lista_esp = guia.get('nomes_especies')
    nomes_formatados = ", ".join(lista_esp) if lista_esp else "Não identificadas"

    st.markdown(f"""
    <div class="card">
        <p><b>📄 Número da guia:</b> {guia['numero']}</p>
        <p><b>📅 Data de emissão:</b> {guia['data_emissao'][:10]}</p>
        <p><b>🚗 Placa:</b> {guia['placa']}</p>
        <p><b>🌱 Espécies ({qtd_esp}):</b> {nomes_formatados}</p>
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

    # Organizando os filtros em 4 colunas para otimizar o espaço na tela
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

    # Tratamento das datas para a query
    data_inicio = f"{ano}-{mes:02d}-01"
    if mes == 12:
        data_fim = f"{ano + 1}-01-01"
    else:
        data_fim = f"{ano}-{mes + 1:02d}-01"

    # Construção da query no banco de dados
    # Nota: A coluna 'nomes_especies' foi adicionada ao select
    query = (
        supabase.table("guias_florestais")
        .select("numero, data_emissao, situacao, placa, link, num_especie, nomes_especies")
        .eq("relevante", True)
        .gte("data_emissao", data_inicio)
        .lt("data_emissao", data_fim)
    )
    
    if min_especies > 0:
        query = query.gte("num_especie", min_especies)

    resposta = query.order("data_emissao", desc=True).execute()
    guias = resposta.data

    # Exibição dos resultados
    if guias:
        st.info(f"📋 Mostrando {len(guias)} guias encontradas.")
        for guia in guias:
            exibir_card(guia)
    else:
        st.warning("🚫 Nenhuma guia relevante encontrada para os filtros selecionados.")

def aba_busca_especie():
    st.subheader("🌿 Busca Específica por Espécie (Rota Tocantins)")

    col1, col2, col3 = st.columns([2, 2, 4])

    with col1:
        meses = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, 
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, 
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        mes_atual = datetime.today().month
        mes_selecionado = st.selectbox("Mês", list(meses.keys()), index=mes_atual - 1, key="mes_busca_esp")
        mes = meses[mes_selecionado]

    with col2:
        ano_atual = datetime.today().year
        ano = st.selectbox("Ano", [ano_atual, ano_atual - 1, ano_atual - 2], key="ano_busca_esp")

    with col3:
        especie_filtro = st.text_input("Nome da Espécie", placeholder="Ex: cupiuba (sem acento)")

    data_inicio = f"{ano}-{mes:02d}-01"
    if mes == 12:
        data_fim = f"{ano + 1}-01-01"
    else:
        data_fim = f"{ano}-{mes + 1:02d}-01"

    if especie_filtro:
        # Consulta COM o filtro de rota Tocantins ativo
        query = (
            supabase.table("guias_florestais")
            .select("numero, data_emissao, situacao, placa, link, num_especie, nomes_especies, relevante")
            .eq("relevante", True)  # Filtro mantido conforme solicitado
            .gte("data_emissao", data_inicio)
            .lt("data_emissao", data_fim)
            .order("data_emissao", desc=True)
            .execute()
        )
        
        guias = query.data
        guias_filtradas = []
        termo_busca = normalizar_texto(especie_filtro)

        for guia in guias:
            nomes_raw = guia.get('nomes_especies')
            
            # Tratamento híbrido: funciona para text antigo e para o novo jsonb
            if isinstance(nomes_raw, str):
                try:
                    lista_especies = json.loads(nomes_raw)
                except json.JSONDecodeError:
                    lista_especies = []
            elif isinstance(nomes_raw, list):
                lista_especies = nomes_raw
            else:
                lista_especies = []
            
            # Verifica se a espécie buscada está na lista extraída da guia
            if any(termo_busca in normalizar_texto(esp) for esp in lista_especies):
                guias_filtradas.append(guia)

        if guias_filtradas:
            st.success(f"🔎 Encontradas {len(guias_filtradas)} guias relevantes transportando a espécie selecionada.")
            for guia in guias_filtradas:
                exibir_card(guia)
        else:
            st.warning("🚫 Nenhuma guia com rota Tocantins foi encontrada transportando essa espécie no período selecionado.")
    else:
        st.info("👆 Digite o nome de uma espécie para iniciar a busca.")

# ---------- Interface principal ----------
st.title("🌳 Consulta de Guias Florestais")
tabs = st.tabs(["🔎 Busca por Placa", "⭐ Guias Relevantes", "🌿 Busca por Espécie"])

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

with tabs[2]:
    # A nova aba dedicada entra aqui
    aba_busca_especie()