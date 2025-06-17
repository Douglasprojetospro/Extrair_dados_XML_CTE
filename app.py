import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

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

        # Organizar os dados extraídos em um dicionário
        dados = {
            'Número CT-e': ide.find('cte:nCT', ns).text if ide is not None else '',
            'Chave CT-e': cte_proc.find('.//cte:infCte', ns).get('Id')[3:] if cte_proc.find('.//cte:infCte', ns) is not None else '',
            'CNPJ Emitente': emit.find('cte:CNPJ', ns).text if emit is not None and emit.find('cte:CNPJ', ns) is not None else '',
            'Nome Emitente': emit.find('cte:xNome', ns).text if emit is not None and emit.find('cte:xNome', ns) is not None else '',
            'CEP Emitente': emit.find('cte:enderEmit/cte:CEP', ns).text if emit is not None and emit.find('cte:enderEmit/cte:CEP', ns) is not None else '',
            'Cidade Emitente': emit.find('cte:enderEmit/cte:xMun', ns).text if emit is not None and emit.find('cte:enderEmit/cte:xMun', ns) is not None else '',
            'UF Emitente': emit.find('cte:enderEmit/cte:UF', ns).text if emit is not None and emit.find('cte:enderEmit/cte:UF', ns) is not None else '',
            'CNPJ Remetente': rem.find('cte:CNPJ', ns).text if rem is not None and rem.find('cte:CNPJ', ns) is not None else '',
            'Nome Remetente': rem.find('cte:xNome', ns).text if rem is not None and rem.find('cte:xNome', ns) is not None else '',
            'CEP Remetente': rem.find('cte:enderReme/cte:CEP', ns).text if rem is not None and rem.find('cte:enderReme/cte:CEP', ns) is not None else '',
            'Cidade Remetente': rem.find('cte:enderReme/cte:xMun', ns).text if rem is not None and rem.find('cte:enderReme/cte:xMun', ns) is not None else '',
            'UF Remetente': rem.find('cte:enderReme/cte:UF', ns).text if rem is not None and rem.find('cte:enderReme/cte:UF', ns) is not None else '',
            'CNPJ Destinatário': dest.find('cte:CNPJ', ns).text if dest is not None and dest.find('cte:CNPJ', ns) is not None else '',
            'Nome Destinatário': dest.find('cte:xNome', ns).text if dest is not None and dest.find('cte:xNome', ns) is not None else '',
            'CEP Destinatário': dest.find('cte:enderDest/cte:CEP', ns).text if dest is not None and dest.find('cte:enderDest/cte:CEP', ns) is not None else '',
            'Cidade Destinatário': dest.find('cte:enderDest/cte:xMun', ns).text if dest is not None and dest.find('cte:enderDest/cte:xMun', ns) is not None else '',
            'UF Destinatário': dest.find('cte:enderDest/cte:UF', ns).text if dest is not None and dest.find('cte:enderDest/cte:UF', ns) is not None else '',
            'Valor Carga': infCarga.find('cte:vCarga', ns).text if infCarga is not None and infCarga.find('cte:vCarga', ns) is not None else '0',
            'Valor Frete': vPrest.text if vPrest is not None else '0',
            'Chave Carga': infNFe.find('cte:chave', ns).text if infNFe is not None and infNFe.find('cte:chave', ns) is not None else '',
            'Número Carga': ide.find('cte:nCT', ns).text if ide is not None else '',
            'Peso (kg)': f"{peso:.3f}",
            'Data Emissão': ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else '',
            'Status': status
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

def app():
    """Função principal que roda a aplicação Streamlit"""
    st.title("📄 Processador de CT-e")
    st.markdown("""
    Esta aplicação processa arquivos XML de Conhecimento de Transporte Eletrônico (CT-e) e extrai os dados principais para análise.
    """)

    st.sidebar.header("Carregar Arquivo XML")
    uploaded_files = st.sidebar.file_uploader("Escolha arquivos XML", type=["xml"], accept_multiple_files=True)

    if uploaded_files:
        st.sidebar.text(f"Arquivos Carregados: {[file.name for file in uploaded_files]}")

        # Processar os arquivos XML usando ThreadPoolExecutor para otimizar
        with ThreadPoolExecutor() as executor:
            xml_data_list = [file.read() for file in uploaded_files]
            dados_list = list(executor.map(processar_cte, xml_data_list))

        # Gerar relatório para cada arquivo processado
        relatorios = [gerar_relatorio(dados) for dados in dados_list if dados]

        # Combinar todos os relatórios em um único DataFrame
        if relatorios:
            final_df = pd.concat(relatorios, ignore_index=True)
            st.subheader("Relatório do CT-e")
            st.dataframe(final_df)
            
            # Opção de exportar para Excel
            excel_data = BytesIO()
            with pd.ExcelWriter(excel_data, engine="openpyxl") as writer:
                final_df.to_excel(writer, index=False)
            st.sidebar.download_button(
                label="Baixar Relatório (Excel)",
                data=excel_data.getvalue(),
                file_name="relatorio_cte.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Erro ao processar os arquivos XML.")
            
if __name__ == "__main__":
    app()
