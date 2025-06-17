from flask import Flask, request, send_file, jsonify, render_template_string
from lxml import etree
import pandas as pd
from io import BytesIO
import os
from datetime import datetime

app = Flask(__name__)

# [...] (Manter as funções parse_cte e generate_excel existentes)

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
        <style>
            .container {
                max-width: 800px;
                margin-top: 50px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
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
                            <input class="form-control" type="file" name="file" accept=".xml" required>
                            <div class="form-text">Apenas arquivos XML no formato CT-e</div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">
                            <span id="submitText">Processar CT-e</span>
                            <span id="spinner" class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
                        </button>
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
                    <p>Seu arquivo foi processado com sucesso.</p>
                    <a id="downloadBtn" href="#" class="btn btn-success w-100">
                        <i class="bi bi-download"></i> Baixar Planilha
                    </a>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Mostrar loading
                document.getElementById('loading').style.display = 'block';
                document.getElementById('submitText').textContent = 'Processando...';
                document.getElementById('spinner').style.display = 'inline-block';
                
                // Enviar o formulário via AJAX
                const formData = new FormData(this);
                fetch(this.action, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) throw new Error('Erro no processamento');
                    return response.blob();
                })
                .then(blob => {
                    // Esconder loading
                    document.getElementById('loading').style.display = 'none';
                    
                    // Criar link para download
                    const url = window.URL.createObjectURL(blob);
                    document.getElementById('downloadBtn').href = url;
                    
                    // Mostrar resultado
                    document.getElementById('resultContainer').style.display = 'block';
                    document.getElementById('submitText').textContent = 'Processar outro CT-e';
                    document.getElementById('spinner').style.display = 'none';
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('submitText').textContent = 'Processar CT-e';
                    document.getElementById('spinner').style.display = 'none';
                    alert('Erro: ' + error.message);
                });
            });
        </script>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

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
            download_name=f"CTe_{data.get('Número CT-e', '')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
