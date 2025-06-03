import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO
import base64

# Configuração da página
st.set_page_config(layout="wide", page_title="Sistema de Extração de Atributos Avançado")

# Palavras para ignorar (inicial)
DEFAULT_STOPWORDS = {
    'de', 'para', 'com', 'sem', 'em', 'por', 'que', 'os', 'as', 'um', 'uma',
    'ao', 'aos', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas', 'pelo',
    'pela', 'pelos', 'pelas', 'este', 'esta', 'estes', 'estas', 'esse',
    'essa', 'esses', 'essas', 'aquele', 'aquela', 'aqueles', 'aquelas',
    'ou', 'e', 'mas', 'porém', 'entretanto', 'contudo', 'quando', 'enquanto',
    'como', 'porque', 'pois', 'assim', 'então', 'logo', 'portanto', 'desse',
    'dessa', 'destes', 'destas', 'deste', 'isso', 'isto', 'aquilo'
}

class ExtratorAtributos:
    def __init__(self):
        self.atributos = {}
        self.dados_processados = pd.DataFrame()
        self.etapa_configuracao = 0  # 0=nome, 1=variações, 2=padrões, 3=prioridade, 4=formato
        self.atributo_atual = {}
        
        if 'atributos' not in st.session_state:
            st.session_state.atributos = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        st.title("Sistema de Extração de Atributos Avançado")
        
        # Abas principais
        tab1, tab2, tab3 = st.tabs(["Modelo e Upload", "Configuração", "Resultados"])
        
        with tab1:
            self.setup_aba_modelo()
        with tab2:
            self.setup_aba_configuracao()
        with tab3:
            self.setup_aba_resultados()
    
    def setup_aba_modelo(self):
        st.header("Modelo e Upload")
        
        # Seção para modelo
        with st.expander("Gerar Modelo de Planilha", expanded=True):
            st.download_button(
                "⬇️ Baixar Modelo Excel",
                data=self.gerar_modelo(),
                file_name="modelo_descricoes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Seção para upload
        with st.expander("Upload de Planilha", expanded=True):
            uploaded_file = st.file_uploader("Selecione a planilha (Excel)", type=["xlsx", "xls"])
            
            if uploaded_file is not None:
                try:
                    self.dados_originais = pd.read_excel(uploaded_file)
                    
                    if 'ID' not in self.dados_originais.columns or 'Descrição' not in self.dados_originais.columns:
                        st.error("A planilha deve conter as colunas 'ID' e 'Descrição'")
                    else:
                        st.success(f"Planilha carregada com sucesso! ({len(self.dados_originais)} registros)")
                        st.dataframe(self.dados_originais.head())
                except Exception as e:
                    st.error(f"Erro ao carregar planilha: {str(e)}")
    
    def setup_aba_configuracao(self):
        st.header("Configuração de Atributos")
        
        # Seção de configuração dinâmica
        with st.expander("Configurar Novo Atributo", expanded=True):
            self.atualizar_interface_configuracao()
        
        # Seção para importar/exportar configurações
        with st.expander("Importar/Exportar Configurações", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                uploaded_config = st.file_uploader("Importar configurações", type=["json"])
                if uploaded_config is not None:
                    self.importar_configuracoes(uploaded_config)
            
            with col2:
                if st.button("Exportar Configurações Atuais"):
                    self.exportar_configuracoes()
        
        # Lista de atributos configurados
        with st.expander("Atributos Configurados", expanded=True):
            if not st.session_state.get('atributos', {}):
                st.info("Nenhum atributo configurado ainda")
            else:
                for nome, config in st.session_state.atributos.items():
                    with st.container():
                        col1, col2, col3 = st.columns([4, 1, 1])
                        
                        with col1:
                            st.subheader(nome)
                            st.caption(f"Variações: {', '.join([v['descricao'] for v in config['variacoes']])}")
                            st.caption(f"Formato: {'Valor' if config['tipo_retorno'] == 'valor' else 'Texto' if config['tipo_retorno'] == 'texto' else 'Completo'}")
                        
                        with col2:
                            if st.button("Editar", key=f"edit_{nome}"):
                                self.editar_atributo(nome)
                        
                        with col3:
                            if st.button("Remover", key=f"remove_{nome}"):
                                self.remover_atributo(nome)
    
    def setup_aba_resultados(self):
        st.header("Resultados da Extração")
        
        if not hasattr(self, 'dados_processados') or self.dados_processados.empty:
            st.info("Processe os dados primeiro na aba 'Configuração'")
            return
        
        st.dataframe(self.dados_processados)
        
        st.download_button(
            "📥 Exportar Resultados",
            data=self.exportar_resultados(),
            file_name="resultados_extracao.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    def atualizar_interface_configuracao(self):
        # Controles de navegação
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("← Voltar", disabled=self.etapa_configuracao == 0):
                self.etapa_configuracao -= 1
                st.experimental_rerun()
        
        with col2:
            btn_avancar = st.button(self.get_texto_botao_avancar())
        
        with col3:
            if st.button("Cancelar Configuração"):
                self.cancelar_configuracao()
        
        # Exibe o passo atual
        if self.etapa_configuracao == 0:
            self.passo_nome_atributo()
        elif self.etapa_configuracao == 1:
            self.passo_variacoes()
        elif self.etapa_configuracao == 2:
            self.passo_padroes()
        elif self.etapa_configuracao == 3:
            self.passo_prioridade()
        elif self.etapa_configuracao == 4:
            self.passo_formato()
        
        # Lógica do botão avançar
        if btn_avancar:
            try:
                if self.etapa_configuracao == 0:
                    self.validar_passo_nome()
                elif self.etapa_configuracao == 1:
                    self.validar_passo_variacoes()
                elif self.etapa_configuracao == 2:
                    self.validar_passo_padroes()
                elif self.etapa_configuracao == 3:
                    self.validar_passo_prioridade()
                elif self.etapa_configuracao == 4:
                    self.validar_passo_formato()
                
                self.etapa_configuracao += 1
                if self.etapa_configuracao > 4:
                    self.finalizar_configuracao()
                    return
                
                st.experimental_rerun()
            except Exception as e:
                st.error(str(e))
    
    # [Métodos auxiliares para cada passo da configuração...]
    # Implementar todos os métodos necessários seguindo o mesmo padrão
    
    def processar_dados(self):
        if not hasattr(self, 'dados_originais'):
            st.error("Por favor, carregue uma planilha primeiro")
            return
        
        if not st.session_state.get('atributos', {}):
            st.error("Por favor, configure pelo menos um atributo")
            return
        
        try:
            self.dados_processados = self.dados_originais.copy()
            progress_bar = st.progress(0)
            
            for i, (atributo_nome, config) in enumerate(st.session_state.atributos.items()):
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
            
            st.success("Processamento concluído com sucesso!")
            st.experimental_rerun()
        
        except Exception as e:
            st.error(f"Falha ao processar dados: {str(e)}")
    
    # [Implementar todos os outros métodos necessários...]

# Função principal para execução no Streamlit
def main():
    extrator = ExtratorAtributos()

if __name__ == "__main__":
    main()
