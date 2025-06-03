import pandas as pd
import re
import json
import streamlit as st
from io import BytesIO

class ExtratorAtributos:
    def __init__(self):
        self.atributos = {}
        self.dados_processados = pd.DataFrame()
        self.etapa_configuracao = 0  # 0=nome, 1=variações, 2=padrões, 3=prioridade, 4=formato
        self.atributo_atual = {}
        
        # Configuração inicial da página
        st.set_page_config(
            page_title="Sistema de Extração de Atributos",
            page_icon=":mag:",
            layout="wide"
        )
        
        self.setup_ui()
    
    def setup_ui(self):
        st.title("Sistema de Extração de Atributos de Produtos")
        
        # Abas principais
        tab1, tab2, tab3 = st.tabs(["Modelo e Upload", "Configuração", "Resultados"])
        
        with tab1:
            self.setup_aba_modelo()
        
        with tab2:
            self.setup_aba_configuracao()
        
        with tab3:
            self.setup_aba_resultados()
    
    def setup_aba_modelo(self):
        st.header("Modelo e Upload de Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Gerar Modelo")
            if st.button("Gerar Modelo Excel"):
                self.gerar_modelo()
        
        with col2:
            st.subheader("Upload de Planilha")
            uploaded_file = st.file_uploader("Selecione uma planilha Excel", type=["xlsx", "xls"])
            
            if uploaded_file is not None:
                try:
                    self.dados_originais = pd.read_excel(uploaded_file)
                    
                    if 'ID' not in self.dados_originais.columns or 'Descrição' not in self.dados_originais.columns:
                        st.error("A planilha deve conter as colunas 'ID' e 'Descrição'")
                    else:
                        st.success("Planilha carregada com sucesso!")
                        st.dataframe(self.dados_originais.head())
                except Exception as e:
                    st.error(f"Erro ao carregar planilha: {str(e)}")
    
    def setup_aba_configuracao(self):
        st.header("Configuração de Atributos")
        
        # Seção de instruções
        self.mostrar_instrucoes()
        
        # Seção de configuração do atributo atual
        self.configurar_atributo_atual()
        
        # Seção de atributos configurados
        st.subheader("Atributos Configurados")
        
        if not self.atributos:
            st.info("Nenhum atributo configurado ainda.")
        else:
            # Mostra tabela de atributos
            dados_tabela = []
            for nome, config in self.atributos.items():
                variacoes = ", ".join([v['descricao'] for v in config['variacoes']])
                prioridade = config['variacoes'][0]['descricao']  # Mostra a de maior prioridade
                formato = "Valor" if config['tipo_retorno'] == "valor" else "Texto" if config['tipo_retorno'] == "texto" else "Completo"
                dados_tabela.append([nome, variacoes, prioridade, formato])
            
            df_atributos = pd.DataFrame(dados_tabela, columns=["Atributo", "Variações", "Prioridade", "Formato"])
            st.dataframe(df_atributos, use_container_width=True)
            
            # Botões de gerenciamento
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                nome_editar = st.selectbox("Selecione para editar", [""] + list(self.atributos.keys()))
                if nome_editar and st.button("Editar"):
                    self.atributo_atual = self.atributos[nome_editar].copy()
                    self.etapa_configuracao = 0
                    st.experimental_rerun()
            
            with col2:
                nome_remover = st.selectbox("Selecione para remover", [""] + list(self.atributos.keys()))
                if nome_remover and st.button("Remover"):
                    del self.atributos[nome_remover]
                    st.experimental_rerun()
            
            with col3:
                if st.button("Limpar Todos"):
                    self.atributos = {}
                    st.experimental_rerun()
            
            with col4:
                st.download_button(
                    label="Exportar Configurações",
                    data=self.exportar_configuracoes_json(),
                    file_name="config_atributos.json",
                    mime="application/json"
                )
            
            st.file_uploader(
                "Importar Configurações",
                type=["json"],
                key="import_config",
                accept_multiple_files=False,
                on_change=self.importar_configuracoes
            )
    
    def mostrar_instrucoes(self):
        instrucoes = {
            0: "1. Digite o nome do atributo que deseja configurar (ex: 'Voltagem')\nO nome será usado como cabeçalho na planilha de resultados.",
            1: "2. Adicione as variações de descrição para este atributo (ex: '110V', '220V', 'Bivolt')\nCada variação será uma possível saída do sistema.",
            2: "3. Para cada variação, adicione os padrões de reconhecimento (um por linha)\nEstes são os textos que o sistema buscará na descrição do produto.",
            3: "4. Defina a ordem de prioridade das variações\nQuando vários padrões forem encontrados, o sistema usará a variação com maior prioridade.",
            4: "5. Selecione o formato de retorno para este atributo\nO sistema pode retornar apenas o valor, o texto padrão ou uma descrição completa."
        }
        
        st.info(instrucoes.get(self.etapa_configuracao, "Configuração concluída!"))
    
    def configurar_atributo_atual(self):
        st.subheader("Configuração do Atributo")
        
        if self.etapa_configuracao == 0:
            nome = st.text_input("Nome do Atributo:", value=self.atributo_atual.get('nome', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Cancelar", disabled=self.etapa_configuracao == 0):
                    self.cancelar_configuracao()
            with col2:
                if st.button("Avançar →", disabled=not nome.strip()):
                    self.atributo_atual = {'nome': nome.strip()}
                    self.etapa_configuracao += 1
                    st.experimental_rerun()
        
        elif self.etapa_configuracao == 1:
            default_variacoes = "\n".join([v['descricao'] for v in self.atributo_atual.get('variacoes', [])])
            variacoes = st.text_area(
                "Variações (uma por linha):", 
                value=default_variacoes,
                height=150
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Voltar"):
                    self.etapa_configuracao -= 1
                    st.experimental_rerun()
            with col2:
                if st.button("Avançar →", disabled=not variacoes.strip()):
                    variacoes_lista = [v.strip() for v in variacoes.split('\n') if v.strip()]
                    self.atributo_atual['variacoes'] = [{'descricao': v, 'padroes': []} for v in variacoes_lista]
                    self.etapa_configuracao += 1
                    st.experimental_rerun()
        
        elif self.etapa_configuracao == 2:
            tabs = st.tabs([v['descricao'] for v in self.atributo_atual['variacoes']])
            
            for idx, tab in enumerate(tabs):
                with tab:
                    default_padroes = "\n".join(self.atributo_atual['variacoes'][idx].get('padroes', []))
                    padroes = st.text_area(
                        f"Padrões para reconhecer '{self.atributo_atual['variacoes'][idx]['descricao']}':",
                        value=default_padroes,
                        height=100,
                        key=f"padroes_{idx}"
                    )
                    self.atributo_atual['variacoes'][idx]['padroes'] = [p.strip() for p in padroes.split('\n') if p.strip()]
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Voltar"):
                    self.etapa_configuracao -= 1
                    st.experimental_rerun()
            with col2:
                if st.button("Avançar →"):
                    # Verifica se todos os padrões foram preenchidos
                    for variacao in self.atributo_atual['variacoes']:
                        if not variacao['padroes']:
                            st.error(f"Por favor, informe pelo menos um padrão para '{variacao['descricao']}'")
                            return
                    self.etapa_configuracao += 1
                    st.experimental_rerun()
        
        elif self.etapa_configuracao == 3:
            st.write("Arraste para ordenar (a primeira tem maior prioridade):")
            
            # Cria lista ordenável
            variacoes = [v['descricao'] for v in self.atributo_atual['variacoes']]
            
            # Usa session_state para manter a ordem
            if 'ordem_variacoes' not in st.session_state:
                st.session_state.ordem_variacoes = variacoes
            
            # Permite reordenar
            for i, var in enumerate(st.session_state.ordem_variacoes):
                col1, col2 = st.columns([1, 10])
                with col1:
                    st.write(f"{i+1}.")
                with col2:
                    if st.button(f"↑", key=f"up_{i}", disabled=i==0):
                        if i > 0:
                            st.session_state.ordem_variacoes[i], st.session_state.ordem_variacoes[i-1] = st.session_state.ordem_variacoes[i-1], st.session_state.ordem_variacoes[i]
                            st.experimental_rerun()
                    if st.button(f"↓", key=f"down_{i}", disabled=i==len(st.session_state.ordem_variacoes)-1):
                        if i < len(st.session_state.ordem_variacoes)-1:
                            st.session_state.ordem_variacoes[i], st.session_state.ordem_variacoes[i+1] = st.session_state.ordem_variacoes[i+1], st.session_state.ordem_variacoes[i]
                            st.experimental_rerun()
                    st.write(var)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Voltar"):
                    self.etapa_configuracao -= 1
                    st.experimental_rerun()
            with col2:
                if st.button("Avançar →"):
                    # Reordena as variações conforme a prioridade
                    variacoes_ordenadas = []
                    for descricao in st.session_state.ordem_variacoes:
                        for variacao in self.atributo_atual['variacoes']:
                            if variacao['descricao'] == descricao:
                                variacoes_ordenadas.append(variacao)
                                break
                    
                    self.atributo_atual['variacoes'] = variacoes_ordenadas
                    self.etapa_configuracao += 1
                    st.experimental_rerun()
        
        elif self.etapa_configuracao == 4:
            tipo_retorno = st.radio(
                "Formato de retorno:",
                options=["valor", "texto", "completo"],
                format_func=lambda x: {
                    "valor": "Valor (ex: '110')",
                    "texto": "Texto Padrão (ex: '110V')",
                    "completo": "Descrição Completa (ex: 'Voltagem: 110V')"
                }[x],
                index={
                    "valor": 0,
                    "texto": 1,
                    "completo": 2
                }.get(self.atributo_atual.get('tipo_retorno', 'texto'), 0)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Voltar"):
                    self.etapa_configuracao -= 1
                    st.experimental_rerun()
            with col2:
                if st.button("Concluir"):
                    self.atributo_atual['tipo_retorno'] = tipo_retorno
                    
                    # Adiciona ao dicionário de atributos
                    self.atributos[self.atributo_atual['nome']] = self.atributo_atual
                    
                    # Reseta para nova configuração
                    self.etapa_configuracao = 0
                    self.atributo_atual = {}
                    st.success("Atributo configurado com sucesso!")
                    st.experimental_rerun()
    
    def cancelar_configuracao(self):
        self.etapa_configuracao = 0
        self.atributo_atual = {}
        st.experimental_rerun()
    
    def exportar_configuracoes_json(self):
        dados_export = {}
        for nome, config in self.atributos.items():
            dados_export[nome] = {
                'tipo_retorno': config['tipo_retorno'],
                'variacoes': []
            }
            
            for variacao in config['variacoes']:
                dados_export[nome]['variacoes'].append({
                    'descricao': variacao['descricao'],
                    'padroes': variacao['padroes']
                })
        
        return json.dumps(dados_export, indent=4, ensure_ascii=False)
    
    def importar_configuracoes(self):
        if "import_config" in st.session_state and st.session_state.import_config is not None:
            try:
                dados_import = json.load(st.session_state.import_config)
                
                # Valida a estrutura do arquivo
                if not isinstance(dados_import, dict):
                    st.error("Formato de arquivo inválido")
                    return
                
                # Limpa os atributos atuais
                self.atributos = {}
                
                # Importa cada atributo com validação
                for nome, config in dados_import.items():
                    if not isinstance(config, dict):
                        continue
                    
                    # Verifica se tem os campos obrigatórios
                    if 'tipo_retorno' not in config or 'variacoes' not in config:
                        continue
                    
                    # Cria o atributo
                    self.atributos[nome] = {
                        'nome': nome,
                        'tipo_retorno': config['tipo_retorno'],
                        'variacoes': []
                    }
                    
                    # Adiciona as variações com validação
                    for variacao in config['variacoes']:
                        if not isinstance(variacao, dict):
                            continue
                        
                        if 'descricao' not in variacao or 'padroes' not in variacao:
                            continue
                        
                        self.atributos[nome]['variacoes'].append({
                            'descricao': variacao['descricao'],
                            'padroes': variacao['padroes']
                        })
                
                st.success("Configurações importadas com sucesso!")
                st.experimental_rerun()
            except json.JSONDecodeError as e:
                st.error(f"Arquivo JSON inválido: {str(e)}")
            except Exception as e:
                st.error(f"Falha ao importar configurações: {str(e)}")
    
    def setup_aba_resultados(self):
        st.header("Resultados da Extração")
        
        if not hasattr(self, 'dados_originais'):
            st.warning("Por favor, carregue uma planilha na aba 'Modelo e Upload'")
            return
        
        if not self.atributos:
            st.warning("Por favor, configure pelo menos um atributo na aba 'Configuração'")
            return
        
        if st.button("Extrair Atributos"):
            with st.spinner("Processando dados..."):
                try:
                    self.dados_processados = self.dados_originais.copy()
                    progress_bar = st.progress(0)
                    
                    for i, (atributo_nome, config) in enumerate(self.atributos.items()):
                        tipo_retorno = config['tipo_retorno']
                        variacoes = config['variacoes']
                        
                        # Prepara regex para cada variação
                        regex_variacoes = []
                        for variacao in variacoes:
                            padroes_escaped = [re.escape(p) for p in variacao['padroes']]
                            regex = r'\b(' + '|'.join(padroes_escaped) + r')\b'
                            regex_variacoes.append((regex, variacao['descricao']))
                        
                        self.dados_processados[atributo_nome] = ""
                        
                        for idx, row in self.dados_processados.iterrows():
                            descricao = str(row['Descrição']).lower()
                            resultado = None
                            
                            # Verifica cada variação na ordem de prioridade
                            for regex, desc_padrao in regex_variacoes:
                                match = re.search(regex, descricao, re.IGNORECASE)
                                if match:
                                    resultado = self.formatar_resultado(
                                        match.group(1),
                                        tipo_retorno,
                                        atributo_nome,
                                        desc_padrao
                                    )
                                    break  # Usa a primeira correspondência (maior prioridade)
                            
                            self.dados_processados.at[idx, atributo_nome] = resultado if resultado else ""
                            progress = (idx + 1) / len(self.dados_processados)
                            progress_bar.progress(progress)
                    
                    progress_bar.empty()
                    st.success("Processamento concluído com sucesso!")
                except Exception as e:
                    st.error(f"Erro durante o processamento: {str(e)}")
        
        if hasattr(self, 'dados_processados') and not self.dados_processados.empty:
            st.subheader("Resultados")
            st.dataframe(self.dados_processados, use_container_width=True)
            
            # Botão de exportação
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                self.dados_processados.to_excel(writer, index=False)
            
            st.download_button(
                label="Exportar Resultados",
                data=buffer.getvalue(),
                file_name=f"resultados_extracao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    def formatar_resultado(self, valor_encontrado, tipo_retorno, nome_atributo, descricao_padrao):
        if tipo_retorno == "valor":
            # Extrai apenas números
            numeros = re.findall(r'\d+', valor_encontrado)
            return numeros[0] if numeros else ""
        elif tipo_retorno == "texto":
            return descricao_padrao
        elif tipo_retorno == "completo":
            return f"{nome_atributo}: {descricao_padrao}"
        return valor_encontrado
    
    def gerar_modelo(self):
        modelo = pd.DataFrame(columns=['ID', 'Descrição'])
        modelo.loc[0] = ['001', 'ventilador de paredes 110V']
        modelo.loc[1] = ['002', 'luminária de teto 220V branca']
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            modelo.to_excel(writer, index=False)
        
        st.download_button(
            label="Baixar Modelo",
            data=buffer.getvalue(),
            file_name="modelo_descricoes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    app = ExtratorAtributos()
