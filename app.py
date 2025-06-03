import pandas as pd
import re
import streamlit as st
import json
import io

st.set_page_config(page_title="Extrator de Atributos", layout="wide")
st.title("🔍 Sistema de Extração de Atributos Avançado")

# Sessão de estados persistentes
if 'atributos' not in st.session_state:
    st.session_state['atributos'] = {}

# Carregar arquivo Excel
dados_originais = None
uploaded_file = st.file_uploader("📤 Envie uma planilha (.xlsx) com colunas 'ID' e 'Descrição'", type=[".xlsx"])

if uploaded_file:
    try:
        dados_originais = pd.read_excel(uploaded_file)
        if 'ID' not in dados_originais.columns or 'Descrição' not in dados_originais.columns:
            st.error("A planilha deve conter as colunas 'ID' e 'Descrição'")
            dados_originais = None
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {str(e)}")

# Aba lateral para configuração de atributos
st.sidebar.header("⚙️ Configurar Atributos")
nome_atributo = st.sidebar.text_input("Nome do Atributo")

with st.sidebar.expander("Variações e Padrões"):
    variacoes_raw = st.text_area("Digite as variações e padrões (ex: 110V: 110,110v,127\n220V: 220,220v)")

tipo_retorno = st.sidebar.selectbox("Formato de Retorno", ["valor", "texto", "completo"])

if st.sidebar.button("Adicionar Atributo"):
    if nome_atributo and variacoes_raw:
        variacoes = []
        for linha in variacoes_raw.splitlines():
            if ':' in linha:
                desc, pad = linha.split(':', 1)
                padroes = [p.strip() for p in pad.split(',') if p.strip()]
                variacoes.append({"descricao": desc.strip(), "padroes": padroes})
        st.session_state['atributos'][nome_atributo] = {
            "tipo_retorno": tipo_retorno,
            "variacoes": variacoes
        }
        st.sidebar.success("Atributo adicionado com sucesso!")

if st.sidebar.button("Limpar Atributos"):
    st.session_state['atributos'] = {}

# Mostrar atributos configurados
if st.session_state['atributos']:
    st.subheader("🧩 Atributos Configurados")
    for nome, cfg in st.session_state['atributos'].items():
        st.markdown(f"**{nome}** - Retorno: `{cfg['tipo_retorno']}`")
        for v in cfg['variacoes']:
            st.markdown(f"- {v['descricao']}: `{', '.join(v['padroes'])}`")

# Processar planilha
if dados_originais is not None and st.session_state['atributos']:
    st.subheader("✅ Resultado da Extração")
    dados_processados = dados_originais.copy()

    for nome_attr, config in st.session_state['atributos'].items():
        tipo_retorno = config['tipo_retorno']
        variacoes = config['variacoes']
        regex_variacoes = []
        for var in variacoes:
            regex = r"\b(" + "|".join(re.escape(p) for p in var['padroes']) + r")\b"
            regex_variacoes.append((regex, var['descricao']))
        resultados = []
        for desc in dados_processados['Descrição']:
            desc_lower = str(desc).lower()
            valor = ""
            for regex, descricao in regex_variacoes:
                match = re.search(regex, desc_lower, re.IGNORECASE)
                if match:
                    if tipo_retorno == "valor":
                        numeros = re.findall(r"\d+", match.group(1))
                        valor = numeros[0] if numeros else ""
                    elif tipo_retorno == "texto":
                        valor = descricao
                    elif tipo_retorno == "completo":
                        valor = f"{nome_attr}: {descricao}"
                    break
            resultados.append(valor)
        dados_processados[nome_attr] = resultados

    st.dataframe(dados_processados)

    buffer = io.BytesIO()
    dados_processados.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar Resultados",
        data=buffer,
        file_name="resultados_extracao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Envie uma planilha e configure os atributos para iniciar a extração.")
