import streamlit as st
import pandas as pd
import google.generativeai as genai
import PyPDF2
from io import BytesIO, StringIO
import datetime

# --- CONFIGURAÇÃO E VALIDAÇÃO DA CHAVE API ---
st.set_page_config(
    page_title="Market Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Chave da API do Gemini não configurada! Adicione `GEMINI_API_KEY` nos Secrets da aplicação.")
    st.stop()

# --- FUNÇÕES CORE ---

@st.cache_data
def extrair_texto_pdf(arquivo_pdf_bytes, nome_arquivo):
    """Extrai texto do documento PDF inteiro."""
    try:
        texto_completo = ""
        leitor_pdf = PyPDF2.PdfReader(BytesIO(arquivo_pdf_bytes))
        for pagina in leitor_pdf.pages:
            texto_completo += pagina.extract_text() or ""
        return texto_completo
    except Exception as e:
        st.error(f"Erro ao ler o arquivo PDF '{nome_arquivo}': {e}")
        return None

@st.cache_data
def extrair_dados_com_ia(_texto_pdf):
    """Envia o texto para a API do Gemini e retorna os dados estruturados."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = """
    Analise o texto do relatório de mercado a seguir. Sua tarefa é extrair as visões de investimento.
    Retorne uma lista de dicionários Python, com cada dicionário representando uma visão específica.
    Use estritamente as seguintes chaves: "data_relatorio", "nome_gestora", "pais_regiao", "classe_ativo", "subclasse_ativo", "visao_sentimento", "tese_principal".
    - "visao_sentimento" deve ser apenas "Otimista", "Neutro" ou "Pessimista".
    - Se uma informação não for encontrada, use um campo vazio "".
    - "data_relatorio" deve ser o mês/ano ou data do relatório.
    O texto para análise é:
    ---
    {}
    ---
    """.format(_texto_pdf)
    
    try:
        response = model.generate_content(prompt)
        clean_response = response.text.strip().replace("```python", "").replace("```", "").strip()
        dados_extraidos = eval(clean_response)
        if isinstance(dados_extraidos, list) and all(isinstance(d, dict) for d in dados_extraidos):
            return dados_extraidos
        else:
            st.error("A IA não retornou os dados no formato esperado (lista de dicionários).")
            return None
    except Exception as e:
        st.error(f"Erro ao processar a resposta da IA: {e}")
        st.text_area("Resposta bruta da IA que causou o erro:", response.text, height=200)
        return None

# --- NAVEGAÇÃO E PÁGINAS ---

st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Escolha uma página", ["Macro View", "Assets View", "Admin: Processar Relatório"])

try:
    df = pd.read_csv("market_intelligence_db.csv")
except FileNotFoundError:
    st.sidebar.error("Arquivo 'market_intelligence_db.csv' não encontrado.")
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
                # **INÍCIO DO BLOCO CORRIGIDO**
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
                # **FIM DO BLOCO CORRIGIDO**

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
                # **INÍCIO DO BLOCO CORRIGIDO**
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
                # **FIM DO BLOCO CORRIGIDO**

elif pagina == "Admin: Processar Relatório":
    st.title("⚙️ Admin: Extrair Dados de um Novo Relatório")
    uploaded_file = st.file_uploader("1. Faça o upload do relatório em PDF", type="pdf")
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.getvalue()
        texto_pdf = extrair_texto_pdf(pdf_bytes, uploaded_file.name)
        if texto_pdf:
            st.subheader("2. Análise com Inteligência Artificial")
            if st.button("Analisar Documento Completo"):
                with st.spinner("A IA está lendo e analisando o relatório... Isso pode levar um minuto."):
                    dados_extraidos = extrair_dados_com_ia(texto_pdf)
                if dados_extraidos:
                    st.success("Análise concluída com sucesso!")
                    st.subheader("3. Resultados da Extração")
                    df_novos_dados = pd.DataFrame(dados_extraidos)
                    df_novos_dados['data_extracao'] = datetime.date.today().strftime("%Y-%m-%d")
                    df_novos_dados['fonte_documento'] = uploaded_file.name
                    ordem_colunas = ['data_extracao', 'data_relatorio', 'nome_gestora', 'fonte_documento', 'pais_regiao', 'classe_ativo', 'subclasse_ativo', 'visao_sentimento', 'tese_principal']
                    # Garante que todas as colunas existam, preenchendo com "" se faltar
                    for col in ordem_colunas:
                        if col not in df_novos_dados.columns:
                            df_novos_dados[col] = ""
                    df_novos_dados = df_novos_dados[ordem_colunas]
                    st.dataframe(df_novos_dados)
                    st.subheader("4. Adicionar ao Banco de Dados")
                    st.warning("A atualização automática no GitHub ainda não está implementada.")
                    output = StringIO()
                    df_novos_dados.to_csv(output, index=False, header=False)
                    csv_string = output.getvalue()
                    st.text_area(
                        "Copie o texto abaixo e cole no final do seu arquivo `market_intelligence_db.csv` no GitHub:",
                        csv_string,
                        height=200
                    )
