import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from io import BytesIO

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Certifique-se de que a pasta de uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class CTeProcessor:
    def __init__(self):
        self.resultados_df = pd.DataFrame()

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
                'Número Carga': ide.find('cte:nCT', ns).text if ide is not None else '',  # Usando número do CT-e como proxy
                'Peso (kg)': f"{peso:.3f}",
                'Data Emissão': self.formatar_data(ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else ''),
                'Status': status
            }
        except Exception as e:
            print(f"Erro ao processar CT-e: {str(e)}")
            return None

    def processar_arquivos(self, arquivos):
        """Processa múltiplos arquivos XML"""
        resultados = []
        
        for arquivo in arquivos:
            try:
                caminho = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(arquivo.filename))
                arquivo.save(caminho)
                dados = self.processar_cte(caminho)
                if dados:
                    resultados.append(dados)
                # Remove o arquivo após processamento
                os.remove(caminho)
            except Exception as e:
                print(f"Erro ao processar {arquivo.filename}: {str(e)}")

        if resultados:
            self.resultados_df = pd.DataFrame(resultados)
            return True
        return False

    def exportar_excel(self):
        """Exporta os resultados para Excel em memória"""
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        self.resultados_df.to_excel(writer, index=False)
        writer.save()
        output.seek(0)
        return output

cte_processor = CTeProcessor()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'arquivos' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        arquivos = request.files.getlist('arquivos')
        if not arquivos or all(f.filename == '' for f in arquivos):
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

        if cte_processor.processar_arquivos(arquivos):
            # Converter DataFrame para JSON
            resultados_json = cte_processor.resultados_df.to_dict(orient='records')
            return jsonify({
                'success': True,
                'message': f'Processados {len(resultados_json)} arquivos CT-e',
                'data': resultados_json,
                'columns': list(cte_processor.resultados_df.columns)
            })
        else:
            return jsonify({'error': 'Nenhum dado válido encontrado nos arquivos'}), 400

    return render_template('index.html')

@app.route('/download', methods=['GET'])
def download():
    if cte_processor.resultados_df.empty:
        return jsonify({'error': 'Nenhum dado para exportar'}), 400
    
    try:
        output = cte_processor.exportar_excel()
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"CTe_Resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    except Exception as e:
        return jsonify({'error': f'Não foi possível gerar o arquivo: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
