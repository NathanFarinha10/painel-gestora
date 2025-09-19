import streamlit as st
import pandas as pd
import google.generativeai as genai
import PyPDF2
from io import BytesIO, StringIO
import datetime
import json
import requests
import base64 

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

# Token de Acesso do GitHub
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    st.error("Token do GitHub não configurado! Adicione `GITHUB_TOKEN` nos Secrets para a automação funcionar.")
    st.stop()

# --- CONFIGURAÇÃO DO GITHUB (VOCÊ PRECISA EDITAR ISSO) ---
REPO_OWNER = "NathanFarinha10"  # Ex: "fulanodasilva"
REPO_NAME = "painel-gestora"       # Ex: "painel-gestora"
FILE_PATH = "market_intelligence_db.csv"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

# --- FUNÇÕES CORE (REATORADAS) ---

# A função de extrair texto do PDF permanece a mesma
@st.cache_data
def extrair_texto_pdf(arquivo_pdf_bytes, nome_arquivo):
    try:
        texto_completo = ""
        leitor_pdf = PyPDF2.PdfReader(BytesIO(arquivo_pdf_bytes))
        for pagina in leitor_pdf.pages:
            texto_completo += pagina.extract_text() or ""
        return texto_completo
    except Exception as e:
        st.error(f"Erro ao ler o arquivo PDF '{nome_arquivo}': {e}")
        return None

# Função de extração com IA foi refatorada para ser mais segura e não ter widgets
@st.cache_data
def extrair_dados_com_ia(_texto_pdf):
    """
    Chama a IA para extrair dados.
    Retorna uma tupla: (dados, erro, resposta_bruta).
    - Em caso de sucesso: (lista_de_dicionarios, None, None)
    - Em caso de falha: (None, mensagem_de_erro, resposta_da_ia)
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = """
    Analise o texto do relatório de mercado a seguir. Sua tarefa é extrair as visões de investimento.
    Retorne sua resposta como uma string JSON válida, contendo uma lista de objetos.
    Cada objeto deve ter estritamente as seguintes chaves: "data_relatorio", "nome_gestora", "pais_regiao", "classe_ativo", "subclasse_ativo", "visao_sentimento", "tese_principal".
    - "visao_sentimento" deve ser apenas "Otimista", "Neutro" ou "Pessimista".
    - Se uma informação não for encontrada, use um campo vazio "".
    - Se nenhuma visão de investimento for encontrada no texto, retorne uma lista vazia [].
    O texto para análise é:
    ---
    {}
    ---
    """.format(_texto_pdf)
    
    try:
        response = model.generate_content(prompt)
        # Limpa a resposta para garantir que seja um JSON válido
        clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        # Usa json.loads(), que é muito mais seguro que eval()
        dados_extraidos = json.loads(clean_response)
        
        if isinstance(dados_extraidos, list):
            return dados_extraidos, None, None
        else:
            return None, "A IA não retornou uma lista no JSON.", clean_response
            
    except json.JSONDecodeError:
        return None, "A IA retornou um JSON inválido. Não foi possível decodificar.", response.text
    except Exception as e:
        return None, f"Ocorreu um erro inesperado: {e}", response.text

def update_csv_on_github(novas_linhas_csv):
    """
    Função para buscar o CSV no GitHub, adicionar novas linhas e salvar de volta.
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Obter o conteúdo atual do arquivo e seu SHA (obrigatório para atualização)
    try:
        response = requests.get(GITHUB_API_URL, headers=headers)
        response.raise_for_status() # Lança um erro se a requisição falhar (ex: 404 Not Found)
        
        file_data = response.json()
        content_base64 = file_data["content"]
        sha = file_data["sha"]
        
        # 2. Decodificar o conteúdo de Base64 para texto
        conteudo_atual = base64.b64decode(content_base64).decode("utf-8")
        
        # 3. Adicionar as novas linhas ao conteúdo existente
        conteudo_final = conteudo_atual + "\n" + novas_linhas_csv.strip()
        
        # 4. Codificar o novo conteúdo de volta para Base64
        novo_conteudo_base64 = base64.b64encode(conteudo_final.encode("utf-8")).decode("utf-8")
        
        # 5. Preparar os dados para a requisição de atualização (PUT)
        data = {
            "message": f"Atualização automática do DB via Streamlit App - {datetime.date.today()}",
            "content": novo_conteudo_base64,
            "sha": sha # Informa ao GitHub qual versão do arquivo estamos atualizando
        }
        
        update_response = requests.put(GITHUB_API_URL, headers=headers, json=data)
        update_response.raise_for_status() # Lança um erro se a atualização falhar
        
        return True, "Arquivo atualizado com sucesso no GitHub!"
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return False, f"Erro: Arquivo '{FILE_PATH}' não encontrado. Verifique o caminho e nome do repositório."
        return False, f"Erro de HTTP ao comunicar com o GitHub: {e}"
    except Exception as e:
        return False, f"Ocorreu um erro inesperado na automação: {e}"

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
    st.title("⚙️ Admin: Extrair Dados e Atualizar a Base")

    uploaded_file = st.file_uploader("1. Faça o upload do relatório em PDF", type="pdf")

    if uploaded_file is not None:
        if st.button("Analisar e Salvar no GitHub"):
            
            with st.spinner("Lendo o PDF..."):
                pdf_bytes = uploaded_file.getvalue()
                texto_pdf = extrair_texto_pdf(pdf_bytes, uploaded_file.name)
            
            if texto_pdf:
                with st.spinner("Analisando com IA e preparando dados..."):
                    dados, erro, resposta_bruta = extrair_dados_com_ia(texto_pdf)
                
                if erro:
                    st.error(f"**Falha na Extração:** {erro}")
                    st.text_area("Resposta bruta da IA:", resposta_bruta, height=200)
                elif not dados:
                     st.warning("Nenhuma visão de investimento foi encontrada no documento.")
                else:
                    st.success("Dados extraídos com sucesso pela IA!")
                    df_novos_dados = pd.DataFrame(dados)
                    df_novos_dados['data_extracao'] = datetime.date.today().strftime("%Y-%m-%d")
                    df_novos_dados['fonte_documento'] = uploaded_file.name
                    
                    # Preparar as novas linhas em formato CSV
                    output = StringIO()
                    df_novos_dados.to_csv(output, index=False, header=False)
                    csv_string = output.getvalue()
                    
                    with st.spinner("Salvando dados no GitHub..."):
                        sucesso, mensagem = update_csv_on_github(csv_string)
                    
                    if sucesso:
                        st.success(mensagem)
                        st.balloons()
                        st.info("A aplicação irá recarregar para exibir os novos dados. Atualize a página se necessário.")
                    else:
                        st.error(f"**Falha ao salvar no GitHub:** {mensagem}")
