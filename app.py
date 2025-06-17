import xml.etree.ElementTree as ET
import pandas as pd

def processar_cte(xml_path):
    """Extrai os dados do CT-e do arquivo XML e retorna como um dicionário"""
    try:
        # Namespace utilizado no XML
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        
        # Parse do XML
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
        print(f"Erro ao processar o XML {xml_path}: {str(e)}")
        return None

def gerar_relatorio(dados):
    """Gera um relatório a partir dos dados extraídos"""
    if dados:
        df = pd.DataFrame([dados])
        print(df)
        return df
    else:
        print("Nenhum dado válido encontrado.")
        return None

# Exemplo de uso
xml_path = 'caminho/do/seu/arquivo.xml'
dados = processar_cte(xml_path)
relatorio = gerar_relatorio(dados)
