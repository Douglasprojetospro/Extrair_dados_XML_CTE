import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from io import BytesIO
import signal

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['PROCESSING_TIMEOUT'] = 30  # segundos por arquivo

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Tempo de processamento excedido")

class CTeProcessor:
    # ... (mantenha os métodos formatadores como estão)

    def processar_cte(self, xml_path):
        """Extrai os dados do CT-e com timeout"""
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(app.config['PROCESSING_TIMEOUT'])
        
        try:
            # Usar parser iterativo para melhor performance
            context = ET.iterparse(xml_path, events=('start', 'end'))
            ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
            
            dados = {}
            for event, elem in context:
                if event == 'end':
                    # Adicione aqui a lógica de extração de dados
                    # Exemplo simplificado:
                    if elem.tag == '{http://www.portalfiscal.inf.br/cte}nCT':
                        dados['Número CT-e'] = elem.text
                    # Limpar elemento após processar para economizar memória
                    elem.clear()
            
            signal.alarm(0)  # Desativa o alarme
            return dados
            
        except TimeoutException:
            print(f"Timeout ao processar {xml_path}")
            return None
        except Exception as e:
            print(f"Erro ao processar CT-e: {str(e)}")
            return None
        finally:
            signal.alarm(0)  # Garante que o alarme seja desativado
            if os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except:
                    pass

    def processar_arquivos(self, arquivos):
        """Processa múltiplos arquivos XML com gerenciamento de recursos"""
        resultados = []
        
        for arquivo in arquivos:
            try:
                caminho = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(arquivo.filename))
                arquivo.save(caminho)
                
                dados = self.processar_cte(caminho)
                if dados:
                    resultados.append(dados)
                    
            except Exception as e:
                print(f"Erro ao processar {arquivo.filename}: {str(e)}")
            finally:
                # Garante que o arquivo seja removido mesmo em caso de erro
                if 'caminho' in locals() and os.path.exists(caminho):
                    try:
                        os.remove(caminho)
                    except:
                        pass

        return resultados

# ... (restante do código permanece igual)

if __name__ == '__main__':
    app.run(debug=True)
