import streamlit as st
import pandas as pd
import google.generativeai as genai
import PyPDF2
from io import BytesIO
import datetime

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Market Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CHAVE DA API ---
# Para o deploy no Streamlit Cloud, adicione a chave como um "Secret"
# st.secrets['GEMINI_API_KEY']
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except FileNotFoundError:
    # Este bloco é para rodar localmente, caso você crie um arquivo secrets.toml
    st.warning("Arquivo de secrets não encontrado. Crie um arquivo .streamlit/secrets.toml para desenvolvimento local.")
    st.stop()
except KeyError:
    st.error("Chave da API do Gemini não encontrada. Configure o 'GEMINI_API_KEY' nos Secrets do Streamlit Cloud.")
    st.stop()


# --- FUNÇÕES CORE ---

def extrair_texto_pdf(arquivo_pdf):
    """Extrai texto de um arquivo PDF carregado pelo Streamlit."""
    texto_completo = ""
    leitor_pdf = PyPDF2.PdfReader(BytesIO(arquivo_pdf.read()))
    for pagina in leitor_pdf.pages:
        texto_completo += pagina.extract_text()
    return texto_completo

def extrair_dados_com_ia(texto_pdf):
    """Envia o texto para a API do Gemini e pede para extrair as informações."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Você é um analista de investimentos sênior. Sua tarefa é analisar o texto de um relatório de mercado e extrair as principais visões de investimento da gestora.
    Para cada visão que identificar, retorne a informação em um formato de lista de dicionários Python.
    Siga estritamente esta estrutura para cada dicionário:
    {"nome_gestora": "Nome da Gestora", "pais_regiao": "País ou Região analisada", "classe_ativo": "Classe de Ativo principal", "subclasse_ativo": "Se mencionado, a Subclasse do ativo", "visao_sentimento": "Otimista, Neutro ou Pessimista", "tese_principal": "A citação ou resumo conciso que justifica a visão"}
    
    Extraia múltiplas visões se houver. Se uma informação como 'subclasse_ativo' não for encontrada, retorne um campo vazio.
    O texto para análise é o seguinte:
    ---
    {}
    ---
    """.format(texto_pdf)
    
    try:
        response = model.generate_content(prompt)
        # O Gemini pode retornar o texto formatado como markdown, então precisamos limpá-lo.
        clean_response = response.text.strip().replace("```python", "").replace("```", "").strip()
        # Converte a string da resposta em uma lista de dicionários Python real
        dados_extraidos = eval(clean_response)
        return dados_extraidos
    except Exception as e:
        st.error(f"Erro ao chamar a API do Gemini: {e}")
        st.error(f"Resposta recebida: {response.text}")
        return None

# --- NAVEGAÇÃO E PÁGINAS ---

st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Escolha uma página", ["Macro View", "Assets View", "Admin: Upload de Relatórios"])

# Carregar o banco de dados
try:
    df = pd.read_csv("market_intelligence_db.csv")
except FileNotFoundError:
    st.sidebar.error("Arquivo 'market_intelligence_db.csv' não encontrado. Crie-o no repositório.")
    st.stop()

if pagina == "Macro View":
    st.title("🌎 Macro View - Análise por País/Região")

    paises = df['pais_regiao'].dropna().unique()
    pais_selecionado = st.selectbox("Selecione uma Região", sorted(paises))

    if pais_selecionado:
        df_filtrado = df[df['pais_regiao'] == pais_selecionado]
        st.subheader(f"Visões para {pais_selecionado}")

        if df_filtrado.empty:
            st.info("Nenhuma visão encontrada para esta região.")
        else:
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Gestora:** {row['nome_gestora']}")
                        st.markdown(f"**Ativo:** {row['classe_ativo']} ({row.get('subclasse_ativo', 'N/A')})")
                        st.info(f"**Tese:** {row['tese_principal']}")
                    with col2:
                        sentimento = row['visao_sentimento']
                        if sentimento == 'Otimista':
                            st.success(f"**Visão: {sentimento}**")
                        elif sentimento == 'Pessimista':
                            st.error(f"**Visão: {sentimento}**")
                        else:
                            st.warning(f"**Visão: {sentimento}**")
                        st.caption(f"Fonte: {row['fonte_documento']}")


elif pagina == "Assets View":
    st.title("📊 Assets View - Análise por Classe de Ativo")
    
    classes = df['classe_ativo'].dropna().unique()
    classe_selecionada = st.selectbox("Selecione uma Classe de Ativo", sorted(classes))

    if classe_selecionada:
        df_filtrado = df[df['classe_ativo'] == classe_selecionada]
        st.subheader(f"Visões para {classe_selecionada}")

        if df_filtrado.empty:
            st.info("Nenhuma visão encontrada para esta classe de ativo.")
        else:
            for index, row in df_filtrado.iterrows():
                 with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Gestora:** {row['nome_gestora']}")
                        st.markdown(f"**Região:** {row['pais_regiao']}")
                        st.info(f"**Tese:** {row['tese_principal']}")
                    with col2:
                        sentimento = row['visao_sentimento']
                        if sentimento == 'Otimista':
                            st.success(f"**Visão: {sentimento}**")
                        elif sentimento == 'Pessimista':
                            st.error(f"**Visão: {sentimento}**")
                        else:
                            st.warning(f"**Visão: {sentimento}**")
                        st.caption(f"Fonte: {row['fonte_documento']}")


elif pagina == "Admin: Upload de Relatórios":
    st.title("⚙️ Admin: Upload e Processamento de Relatórios")
    st.warning("Atenção: A funcionalidade de salvar os dados extraídos diretamente no GitHub ainda não foi implementada. Por enquanto, esta página apenas exibe os dados extraídos.")

    uploaded_file = st.file_uploader("Escolha um relatório em PDF", type="pdf")

    if uploaded_file is not None:
        if st.button("Processar Relatório com IA"):
            with st.spinner("Extraindo texto do PDF..."):
                texto_pdf = extrair_texto_pdf(uploaded_file)
                st.text_area("Texto Extraído (primeiros 1000 caracteres)", texto_pdf[:1000] + "...", height=150)

            with st.spinner("Analisando com a IA do Gemini... Isso pode levar um momento."):
                dados_extraidos = extrair_dados_com_ia(texto_pdf)

            if dados_extraidos:
                st.success("Dados extraídos com sucesso!")
                df_novos_dados = pd.DataFrame(dados_extraidos)
                
                # Adicionar colunas de metadados
                df_novos_dados['data_extracao'] = datetime.date.today().strftime("%Y-%m-%d")
                df_novos_dados['fonte_documento'] = uploaded_file.name
                
                # Para o futuro: aqui viria a lógica para salvar no CSV do GitHub
                st.subheader("Pré-visualização dos Dados para Salvar")
                st.dataframe(df_novos_dados)
                
                st.info("Para adicionar estes dados à plataforma, copie-os e cole-os manualmente no arquivo 'market_intelligence_db.csv' no GitHub por enquanto.")
