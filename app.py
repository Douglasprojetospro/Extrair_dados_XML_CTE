from flask import Flask, request, send_file, jsonify
from lxml import etree
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)

def parse_cte(xml_content):
    """Extrai dados do CT-e XML"""
    try:
        root = etree.fromstring(xml_content)
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        
        inf_cte = root.find('.//cte:infCte', namespaces=ns)
        prot_cte = root.find('.//cte:infProt', namespaces=ns)

        # Dados básicos
        ide = inf_cte.find('.//cte:ide', namespaces=ns)
        emit = inf_cte.find('.//cte:emit', namespaces=ns)
        rem = inf_cte.find('.//cte:rem', namespaces=ns)
        dest = inf_cte.find('.//cte:dest', namespaces=ns)
        inf_carga = inf_cte.find('.//cte:infCarga', namespaces=ns)
        v_prest = inf_cte.find('.//cte:vPrest', namespaces=ns)

        # Extração segura de dados
        def safe_get(element, path, attr=None):
            if element is None:
                return ''
            found = element.find(path, namespaces=ns)
            if found is None:
                return ''
            return found.text if attr is None else found.get(attr)

        # Valor do frete
        frete_valor = ''
        if v_prest is not None:
            for comp in v_prest.findall('.//cte:Comp', namespaces=ns):
                if safe_get(comp, './/cte:xNome') == 'FRETE VALOR':
                    frete_valor = safe_get(comp, './/cte:vComp')
                    break

        # Peso (kg)
        peso = ''
        if inf_carga is not None:
            for inf_q in inf_carga.findall('.//cte:infQ', namespaces=ns):
                if safe_get(inf_q, './/cte:tpMed') == 'PESO REAL':
                    peso = safe_get(inf_q, './/cte:qCarga')
                    break

        return {
            'Número CT-e': safe_get(ide, './/cte:nCT'),
            'Chave CT-e': safe_get(prot_cte, './/cte:chCTe'),
            'CNPJ Emitente': safe_get(emit, './/cte:CNPJ'),
            'Nome Emitente': safe_get(emit, './/cte:xNome'),
            'CEP Emitente': safe_get(emit, './/cte:enderEmit/cte:CEP'),
            'Cidade Emitente': safe_get(emit, './/cte:enderEmit/cte:xMun'),
            'UF Emitente': safe_get(emit, './/cte:enderEmit/cte:UF'),
            'CNPJ Remetente': safe_get(rem, './/cte:CNPJ'),
            'Nome Remetente': safe_get(rem, './/cte:xNome'),
            'CEP Remetente': safe_get(rem, './/cte:enderReme/cte:CEP'),
            'Cidade Remetente': safe_get(rem, './/cte:enderReme/cte:xMun'),
            'UF Remetente': safe_get(rem, './/cte:enderReme/cte:UF'),
            'CNPJ Destinatário': safe_get(dest, './/cte:CNPJ'),
            'Nome Destinatário': safe_get(dest, './/cte:xNome'),
            'CEP Destinatário': safe_get(dest, './/cte:enderDest/cte:CEP'),
            'Cidade Destinatário': safe_get(dest, './/cte:enderDest/cte:xMun'),
            'UF Destinatário': safe_get(dest, './/cte:enderDest/cte:UF'),
            'Valor Carga': safe_get(inf_carga, './/cte:vCarga'),
            'Valor Frete': frete_valor,
            'Chave Carga': safe_get(inf_cte, './/cte:infDoc/cte:infNFe/cte:chave'),
            'Peso (kg)': peso,
            'Data Emissão': safe_get(ide, './/cte:dhEmi'),
            'Status': safe_get(prot_cte, './/cte:xMotivo')
        }

    except Exception as e:
        return {'error': f'Erro ao processar XML: {str(e)}'}

def generate_excel(data):
    """Gera arquivo Excel a partir dos dados"""
    try:
        df = pd.DataFrame([data])
        
        # Formatação de valores
        numeric_cols = ['Valor Carga', 'Valor Frete', 'Peso (kg)']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
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
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajusta largura das colunas
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        
        output.seek(0)
        return output
    
    except Exception as e:
        return None

@app.route('/api/process_cte', methods=['POST'])
def process_cte():
    """Endpoint para processar CT-e"""
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    
    if not file.filename.lower().endswith('.xml'):
        return jsonify({'error': 'Formato inválido. Envie um XML'}), 400
    
    try:
        data = parse_cte(file.read())
        if 'error' in data:
            return jsonify(data), 400
        
        excel_file = generate_excel(data)
        if not excel_file:
            return jsonify({'error': 'Falha ao gerar Excel'}), 500
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"cte_{data.get('Número CT-e', '')}.xlsx"
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return """
    <h1>API de Extração de CT-e</h1>
    <p>Envie um XML via POST para /api/process_cte</p>
    <form action="/api/process_cte" method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".xml">
      <button type="submit">Enviar</button>
    </form>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
