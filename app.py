import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    resultados = []
    if request.method == "POST":
        files = request.files.getlist("xml_files")
        for file in files:
            if file.filename.lower().endswith(".xml"):
                path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
                file.save(path)
                dados = processar_cte(path)
                if dados:
                    resultados.append(dados)
        if resultados:
            df = pd.DataFrame(resultados)
            output_path = os.path.join("resultado.xlsx")
            df.to_excel(output_path, index=False)
            return send_file(output_path, as_attachment=True)
    return render_template("index.html")

def formatar_cnpj(cnpj):
    if cnpj and len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj

def formatar_cep(cep):
    if cep and len(cep) == 8:
        return f"{cep[:5]}-{cep[5:8]}"
    return cep

def formatar_data(data_str):
    try:
        if 'T' in data_str:
            data = datetime.strptime(data_str.split('T')[0], "%Y-%m-%d")
            return data.strftime("%d/%m/%Y")
        return data_str
    except:
        return data_str

def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def processar_cte(xml_path):
    try:
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        tree = ET.parse(xml_path)
        root = tree.getroot()
        cte_proc = root.find('.//cte:CTe', ns) or root

        ide = cte_proc.find('.//cte:ide', ns)
        emit = cte_proc.find('.//cte:emit', ns)
        rem = cte_proc.find('.//cte:rem', ns)
        dest = cte_proc.find('.//cte:dest', ns)
        infCarga = cte_proc.find('.//cte:infCarga', ns)
        vPrest = cte_proc.find('.//cte:vPrest/cte:vTPrest', ns)
        infNFe = cte_proc.find('.//cte:infNFe', ns)
        protCTe = root.find('.//cte:protCTe', ns)

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
            'Número Carga': ide.find('cte:nCT', ns).text if ide is not None else '',
            'Peso (kg)': f"{peso:.3f}",
            'Data Emissão': formatar_data(ide.find('cte:dhEmi', ns).text if ide is not None and ide.find('cte:dhEmi', ns) is not None else ''),
            'Status': status
        }
    except Exception as e:
        print(f"Erro ao processar {xml_path}: {str(e)}")
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
