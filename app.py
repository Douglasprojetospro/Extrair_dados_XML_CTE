from flask import Flask, request, send_file, jsonify, render_template_string
from lxml import etree
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
import logging

app = Flask(__name__)

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_cte(xml_content):
    """Função para extrair dados do XML do CT-e com tratamento robusto"""
    try:
        # Tentar decodificar se for bytes
        if isinstance(xml_content, bytes):
            try:
                xml_content = xml_content.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = xml_content.decode('latin-1')

        # Parse do XML
        root = etree.fromstring(xml_content)
        
        # Namespaces (ajuste conforme necessário)
        ns = {
            'cte': 'http://www.portalfiscal.inf.br/cte',
            'ns2': 'http://www.portalfiscal.inf.br/cte'  # Alternativo
        }
        
        # Função auxiliar para extração segura de dados
        def safe_extract(path, default='N/A', namespace=ns):
            result = root.xpath(path, namespaces=namespace)
            return result[0] if result else default

        # Extração dos dados principais com fallbacks
        data = {
            'Número CT-e': safe_extract('//cte:infCte/cte:ide/cte:nCT/text()|//ns2:infCte/ns2:ide/ns2:nCT/text()'),
            'Série': safe_extract('//cte:infCte/cte:ide/cte:serie/text()|//ns2:infCte/ns2:ide/ns2:serie/text()'),
            'Data Emissão': safe_extract('//cte:infCte/cte:ide/cte:dhEmi/text()|//ns2:infCte/ns2:ide/ns2:dhEmi/text()'),
            'Valor Total': safe_extract('//cte:infCte/cte:vRec/text()|//ns2:infCte/ns2:vRec/text()', '0.00'),
            'Remetente': safe_extract('//cte:rem/cte:xNome/text()|//ns2:rem/ns2:xNome/text()'),
            'Destinatário': safe_extract('//cte:dest/cte:xNome/text()|//ns2:dest/ns2:xNome/text()'),
            'UF Origem': safe_extract('//cte:infCte/cte:ide/cte:UFIni/text()|//ns2:infCte/ns2:ide/ns2:UFIni/text()'),
            'Município Origem': safe_extract('//cte:infCte/cte:ide/cte:municIni/text()|//ns2:infCte/ns2:ide/ns2:municIni/text()'),
            'UF Destino': safe_extract('//cte:infCte/cte:ide/cte:UFFim/text()|//ns2:infCte/ns2:ide/ns2:UFFim/text()'),
            'Município Destino': safe_extract('//cte:infCte/cte:ide/cte:municFim/text()|//ns2:infCte/ns2:ide/ns2:municFim/text()'),
            'Chave de Acesso': safe_extract('//cte:infCte/@Id|//ns2:infCte/@Id', '').replace('CTe', '')
        }
        
        # Formatação de campos combinados
        data['Origem'] = f"{data['UF Origem']} - {data['Município Origem']}"
        data['Destino'] = f"{data['UF Destino']} - {data['Município Destino']}"
        
        return data
        
    except Exception as e:
        logger.error(f"Erro ao processar XML: {str(e)}")
        return {'error': f'Erro ao processar XML: {str(e)}'}

