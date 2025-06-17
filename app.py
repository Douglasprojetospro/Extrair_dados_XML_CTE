from flask import Flask, request, send_file, jsonify, render_template_string
from lxml import etree
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
import logging

# Configuração básica do Flask
app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_cte(xml_content):
    """Processa o XML do CT-e e extrai os dados principais com tratamento de erros"""
    try:
        # Decodificação segura do conteúdo
        if isinstance(xml_content, bytes):
            try:
                xml_content = xml_content.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_content.decode('latin-1')

        # Parse do XML
        root = etree.fromstring(xml_content)
        
        # Namespaces alternativos para compatibilidade
        ns = {
            'cte': 'http://www.portalfiscal.inf.br/cte',
            'ns2': 'http://www.portalfiscal.inf.br/cte'
        }
        
        # Função auxiliar para extração segura
        def safe_xpath(path, default='N/A'):
            for namespace in [ns['cte'], ns['ns2']]:
                result = root.xpath(path.replace('cte:', f'{namespace.split("/")[-1]}:'), namespaces={'ns': namespace})
                if result:
                    return result[0]
            return default

        # Dados essenciais do CT-e
        data = {
            'Número CT-e': safe_xpath('//cte:infCte/cte:ide/cte:nCT/text()'),
            'Série': safe_xpath('//cte:infCte/cte:ide/cte:serie/text()'),
            'Chave de Acesso': safe_xpath('//cte:infCte/@Id', '').replace('CTe', ''),
            'Data Emissão': safe_xpath('//cte:infCte/cte:ide/cte:dhEmi/text()'),
            'Valor Total': safe_xpath('//cte:infCte/cte:vRec/text()', '0.00'),
            'Remetente': safe_xpath('//cte:rem/cte:xNome/text()'),
            'Destinatário': safe_xpath('//cte:dest/cte:xNome/text()'),
            'UF Origem': safe_xpath('//cte:infCte/cte:ide/cte:UFIni/text()'),
            'Município Origem': safe_xpath('//cte:infCte/cte:ide/cte:municIni/text()'),
            'UF Destino': safe_xpath('//cte:infCte/cte:ide/cte:UFFim/text()'),
            'Município Destino': safe_xpath('//cte:infCte/cte:ide/cte:municFim/text()')
        }
        
        # Campos calculados
        data['Origem'] = f"{data['UF Origem']} - {data['Município Origem']}"
        data['Destino'] = f"{data['UF Destino']} - {data['Município Destino']}"
        
        return data
        
    except Exception as e:
        logger.error(f"Erro no parse_cte: {str(e)}")
        return {'error': f'Falha ao processar XML: {str(e)}'}

def generate_excel(data):
    """Gera o arquivo Excel formatado a partir dos dados"""
    try:
        # Criação do DataFrame
        df = pd.DataFrame([data])
        
        # Ordenação e seleção de colunas
        columns_order = [
            'Número CT-e', 'Série', 'Chave de Acesso', 'Data Emissão', 'Valor Total',
            'Remetente', 'Destinatário', 'Origem', 'Destino'
        ]
        df = df[columns_order]
        
        # Geração do Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CT-e')
            
            # Formatação automática das colunas
            worksheet = writer.sheets['CT-e']
            for col in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in col)
                worksheet.column_dimensions[col[0].column_letter].width = max_length + 2
        
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Erro no generate_excel: {str(e)}")
        return None

@app.route('/')
def home():
    """Rota principal com interface HTML"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Processador de CT-e</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            .container { max-width: 800px; margin-top: 50px; }
            .logo { text-align: center; margin-bottom: 30px; }
            .card { border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .loading { display: none; text-align: center; margin: 20px 0; }
            #errorAlert { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1 class="text-primary">📄 Processador de CT-e</h1>
                <p class="text-muted">Converta seus CT-e XML para Excel automaticamente</p>
            </div>
            
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Envie seu CT-e</h5>
                    <form id="uploadForm" enctype="multipart/form-data">
                        <div class="mb-3">
                            <input class="form-control" type="file" name="file" accept=".xml" required>
                            <div class="form-text">Apenas arquivos XML no padrão CT-e</div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100" id="submitBtn">
                            <span id="submitText">Processar</span>
                            <span id="spinner" class="spinner-border spinner-border-sm d-none"></span>
                        </button>
                    </form>
                    <div id="errorAlert" class="alert alert-danger mt-3 d-none"></div>
                </div>
            </div>

            <div id="loading" class="loading">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Processando seu arquivo...</p>
            </div>

            <div id="resultSection" class="card mt-3 d-none">
                <div class="card-body text-center">
                    <h5 class="text-success">✅ Pronto!</h5>
                    <a id="downloadLink" href="#" class="btn btn-success mt-2">
                        <i class="bi bi-download"></i> Baixar Planilha
                    </a>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                // Reset UI
                document.getElementById('errorAlert').classList.add('d-none');
                document.getElementById('resultSection').classList.add('d-none');
                document.getElementById('loading').style.display = 'block';
                document.getElementById('submitBtn').disabled = true;
                document.getElementById('spinner').classList.remove('d-none');
                document.getElementById('submitText').textContent = 'Processando...';
                
                try {
                    const formData = new FormData(e.target);
                    const response = await fetch('/api/process_cte', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.error || 'Erro desconhecido');
                    }

                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    document.getElementById('downloadLink').href = url;
                    document.getElementById('downloadLink').download = 
                        `CTe_${new Date().toISOString().slice(0,10)}.xlsx`;
                    
                    document.getElementById('resultSection').classList.remove('d-none');
                } catch (error) {
                    const errorAlert = document.getElementById('errorAlert');
                    errorAlert.textContent = error.message;
                    errorAlert.classList.remove('d-none');
                } finally {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('submitBtn').disabled = false;
                    document.getElementById('spinner').classList.add('d-none');
                    document.getElementById('submitText').textContent = 'Processar';
                }
            });
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

@app.route('/api/process_cte', methods=['POST'])
def api_process_cte():
    """Endpoint para processamento do CT-e"""
    try:
        # Validação do arquivo
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if not file.filename.lower().endswith('.xml'):
            return jsonify({'error': 'Formato inválido. Envie um XML'}), 400
        
        # Processamento
        xml_data = file.read()
        if not xml_data:
            return jsonify({'error': 'Arquivo vazio'}), 400
            
        parsed_data = parse_cte(xml_data)
        if 'error' in parsed_data:
            return jsonify(parsed_data), 400
        
        excel_file = generate_excel(parsed_data)
        if not excel_file:
            return jsonify({'error': 'Falha ao gerar planilha'}), 500
        
        # Nome do arquivo de saída
        filename = f"CTe_{parsed_data.get('Número CT-e', '')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro na API: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
