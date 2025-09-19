import streamlit as st

st.set_page_config(layout="wide")
st.title("Teste de Diagnóstico de Secrets")

# Tentativa 1: Acessar diretamente (causa o KeyError se não existir)
st.subheader("Teste 1: Acesso Direto")
try:
    api_key_direct = st.secrets["GEMINI_API_KEY"]
    st.success("Chave encontrada com sucesso via acesso direto!")
    st.write(f"Os primeiros 5 caracteres da sua chave são: `{api_key_direct[:5]}...`")
except KeyError:
    st.error("ERRO: A chave 'GEMINI_API_KEY' não foi encontrada via acesso direto. Verifique o nome da chave nos Secrets.")
except Exception as e:
    st.error(f"Um erro inesperado ocorreu: {e}")

st.divider()

# Tentativa 2: Acessar com o método .get() (mais seguro)
st.subheader("Teste 2: Acesso Seguro com .get()")
api_key_get = st.secrets.get("GEMINI_API_KEY")

if api_key_get:
    st.success("Chave encontrada com sucesso via método .get()!")
    st.write(f"Os primeiros 5 caracteres da sua chave são: `{api_key_get[:5]}...`")
else:
    st.error("ERRO: O método .get('GEMINI_API_KEY') retornou Nulo (None).")
    st.warning("Isso confirma que o Secret não está configurado corretamente ou o nome está errado.")

st.divider()

st.info("Se ambos os testes falharem, o problema é 100% na configuração dos Secrets no painel do Streamlit Cloud. Verifique novamente o nome da chave e o formato.")
