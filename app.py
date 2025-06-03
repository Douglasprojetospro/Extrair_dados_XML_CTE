import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import streamlit as st
from io import BytesIO

def formatar_cnpj(cnpj):
    """Formata CNPJ com pontuação"""
    if cnpj and len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj

def formatar_cep(cep):
    """Formata CEP com hífen"""
    if cep and len(cep) == 8:
        return f"{cep[:5]}-{cep[5:8]}"
    return cep

def formatar_data(data_str):
    """Formata data para padrão brasileiro"""
    try:
        if 'T' in data_str:
            data = datetime.strptime(data_str.split('T')[0], "%Y-%m-%d")
            return data.strftime("%d/%m/%Y")
        return data_str
    except:
        return data_str

def formatar_moeda(valor):
    """Formata valores para o padrão monetário brasileiro"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def processar_cte(xml_path):
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
            'CNPJ Emitente': formatar_cnpj(emit.find('cte:CNPJ', ns).text if emit is not None and emit.find('cte:CNPJ', ns) is not None else ''),
            'Nome Emitente': emit.find('cte:xNome', ns).text if emit is not None and emit.find('cte:xNome', ns) is not None else '',
            'CEP Emitente': formatar_cep(emit.find('cte:enderEmit/cte:CEP', ns).text if emit is not None and emit.find('cte:enderEmit/cte:CEP', ns) is not None else ''),
            'Cidade Emitente': emit.find('cte:enderEmit/cte:xMun', ns).text if emit is not None and emit.find('cte:enderEmit/cte:xMun', ns) is not None else '',
            'UF Emitente': emit.find('cte:enderEmit/cte:UF', ns).text if emit is not None and emit.find('cte:enderEmit/cte:UF', ns) is not None else '',
            'CNPJ Remetente': formatar_cnpj(rem.find('cte:CNPJ', ns).text if rem is not None and rem.find('cte:CNPJ', ns) is not None else ''),
            'Nome Remetente': rem.find('cte:xNome', ns).text if rem is not None and rem.find('cte:xNome', ns) is not None else '',
            'CEP Remetente': formatar_cep(rem.find('cte:enderReme/cte:CEP', ns).text if rem is not None and rem.find('cte:enderReme/cte:CEP', ns) is not None else ''),
            'Cidade Remetente': rem.find('cte:enderReme/cte:xMun', ns).text if rem is not None and rem.find('cte:enderReme/cte:xMun', ns) is not None else '',
            'UF Remetente': rem.find('cte:enderReme/cte:UF', ns).text if rem is not None and rem.find('cte:enderReme/cte:UF', ns) is not None else '',
            'CNPJ Destinatário': formatar_cnpj(dest.find('cte:CNPJ', ns).text if dest is not None and dest.find('cte:CNPJ', ns) is not None else ''),
            'Nome Destinatário': dest.find('cte:xNome', ns).text if dest is not None and dest.find('cte:xNome', ns) is not None else '',
            'CEP Destinatário': formatar_cep(dest.find('cte:enderDest/cte:CEP', ns).text if dest is not None and dest.find('cte:enderDest/cte:CEP', ns) is not None else ''),
            'Cidade Destinatário': dest.find('cte:enderDest/cte:xMun', ns).text if dest is not None and dest.find('cte:enderDest/cte:xMun', ns) is not None else '',
            'UF Destinatário': dest.find('cte:enderDest/cte:UF', ns).text if dest is not None and dest.find('cte:enderDest/cte:UF', ns) is not None else '',
            'Valor Carga': formatar_moeda(infCarga.find('cte:vCarga', ns).text if infCarga is not None and infCarga.find('cte:vCarga', ns) is not None else '0'),
            'Valor Frete': formatar_moeda(vPrest.text if vPrest is not None else '0'),
            'Chave Carga': infNFe.find('cte:chave', ns).text if infNFe is not None and infNFe.find('cte:chave', ns) is not None else '',
            'Número Carga': ide.find('cte:nCT', ns).text if ide is not None else '',  # Usando número do CT-e como proxy
            'Peso (kg)': f"{peso:.3f}",
            'Data Emissão': formatar_data(ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else ''),
            'Status': status
        }
    except Exception as e:
        st.error(f"Erro ao processar CT-e: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="Processador de CT-e", layout="wide")
    
    st.title("📄 Processador de Arquivos CT-e")
    st.markdown("""
    Esta aplicação processa arquivos XML de Conhecimento de Transporte Eletrônico (CT-e) e extrai as informações principais.
    """)
    
    # Upload de arquivos
    uploaded_files = st.file_uploader("Selecione os arquivos XML", type="xml", accept_multiple_files=True)
    
    if uploaded_files:
        resultados = []
        
        for uploaded_file in uploaded_files:
            try:
                # Salva temporariamente o arquivo para processamento
                with open(uploaded_file.name, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                dados = processar_cte(uploaded_file.name)
                if dados:
                    resultados.append(dados)
                
                # Remove o arquivo temporário
                os.remove(uploaded_file.name)
            except Exception as e:
                st.error(f"Erro ao processar {uploaded_file.name}: {str(e)}")
        
        if resultados:
            df = pd.DataFrame(resultados)
            
            st.success(f"Processados {len(resultados)} arquivos CT-e")
            st.dataframe(df)
            
            # Botão para exportar para Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="Exportar para Excel",
                data=output.getvalue(),
                file_name=f"CTe_Resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum dado válido encontrado nos arquivos")

if __name__ == "__main__":
    # Configuração especial para deploy no Render
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # Configurações específicas para produção
        from streamlit.web.cli import main as st_main
        sys.argv = [
            "streamlit",
            "run",
            "app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ]
        st_main()
    else:
        # Modo de desenvolvimento local
        main()
