import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# Configuração da página para layout wide
st.set_page_config(page_title="Processador de CT-e", layout="wide", page_icon="📄")

# Estilos CSS personalizados
st.markdown("""
    <style>
        .main {background-color: #f8f9fa;}
        .stButton>button {background-color: #4CAF50; color: white;}
        .stDownloadButton>button {background-color: #2196F3; color: white;}
        .stFileUploader>div>div>button {background-color: #FF9800; color: white;}
        .report-title {color: #2c3e50; text-align: center;}
        .sidebar .sidebar-content {background-color: #e9ecef;}
        .metric-box {border-radius: 5px; padding: 10px; background-color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

def processar_cte(xml_data):
    """Extrai os dados do CT-e do arquivo XML e retorna como um dicionário"""
    try:
        # Namespace utilizado no XML
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        
        # Parse do XML
        root = ET.fromstring(xml_data)

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
                    except ValueError:
                        pass

        # Status do CT-e
        status = "Autorizado" if protCTe is not None else "Não autorizado"

        # Formatar data se existir
        dh_emi = ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else ''
        if dh_emi:
            dh_emi = pd.to_datetime(dh_emi).strftime('%d/%m/%Y %H:%M:%S')

        # Organizar os dados extraídos em um dicionário
        dados = {
            'Número CT-e': ide.find('cte:nCT', ns).text if ide is not None else '',
            'Chave CT-e': cte_proc.find('.//cte:infCte', ns).get('Id')[3:] if cte_proc.find('.//cte:infCte', ns) is not None else '',
            'Status': status,
            'Data Emissão': dh_emi,
            
            # Emitente
            'CNPJ Emitente': emit.find('cte:CNPJ', ns).text if emit is not None and emit.find('cte:CNPJ', ns) is not None else '',
            'Nome Emitente': emit.find('cte:xNome', ns).text if emit is not None and emit.find('cte:xNome', ns) is not None else '',
            'CEP Emitente': emit.find('cte:enderEmit/cte:CEP', ns).text if emit is not None and emit.find('cte:enderEmit/cte:CEP', ns) is not None else '',
            'Cidade Emitente': emit.find('cte:enderEmit/cte:xMun', ns).text if emit is not None and emit.find('cte:enderEmit/cte:xMun', ns) is not None else '',
            'UF Emitente': emit.find('cte:enderEmit/cte:UF', ns).text if emit is not None and emit.find('cte:enderEmit/cte:UF', ns) is not None else '',
            
            # Remetente
            'CNPJ Remetente': rem.find('cte:CNPJ', ns).text if rem is not None and rem.find('cte:CNPJ', ns) is not None else '',
            'Nome Remetente': rem.find('cte:xNome', ns).text if rem is not None and rem.find('cte:xNome', ns) is not None else '',
            'CEP Remetente': rem.find('cte:enderReme/cte:CEP', ns).text if rem is not None and rem.find('cte:enderReme/cte:CEP', ns) is not None else '',
            'Cidade Remetente': rem.find('cte:enderReme/cte:xMun', ns).text if rem is not None and rem.find('cte:enderReme/cte:xMun', ns) is not None else '',
            'UF Remetente': rem.find('cte:enderReme/cte:UF', ns).text if rem is not None and rem.find('cte:enderReme/cte:UF', ns) is not None else '',
            
            # Destinatário
            'CNPJ Destinatário': dest.find('cte:CNPJ', ns).text if dest is not None and dest.find('cte:CNPJ', ns) is not None else '',
            'Nome Destinatário': dest.find('cte:xNome', ns).text if dest is not None and dest.find('cte:xNome', ns) is not None else '',
            'CEP Destinatário': dest.find('cte:enderDest/cte:CEP', ns).text if dest is not None and dest.find('cte:enderDest/cte:CEP', ns) is not None else '',
            'Cidade Destinatário': dest.find('cte:enderDest/cte:xMun', ns).text if dest is not None and dest.find('cte:enderDest/cte:xMun', ns) is not None else '',
            'UF Destinatário': dest.find('cte:enderDest/cte:UF', ns).text if dest is not None and dest.find('cte:enderDest/cte:UF', ns) is not None else '',
            
            # Informações da Carga
            'Valor Carga (R$)': float(infCarga.find('cte:vCarga', ns).text) if infCarga is not None and infCarga.find('cte:vCarga', ns) is not None else 0.0,
            'Valor Frete (R$)': float(vPrest.text) if vPrest is not None else 0.0,
            'Chave NFe': infNFe.find('cte:chave', ns).text if infNFe is not None and infNFe.find('cte:chave', ns) is not None else '',
            'Peso (kg)': peso,
        }

        return dados

    except Exception as e:
        st.error(f"Erro ao processar o XML: {str(e)}")
        return None

def gerar_relatorio(dados):
    """Gera um relatório a partir dos dados extraídos"""
    if dados:
        df = pd.DataFrame([dados])
        return df
    else:
        return None

def formatar_excel(writer, df):
    """Formata o arquivo Excel com estilos e organização"""
    workbook = writer.book
    # Obtém o nome da primeira planilha
    worksheet_name = writer.sheets.sheetnames[0]
    worksheet = writer.sheets[worksheet_name]
    
    # Formatação para cabeçalho
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    # Formatação para valores monetários
    money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
    
    # Formatação para datas
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm:ss'})
    
    # Formatação para números decimais
    decimal_format = workbook.add_format({'num_format': '#,##0.000'})
    
    # Aplicar formatações
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
    
    # Ajustar largura das colunas
    for i, col in enumerate(df.columns):
        max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(i, i, max_len)
    
    # Formatar colunas específicas
    money_cols = [col for col in ['Valor Carga (R$)', 'Valor Frete (R$)'] if col in df.columns]
    date_cols = [col for col in ['Data Emissão'] if col in df.columns]
    decimal_cols = [col for col in ['Peso (kg)'] if col in df.columns]
    
    for col in money_cols:
        col_idx = df.columns.get_loc(col)
        worksheet.set_column(col_idx, col_idx, 15, money_format)
    
    for col in date_cols:
        col_idx = df.columns.get_loc(col)
        worksheet.set_column(col_idx, col_idx, 20, date_format)
    
    for col in decimal_cols:
        col_idx = df.columns.get_loc(col)
        worksheet.set_column(col_idx, col_idx, 15, decimal_format)

def app():
    """Função principal que roda a aplicação Streamlit"""
    st.markdown('<h1 class="report-title">📄 Processador de CT-e</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        Esta aplicação processa arquivos XML de Conhecimento de Transporte Eletrônico (CT-e) e extrai os dados principais para análise.
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar.expander("📤 Carregar Arquivos", expanded=True):
        uploaded_files = st.file_uploader(
            "Selecione os arquivos XML", 
            type=["xml"], 
            accept_multiple_files=True,
            help="Selecione um ou mais arquivos XML de CT-e para processamento"
        )

    if uploaded_files:
        st.sidebar.success(f"{len(uploaded_files)} arquivo(s) selecionado(s)")
        
        # Processar os arquivos XML usando ThreadPoolExecutor para otimizar
        with st.spinner('Processando arquivos...'):
            with ThreadPoolExecutor() as executor:
                xml_data_list = [file.read() for file in uploaded_files]
                dados_list = list(executor.map(processar_cte, xml_data_list))

        # Gerar relatório para cada arquivo processado
        relatorios = [gerar_relatorio(dados) for dados in dados_list if dados]

        # Combinar todos os relatórios em um único DataFrame
        if relatorios:
            final_df = pd.concat(relatorios, ignore_index=True)
            
            # Exibir relatório com tabs
            tab1, tab2 = st.tabs(["📊 Visualização", "🔍 Dados Completos"])
            
            with tab1:
                st.subheader("Resumo dos CT-es Processados")
                
                # Métricas
                cols = st.columns(3)
                with cols[0]:
                    st.markdown('<div class="metric-box"><h3>Total CT-es</h3><p style="font-size: 24px;">{}</p></div>'.format(len(final_df)), unsafe_allow_html=True)
                with cols[1]:
                    st.markdown('<div class="metric-box"><h3>CT-es Autorizados</h3><p style="font-size: 24px;">{}</p></div>'.format(
                        final_df['Status'].value_counts().get('Autorizado', 0)), unsafe_allow_html=True)
                with cols[2]:
                    st.markdown('<div class="metric-box"><h3>Valor Total Frete</h3><p style="font-size: 24px;">R$ {:,.2f}</p></div>'.format(
                        final_df['Valor Frete (R$)'].sum()), unsafe_allow_html=True)
                
                # Filtros interativos
                with st.expander("🔍 Filtros", expanded=False):
                    status_filter = st.multiselect(
                        'Status',
                        options=final_df['Status'].unique(),
                        default=final_df['Status'].unique()
                    )
                    
                    uf_filter = st.multiselect(
                        'UF Emitente',
                        options=final_df['UF Emitente'].unique(),
                        default=final_df['UF Emitente'].unique()
                    )
                
                # Aplicar filtros
                filtered_df = final_df[
                    (final_df['Status'].isin(status_filter)) & 
                    (final_df['UF Emitente'].isin(uf_filter))
                ]
                
                st.dataframe(filtered_df.style.format({
                    'Valor Carga (R$)': 'R$ {:,.2f}',
                    'Valor Frete (R$)': 'R$ {:,.2f}',
                    'Peso (kg)': '{:,.3f} kg'
                }), height=400, use_container_width=True)
            
            with tab2:
                st.subheader("Dados Completos")
                st.dataframe(final_df.style.format({
                    'Valor Carga (R$)': 'R$ {:,.2f}',
                    'Valor Frete (R$)': 'R$ {:,.2f}',
                    'Peso (kg)': '{:,.3f} kg'
                }), height=600, use_container_width=True)
            
            # Opção de exportar para Excel
            st.sidebar.markdown("---")
            st.sidebar.subheader("Exportar Relatório")
            
            excel_data = BytesIO()
            with pd.ExcelWriter(excel_data, engine="xlsxwriter") as writer:
                final_df.to_excel(writer, index=False, sheet_name='CT-es')
                formatar_excel(writer, final_df)
            
            st.sidebar.download_button(
                label="📥 Baixar Relatório (Excel)",
                data=excel_data.getvalue(),
                file_name="relatorio_cte.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Clique para baixar o relatório completo em formato Excel"
            )
        else:
            st.error("Nenhum dado válido foi extraído dos arquivos XML.")

if __name__ == "__main__":
    app()
