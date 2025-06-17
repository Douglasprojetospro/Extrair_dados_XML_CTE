import pandas as pd
from lxml import etree
from io import BytesIO
import base64
from datetime import datetime
import os
import psutil
import streamlit as st

def parse_cte(xml_content):
    """Extrai os dados do CT-e do XML"""
    try:
        # Parse do XML
        root = etree.fromstring(xml_content)
        
        # Namespaces
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        
        # Dados básicos
        inf_cte = root.find('.//cte:infCte', namespaces=ns)
        prot_cte = root.find('.//cte:infProt', namespaces=ns)
        
        # Dados do emitente
        emitente = inf_cte.find('.//cte:emit', namespaces=ns)
        ender_emit = emitente.find('.//cte:enderEmit', namespaces=ns)
        
        # Dados do remetente
        remetente = inf_cte.find('.//cte:rem', namespaces=ns)
        ender_reme = remetente.find('.//cte:enderReme', namespaces=ns) if remetente is not None else None
        
        # Dados do destinatário
        destinatario = inf_cte.find('.//cte:dest', namespaces=ns)
        ender_dest = destinatario.find('.//cte:enderDest', namespaces=ns) if destinatario is not None else None
        
        # Dados da carga
        inf_carga = inf_cte.find('.//cte:infCarga', namespaces=ns)
        inf_q = inf_carga.findall('.//cte:infQ', namespaces=ns) if inf_carga is not None else []
        
        # Dados do documento relacionado (NFe)
        inf_doc = inf_cte.find('.//cte:infDoc', namespaces=ns)
        inf_nfe = inf_doc.find('.//cte:infNFe', namespaces=ns) if inf_doc is not None else None
        
        # Valor do frete
        v_prest = inf_cte.find('.//cte:vPrest', namespaces=ns)
        frete_comp = next(
            (comp for comp in v_prest.findall('.//cte:Comp', namespaces=ns) 
            if comp.find('.//cte:xNome', namespaces=ns).text == 'FRETE VALOR'
        ) if v_prest is not None else None
        
        # Peso (pegando o primeiro PESO REAL encontrado)
        peso = None
        for q in inf_q:
            if q.find('.//cte:tpMed', namespaces=ns).text == 'PESO REAL':
                peso = q.find('.//cte:qCarga', namespaces=ns).text
                break
        
        # Montagem do dicionário de dados
        data = {
            'Número CT-e': inf_cte.find('.//cte:nCT', namespaces=ns).text if inf_cte.find('.//cte:nCT', namespaces=ns) is not None else '',
            'Chave CT-e': prot_cte.find('.//cte:chCTe', namespaces=ns).text if prot_cte is not None else '',
            'CNPJ Emitente': emitente.find('.//cte:CNPJ', namespaces=ns).text if emitente.find('.//cte:CNPJ', namespaces=ns) is not None else '',
            'Nome Emitente': emitente.find('.//cte:xNome', namespaces=ns).text if emitente.find('.//cte:xNome', namespaces=ns) is not None else '',
            'CEP Emitente': ender_emit.find('.//cte:CEP', namespaces=ns).text if ender_emit is not None and ender_emit.find('.//cte:CEP', namespaces=ns) is not None else '',
            'Cidade Emitente': ender_emit.find('.//cte:xMun', namespaces=ns).text if ender_emit is not None else '',
            'UF Emitente': ender_emit.find('.//cte:UF', namespaces=ns).text if ender_emit is not None else '',
            'CNPJ Remetente': remetente.find('.//cte:CNPJ', namespaces=ns).text if remetente is not None and remetente.find('.//cte:CNPJ', namespaces=ns) is not None else '',
            'Nome Remetente': remetente.find('.//cte:xNome', namespaces=ns).text if remetente is not None else '',
            'CEP Remetente': ender_reme.find('.//cte:CEP', namespaces=ns).text if ender_reme is not None and ender_reme.find('.//cte:CEP', namespaces=ns) is not None else '',
            'Cidade Remetente': ender_reme.find('.//cte:xMun', namespaces=ns).text if ender_reme is not None else '',
            'UF Remetente': ender_reme.find('.//cte:UF', namespaces=ns).text if ender_reme is not None else '',
            'CNPJ Destinatário': destinatario.find('.//cte:CNPJ', namespaces=ns).text if destinatario is not None and destinatario.find('.//cte:CNPJ', namespaces=ns) is not None else '',
            'Nome Destinatário': destinatario.find('.//cte:xNome', namespaces=ns).text if destinatario is not None else '',
            'CEP Destinatário': ender_dest.find('.//cte:CEP', namespaces=ns).text if ender_dest is not None and ender_dest.find('.//cte:CEP', namespaces=ns) is not None else '',
            'Cidade Destinatário': ender_dest.find('.//cte:xMun', namespaces=ns).text if ender_dest is not None else '',
            'UF Destinatário': ender_dest.find('.//cte:UF', namespaces=ns).text if ender_dest is not None else '',
            'Valor Carga': inf_carga.find('.//cte:vCarga', namespaces=ns).text if inf_carga is not None and inf_carga.find('.//cte:vCarga', namespaces=ns) is not None else '',
            'Valor Frete': frete_comp.find('.//cte:vComp', namespaces=ns).text if frete_comp is not None else '',
            'Chave Carga': inf_nfe.find('.//cte:chave', namespaces=ns).text if inf_nfe is not None else '',
            'Número Carga': '',  # Não encontrado no XML de exemplo
            'Peso (kg)': peso,
            'Data Emissão': inf_cte.find('.//cte:dhEmi', namespaces=ns).text if inf_cte.find('.//cte:dhEmi', namespaces=ns) is not None else '',
            'Status': prot_cte.find('.//cte:xMotivo', namespaces=ns).text if prot_cte is not None else ''
        }
        
        return data
    
    except Exception as e:
        st.error(f"Erro ao processar XML: {str(e)}")
        return None

def generate_excel(data):
    """Gera um arquivo Excel a partir dos dados"""
    try:
        # Cria DataFrame
        df = pd.DataFrame([data])
        
        # Formata colunas de valor
        numeric_cols = ['Valor Carga', 'Valor Frete', 'Peso (kg)']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else '')
        
        # Formata data
        if 'Data Emissão' in df.columns:
            df['Data Emissão'] = pd.to_datetime(df['Data Emissão']).dt.strftime('%d/%m/%Y %H:%M:%S')
        
        # Cria arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='CT-e')
            
            # Formatação
            workbook = writer.book
            worksheet = writer.sheets['CT-e']
            
            # Formata cabeçalho
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })
            
            # Aplica formatação ao cabeçalho
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajusta largura das colunas
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        
        output.seek(0)
        return output
    
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Extrator de CT-e",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📄 Extrator de Dados de CT-e")
    st.markdown("""
    Esta aplicação extrai informações de arquivos XML de Conhecimento de Transporte Eletrônico (CT-e) 
    e gera um relatório em Excel com os dados estruturados.
    """)
    
    # Mostra informações de memória
    mem = psutil.virtual_memory()
    st.sidebar.title("Informações do Sistema")
    st.sidebar.write(f"**Memória total:** {mem.total / (1024**3):.2f} GB")
    st.sidebar.write(f"**Memória disponível:** {mem.available / (1024**3):.2f} GB")
    st.sidebar.write(f"**Uso de memória:** {mem.percent}%")
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("Carregue o arquivo XML do CT-e", type=['xml'])
    
    if uploaded_file is not None:
        try:
            # Lê o conteúdo do arquivo
            xml_content = uploaded_file.read()
            
            # Processa o XML
            with st.spinner("Processando CT-e..."):
                data = parse_cte(xml_content)
                
                if data:
                    st.success("CT-e processado com sucesso!")
                    
                    # Mostra pré-visualização dos dados
                    st.subheader("Pré-visualização dos Dados")
                    preview_df = pd.DataFrame([data])
                    st.dataframe(preview_df)
                    
                    # Gera Excel
                    with st.spinner("Gerando arquivo Excel..."):
                        excel_file = generate_excel(data)
                        
                        if excel_file:
                            # Cria botão de download
                            st.download_button(
                                label="📥 Baixar Relatório em Excel",
                                data=excel_file,
                                file_name=f"cte_{data.get('Número CT-e', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

if __name__ == "__main__":
    main()
