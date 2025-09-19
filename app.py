import streamlit as st
import pandas as pd
import google.generativeai as genai
import PyPDF2
from io import BytesIO
import datetime
import traceback

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Market Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VALIDAÇÃO DA CHAVE DA API (VERSÃO FINAL E MAIS SEGURA) ---
# Usamos o método .get() que é mais seguro e não causa KeyError
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Ocorreu um erro ao configurar a API do Gemini. Verifique se a sua chave é válida. Erro: {e}")
        st.stop()
else:
    st.error("Chave da API do Gemini não foi encontrada!")
    st.error("Por favor, adicione sua GEMINI_API_KEY nos 'Secrets' da aplicação no Streamlit Cloud.")
    st.info("No menu 'Manage app' > Settings > Secrets, adicione a linha: GEMINI_API_KEY='SUA_CHAVE_AQUI'")
    st.stop()

# --- FUNÇÕES CORE ---
# ... (o resto do seu código continua exatamente como estava) ...

# --- FUNÇÕES CORE ---

def extrair_texto_pdf(arquivo_pdf):
    """Extrai texto de um arquivo PDF carregado pelo Streamlit."""
    texto_completo = ""
    try:
        leitor_pdf = PyPDF2.PdfReader(BytesIO(arquivo_pdf.read()))
        for pagina in leitor_pdf.pages:
            texto_completo += pagina.extract_text() or ""
    except Exception as e:
        st.error(f"Erro ao ler o arquivo PDF: {e}")
        return None
    return texto_completo

def extrair_dados_com_ia(texto_pdf):
    """Envia o texto para a API do Gemini e pede para extrair as informações."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Você é um analista de investimentos sênior. Sua tarefa é analisar o texto de um relatório de mercado e extrair as principais visões de investimento da gestora.
    Para cada visão que identificar, retorne a informação em um formato de lista de dicionários Python.
    Siga estritamente esta estrutura para cada dicionário:
    {"nome_gestora": "Nome da Gestora", "data_relatorio": "Data ou período do relatório (ex: Setembro 2025)", "pais_regiao": "País ou Região analisada", "classe_ativo": "Classe de Ativo principal", "subclasse_ativo": "Se mencionado, a Subclasse do ativo", "visao_sentimento": "Otimista, Neutro ou Pessimista", "tese_principal": "A citação ou resumo conciso que justifica a visão"}
    
    Extraia múltiplas visões se houver. Se uma informação não for encontrada, retorne um campo vazio ou "não encontrado".
    O texto para análise é o seguinte:
    ---
    {}
    ---
    """.format(texto_pdf)
    
    try:
        response = model.generate_content(prompt)
        # Limpa a resposta para garantir que seja um formato 'eval' válido
        clean_response = response.text.strip().replace("```python", "").replace("```", "").strip()
        
        # Tenta converter a string da resposta para uma lista de dicionários
        dados_extraidos = eval(clean_response)
        
        # Validação extra: verifica se o resultado é uma lista
        if not isinstance(dados_extraidos, list):
            st.warning("A IA não retornou uma lista. Tentando corrigir...")
            # Se não for uma lista, talvez seja um único dicionário. Colocamos dentro de uma lista.
            if isinstance(dados_extraidos, dict):
                return [dados_extraidos]
            else:
                return None # Se não for nem lista nem dicionário, falhou.

        return dados_extraidos
    except Exception as e:
        st.error(f"Erro ao processar a resposta da IA. Verifique o formato retornado.")
        st.error(f"Detalhes do erro: {e}")
        st.text_area("Resposta bruta da IA que causou o erro:", response.text, height=200)
        traceback.print_exc() # Imprime o traceback completo nos logs
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
