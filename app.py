import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import streamlit as st
from io import BytesIO

class CTeProcessor:
    def __init__(self):
        self.setup_ui()
        
    def formatar_cnpj(self, cnpj):
        """Formata CNPJ com pontuação"""
        if cnpj and len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
        return cnpj

    def formatar_cep(self, cep):
        """Formata CEP com hífen"""
        if cep and len(cep) == 8:
            return f"{cep[:5]}-{cep[5:8]}"
        return cep

    def formatar_data(self, data_str):
        """Formata data para padrão brasileiro"""
        try:
            if 'T' in data_str:
                data = datetime.strptime(data_str.split('T')[0], "%Y-%m-%d")
                return data.strftime("%d/%m/%Y")
            return data_str
        except:
            return data_str

    def formatar_moeda(self, valor):
        """Formata valores para o padrão monetário brasileiro"""
        try:
            return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    def processar_cte(self, xml_path):
        """Extrai os dados do CT-e do arquivo XML"""
        try:
            ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Verifica se é um CT-e processado (cteProc)
            cte_proc = root.find('.//cte:CTe', ns) or root

            # Dados básicos
            ide = cte_proc.find('.//cte:ide', ns)
            emit = cte_proc.find('.//cte:emit', ns)
            rem = cte_proc.find('.//cte:rem', ns)
            dest = cte_proc.find('.//cte:dest', ns)
            infCarga = cte_proc.find('.//cte:infCarga', ns)
            vPrest = cte_proc.find('.//cte:vPrest/cte:vTPrest', ns)
            infNFe = cte_proc.find('.//cte:infNFe', ns)
            protCTe = root.find('.//cte:protCTe', ns)

            # Extrair peso (procura por PESO REAL ou PESO BASE DE CALCULO)
            peso = 0.0
            for infQ in cte_proc.findall('.//cte:infQ', ns):
                tpMed = infQ.find('cte:tpMed', ns)
                if tpMed is not None and 'PESO' in tpMed.text.upper():
                    qCarga = infQ.find('cte:qCarga', ns)
                    if qCarga is not None:
                        try:
                            peso = max(peso, float(qCarga.text))
                        except:
                            pass

            # Status do CT-e
            status = "Autorizado" if protCTe is not None else "Não autorizado"

            return {
                'Número CT-e': ide.find('cte:nCT', ns).text if ide is not None else '',
                'Chave CT-e': cte_proc.find('.//cte:infCte', ns).get('Id')[3:] if cte_proc.find('.//cte:infCte', ns) is not None else '',
                'CNPJ Emitente': self.formatar_cnpj(emit.find('cte:CNPJ', ns).text if emit is not None and emit.find('cte:CNPJ', ns) is not None else ''),
                'Nome Emitente': emit.find('cte:xNome', ns).text if emit is not None and emit.find('cte:xNome', ns) is not None else '',
                'CEP Emitente': self.formatar_cep(emit.find('cte:enderEmit/cte:CEP', ns).text if emit is not None and emit.find('cte:enderEmit/cte:CEP', ns) is not None else ''),
                'Cidade Emitente': emit.find('cte:enderEmit/cte:xMun', ns).text if emit is not None and emit.find('cte:enderEmit/cte:xMun', ns) is not None else '',
                'UF Emitente': emit.find('cte:enderEmit/cte:UF', ns).text if emit is not None and emit.find('cte:enderEmit/cte:UF', ns) is not None else '',
                'CNPJ Remetente': self.formatar_cnpj(rem.find('cte:CNPJ', ns).text if rem is not None and rem.find('cte:CNPJ', ns) is not None else ''),
                'Nome Remetente': rem.find('cte:xNome', ns).text if rem is not None and rem.find('cte:xNome', ns) is not None else '',
                'CEP Remetente': self.formatar_cep(rem.find('cte:enderReme/cte:CEP', ns).text if rem is not None and rem.find('cte:enderReme/cte:CEP', ns) is not None else ''),
                'Cidade Remetente': rem.find('cte:enderReme/cte:xMun', ns).text if rem is not None and rem.find('cte:enderReme/cte:xMun', ns) is not None else '',
                'UF Remetente': rem.find('cte:enderReme/cte:UF', ns).text if rem is not None and rem.find('cte:enderReme/cte:UF', ns) is not None else '',
                'CNPJ Destinatário': self.formatar_cnpj(dest.find('cte:CNPJ', ns).text if dest is not None and dest.find('cte:CNPJ', ns) is not None else ''),
                'Nome Destinatário': dest.find('cte:xNome', ns).text if dest is not None and dest.find('cte:xNome', ns) is not None else '',
                'CEP Destinatário': self.formatar_cep(dest.find('cte:enderDest/cte:CEP', ns).text if dest is not None and dest.find('cte:enderDest/cte:CEP', ns) is not None else ''),
                'Cidade Destinatário': dest.find('cte:enderDest/cte:xMun', ns).text if dest is not None and dest.find('cte:enderDest/cte:xMun', ns) is not None else '',
                'UF Destinatário': dest.find('cte:enderDest/cte:UF', ns).text if dest is not None and dest.find('cte:enderDest/cte:UF', ns) is not None else '',
                'Valor Carga': self.formatar_moeda(infCarga.find('cte:vCarga', ns).text if infCarga is not None and infCarga.find('cte:vCarga', ns) is not None else '0'),
                'Valor Frete': self.formatar_moeda(vPrest.text if vPrest is not None else '0'),
                'Chave Carga': infNFe.find('cte:chave', ns).text if infNFe is not None and infNFe.find('cte:chave', ns) is not None else '',
                'Número Carga': ide.find('cte:nCT', ns).text if ide is not None else '',
                'Peso (kg)': f"{peso:.3f}",
                'Data Emissão': self.formatar_data(ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else ''),
                'Status': status
            }
        except Exception as e:
            st.error(f"Erro ao processar CT-e {xml_path}: {str(e)}")
            return None

    def processar_pasta(self, pasta):
        """Processa todos os arquivos XML em uma pasta"""
        resultados = []
        xml_files = [f for f in os.listdir(pasta) if f.lower().endswith('.xml')]
        
        if not xml_files:
            st.warning("Nenhum arquivo XML encontrado na pasta selecionada")
            return None

        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, xml_file in enumerate(xml_files):
            try:
                caminho = os.path.join(pasta, xml_file)
                dados = self.processar_cte(caminho)
                if dados:
                    resultados.append(dados)
                
                # Atualizar progresso
                progresso = (i + 1) / len(xml_files)
                progress_bar.progress(progresso)
                status_text.text(f"Processando {i+1} de {len(xml_files)} arquivos...")
            except Exception as e:
                st.error(f"Erro ao processar {xml_file}: {str(e)}")

        progress_bar.empty()
        status_text.empty()
        
        if resultados:
            df = pd.DataFrame(resultados)
            st.success(f"Processados {len(resultados)} arquivos CT-e com sucesso!")
            return df
        else:
            st.warning("Nenhum dado válido encontrado nos arquivos")
            return None

    def exportar_excel(self, df):
        """Exporta os resultados para Excel"""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='CTes Processados')
            workbook = writer.book
            worksheet = writer.sheets['CTes Processados']
            
            # Ajustar largura das colunas
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        
        processed_data = output.getvalue()
        return processed_data

    def setup_ui(self):
        """Configura a interface do usuário com Streamlit"""
        st.set_page_config(
            page_title="Processador de CT-e",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("📄 Processador de Arquivos CT-e")
        st.markdown("""
        Esta aplicação processa arquivos XML de Conhecimento de Transporte Eletrônico (CT-e) e extrai os dados principais para análise.
        """)
        
        st.sidebar.header("Configurações")
        
        # Upload de arquivos
        st.sidebar.subheader("1. Selecionar Arquivos")
        uploaded_files = st.sidebar.file_uploader(
            "Carregue os arquivos XML de CT-e",
            type=['xml'],
            accept_multiple_files=True
        )
        
        # Ou selecionar pasta
        st.sidebar.subheader("Ou selecionar pasta")
        pasta = st.sidebar.text_input("Caminho da pasta com arquivos XML (para uso local):")
        
        if st.sidebar.button("Processar Arquivos"):
            if uploaded_files or pasta:
                with st.spinner("Processando arquivos..."):
                    resultados = []
                    
                    # Processar arquivos enviados
                    if uploaded_files:
                        for uploaded_file in uploaded_files:
                            try:
                                # Salvar temporariamente para processar
                                with open(uploaded_file.name, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                                dados = self.processar_cte(uploaded_file.name)
                                if dados:
                                    resultados.append(dados)
                                os.remove(uploaded_file.name)  # Limpar arquivo temporário
                            except Exception as e:
                                st.error(f"Erro ao processar {uploaded_file.name}: {str(e)}")
                    
                    # Processar pasta local
                    if pasta and os.path.isdir(pasta):
                        df_pasta = self.processar_pasta(pasta)
                        if df_pasta is not None:
                            if resultados:  # Se já tem resultados dos uploads
                                df_upload = pd.DataFrame(resultados)
                                self.resultados_df = pd.concat([df_upload, df_pasta], ignore_index=True)
                            else:
                                self.resultados_df = df_pasta
                        else:
                            if resultados:
                                self.resultados_df = pd.DataFrame(resultados)
                    elif resultados:
                        self.resultados_df = pd.DataFrame(resultados)
                    
                    if hasattr(self, 'resultados_df') and not self.resultados_df.empty:
                        st.session_state.df_processed = True
                        
                        # Mostrar dados em tabela
                        st.subheader("Resultados do Processamento")
                        st.dataframe(
                            self.resultados_df,
                            height=600,
                            use_container_width=True
                        )
                        
                        # Mostrar estatísticas
                        st.subheader("Estatísticas")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total de CT-es", len(self.resultados_df))
                        with col2:
                            total_frete = self.resultados_df['Valor Frete'].str.replace('R\$ ', '').str.replace('.', '').str.replace(',', '.').astype(float).sum()
                            st.metric("Valor Total de Frete", f"R$ {total_frete:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                        with col3:
                            total_peso = self.resultados_df['Peso (kg)'].astype(float).sum()
                            st.metric("Peso Total (kg)", f"{total_peso:,.3f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    else:
                        st.warning("Nenhum dado válido foi processado.")
            else:
                st.warning("Por favor, carregue arquivos XML ou informe um caminho de pasta válido.")
        
        # Botão de exportação
        if hasattr(self, 'resultados_df') and not self.resultados_df.empty:
            st.sidebar.subheader("Exportar Resultados")
            excel_data = self.exportar_excel(self.resultados_df)
            st.sidebar.download_button(
                label="📥 Baixar Excel",
                data=excel_data,
                file_name=f"CTe_Resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    processor = CTeProcessor()
