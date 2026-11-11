"""Dashboard conversacional de análise de pedidos de delivery com IA."""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.data import load_csv, load_sample
from src.pipeline import answer_question

load_dotenv()

st.set_page_config(page_title="Delivery Analytics AI", page_icon="🍔", layout="wide")
st.title("🍔 Delivery Analytics AI")
st.caption("Pergunte em português sobre os dados de pedidos e receba números, gráficos e insights.")

PROVIDERS = {"Groq (gratuito)": "groq", "Anthropic (Claude)": "anthropic"}

EXAMPLES = [
    "Qual horário do dia tem a maior taxa de atraso?",
    "Como a chuva afeta o tempo de entrega?",
    "Qual categoria de restaurante tem o maior ticket médio?",
    "Qual bairro tem as piores avaliações?",
    "Mostre a evolução de pedidos por semana",
]

with st.sidebar:
    st.header("Configuração")
    provider_label = st.selectbox("Provedor de IA", list(PROVIDERS), index=0)
    provider = PROVIDERS[provider_label]
    env_var = "GROQ_API_KEY" if provider == "groq" else "ANTHROPIC_API_KEY"
    api_key = st.text_input(
        "Chave da API",
        type="password",
        value=os.getenv(env_var, ""),
        help="Fica apenas na sua sessão. Também pode ser definida no arquivo .env.",
    )
    if provider == "groq":
        st.caption("Chave gratuita, sem cartão: [console.groq.com](https://console.groq.com/keys)")
    else:
        st.caption("Chave paga: [console.anthropic.com](https://console.anthropic.com/)")
    source = st.radio("Fonte dos dados", ["Dataset de exemplo", "Enviar meu CSV"])
    uploaded = st.file_uploader("CSV", type="csv") if source == "Enviar meu CSV" else None


@st.cache_data
def get_sample() -> pd.DataFrame:
    return load_sample()


if uploaded is not None:
    df = load_csv(uploaded)
elif source == "Dataset de exemplo":
    df = get_sample()
else:
    st.info("Envie um CSV na barra lateral para começar.")
    st.stop()

# --- Métricas rápidas ---
cols = st.columns(4)
cols[0].metric("Pedidos", f"{len(df):,}".replace(",", "."))
if "delayed" in df.columns:
    cols[1].metric("Taxa de atraso", f"{df['delayed'].mean() * 100:.1f}%")
if "delivery_time_min" in df.columns:
    cols[2].metric("Tempo médio (min)", f"{df['delivery_time_min'].mean():.1f}")
if "rating" in df.columns:
    cols[3].metric("Avaliação média", f"{df['rating'].mean():.2f}")

with st.expander("Ver amostra dos dados"):
    st.dataframe(df.head(50), use_container_width=True)

# --- Perguntas ---
st.subheader("Pergunte aos dados")
chosen = st.pills("Exemplos", EXAMPLES) if hasattr(st, "pills") else None
question = st.chat_input("Ex.: qual horário tem mais atraso?") or chosen

if "history" not in st.session_state:
    st.session_state.history = []

if question:
    if not api_key:
        st.error("Informe a chave da API na barra lateral.")
        st.stop()
    with st.spinner("Analisando os dados..."):
        try:
            st.session_state.history.append(answer_question(question, df, api_key, provider))
        except Exception as exc:  # erros de rede, chave inválida etc.
            st.error(f"Falha ao consultar o modelo: {exc}")

for ans in reversed(st.session_state.history):
    with st.container(border=True):
        st.markdown(f"**🙋 {ans.question}**")
        if ans.error:
            st.error(f"Não consegui responder: {ans.error}")
        else:
            st.markdown(ans.explanation)
            if isinstance(ans.result, (pd.DataFrame, pd.Series)):
                st.dataframe(ans.result, use_container_width=True)
            else:
                st.write(ans.result)
            if ans.fig is not None:
                st.plotly_chart(ans.fig, use_container_width=True)
        with st.expander(f"Ver código gerado (tentativas: {ans.attempts})"):
            st.code(ans.code, language="python")