def generate_excel(data):
    """Função para gerar o arquivo Excel com tratamento de erros"""
    try:
        # Criar DataFrame com os dados
        df = pd.DataFrame([data])
        
        # Ordenar colunas e remover campos auxiliares
        columns_order = [
            'Número CT-e', 'Série', 'Chave de Acesso', 'Data Emissão', 'Valor Total',
            'Remetente', 'Destinatário', 'Origem', 'Destino'
        ]
        df = df[columns_order]
        
        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados CT-e')
            worksheet = writer.sheets['Dados CT-e']
            
            # Ajustar largura das colunas
            for column in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = max_length + 2
        
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Erro ao gerar Excel: {str(e)}")
        return None

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema de Processamento de CT-e</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            .container {
                max-width: 800px;
                margin-top: 50px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo img {
                max-height: 80px;
                margin-bottom: 15px;
            }
            .card {
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .btn-primary {
                background-color: #2c3e50;
                border-color: #2c3e50;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .result-container {
                display: none;
                margin-top: 30px;
            }
            .error-message {
                color: #dc3545;
                margin-top: 10px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1 class="text-primary">📄 Processador de CT-e</h1>
                <p class="text-muted">Sistema profissional para extração de dados de Conhecimento de Transporte Eletrônico</p>
            </div>
            
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Envie seu arquivo CT-e</h5>
                    <form id="uploadForm" action="/api/process_cte" method="post" enctype="multipart/form-data">
                        <div class="mb-3">
                            <input class="form-control" type="file" name="file" id="xmlFile" accept=".xml" required>
                            <div class="form-text">Apenas arquivos XML no formato CT-e</div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100" id="submitBtn">
                            <span id="submitText">Processar CT-e</span>
                            <span id="spinner" class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
                        </button>
                        <div id="errorMessage" class="error-message"></div>
                    </form>
                </div>
            </div>

            <div id="loading" class="loading">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Processando...</span>
                </div>
                <p class="mt-2">Processando seu arquivo, por favor aguarde...</p>
            </div>

            <div id="resultContainer" class="result-container card">
                <div class="card-body">
                    <h5 class="card-title text-success">Processamento concluído!</h5>
                    <p id="successMessage">Seu arquivo foi processado com sucesso.</p>
                    <a id="downloadBtn" href="#" class="btn btn-success w-100">
                        <i class="bi bi-download"></i> Baixar Planilha
                    </a>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Reset estados
                document.getElementById('errorMessage').style.display = 'none';
                document.getElementById('resultContainer').style.display = 'none';
                
                // Validar arquivo
                const fileInput = document.getElementById('xmlFile');
                if (!fileInput.files || fileInput.files.length === 0) {
                    showError('Por favor, selecione um arquivo.');
                    return;
                }
                
                const file = fileInput.files[0];
                if (!file.name.toLowerCase().endsWith('.xml')) {
                    showError('Por favor, envie um arquivo XML.');
                    return;
                }
                
                // Mostrar loading
                document.getElementById('loading').style.display = 'block';
                document.getElementById('submitText').textContent = 'Processando...';
                document.getElementById('spinner').style.display = 'inline-block';
                document.getElementById('submitBtn').disabled = true;
                
                // Enviar o formulário via AJAX
                const formData = new FormData(this);
                fetch(this.action, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.error || 'Erro no processamento');
                        });
                    }
                    return response.blob();
                })
                .then(blob => {
                    // Esconder loading
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('submitBtn').disabled = false;
                    
                    // Criar link para download
                    const url = window.URL.createObjectURL(blob);
                    const downloadBtn = document.getElementById('downloadBtn');
                    downloadBtn.href = url;
                    
                    // Configurar nome do arquivo
                    const filename = `CTe_${new Date().toISOString().slice(0,10)}.xlsx`;
                    downloadBtn.download = filename;
                    
                    // Mostrar resultado
                    document.getElementById('resultContainer').style.display = 'block';
                    document.getElementById('submitText').textContent = 'Processar outro CT-e';
                    document.getElementById('spinner').style.display = 'none';
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('submitText').textContent = 'Processar CT-e';
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('submitBtn').disabled = false;
                    showError(error.message);
                });
            });
            
            function showError(message) {
                const errorElement = document.getElementById('errorMessage');
                errorElement.textContent = message;
                errorElement.style.display = 'block';
            }
        </script>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

@app.route('/api/process_cte', methods=['POST'])
def process_cte():
    """Endpoint para processar CT-e com tratamento completo de erros"""
    logger.info("Recebida requisição para processar CT-e")
    
    if 'file' not in request.files:
        logger.warning("Nenhum arquivo recebido")
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.warning("Nome de arquivo vazio")
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    
    if not file.filename.lower().endswith('.xml'):
        logger.warning(f"Formato inválido: {file.filename}")
        return jsonify({'error': 'Formato inválido. Envie um XML'}), 400
    
    try:
        logger.info(f"Processando arquivo: {file.filename}")
        file_content = file.read()
        
        # Verificar se o arquivo não está vazio
        if not file_content:
            logger.warning("Arquivo vazio recebido")
            return jsonify({'error': 'Arquivo vazio'}), 400
            
        data = parse_cte(file_content)
        
        if 'error' in data:
            logger.error(f"Erro ao parsear CT-e: {data['error']}")
            return jsonify(data), 400
        
        logger.info(f"CT-e processado com sucesso: {data.get('Número CT-e', 'N/A')}")
        
        excel_file = generate_excel(data)
        if not excel_file:
            logger.error("Falha ao gerar arquivo Excel")
            return jsonify({'error': 'Falha ao gerar Excel'}), 500
        
        filename = f"CTe_{data.get('Número CT-e', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        logger.info(f"Enviando arquivo: {filename}")
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
