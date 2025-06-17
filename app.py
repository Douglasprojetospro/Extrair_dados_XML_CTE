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

        # Função auxiliar para extração segura
        def safe_get(element, path):
            if element is None:
                return ''
            found = element.find(path, namespaces=ns)
            return found.text if found is not None else ''

        # Dados básicos
        ide = inf_cte.find('.//cte:ide', namespaces=ns)
        emit = inf_cte.find('.//cte:emit', namespaces=ns)
        rem = inf_cte.find('.//cte:rem', namespaces=ns) or inf_cte.find('.//cte:exped', namespaces=ns)
        dest = inf_cte.find('.//cte:dest', namespaces=ns) or inf_cte.find('.//cte:receb', namespaces=ns)
        inf_carga = inf_cte.find('.//cte:infCarga', namespaces=ns)
        v_prest = inf_cte.find('.//cte:vPrest', namespaces=ns)

        # Valor do frete - VERSÃO CORRIGIDA
        frete_valor = ''
        if v_prest is not None:
            for comp in v_prest.findall('.//cte:Comp', namespaces=ns):
                nome_comp = comp.find('.//cte:xNome', namespaces=ns)
                if nome_comp is not None and nome_comp.text == 'FRETE VALOR':
                    valor_comp = comp.find('.//cte:vComp', namespaces=ns)
                    frete_valor = valor_comp.text if valor_comp is not None else ''
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
            'CEP Remetente': safe_get(rem, './/cte:enderReme/cte:CEP') or safe_get(rem, './/cte:enderExped/cte:CEP'),
            'Cidade Remetente': safe_get(rem, './/cte:enderReme/cte:xMun') or safe_get(rem, './/cte:enderExped/cte:xMun'),
            'UF Remetente': safe_get(rem, './/cte:enderReme/cte:UF') or safe_get(rem, './/cte:enderExped/cte:UF'),
            'CNPJ Destinatário': safe_get(dest, './/cte:CNPJ'),
            'Nome Destinatário': safe_get(dest, './/cte:xNome'),
            'CEP Destinatário': safe_get(dest, './/cte:enderDest/cte:CEP') or safe_get(dest, './/cte:enderReceb/cte:CEP'),
            'Cidade Destinatário': safe_get(dest, './/cte:enderDest/cte:xMun') or safe_get(dest, './/cte:enderReceb/cte:xMun'),
            'UF Destinatário': safe_get(dest, './/cte:enderDest/cte:UF') or safe_get(dest, './/cte:enderReceb/cte:UF'),
            'Valor Carga': safe_get(inf_carga, './/cte:vCarga'),
            'Valor Frete': frete_valor,
            'Chave Carga': safe_get(inf_cte, './/cte:infDoc/cte:infNFe/cte:chave'),
            'Peso (kg)': peso,
            'Data Emissão': safe_get(ide, './/cte:dhEmi'),
            'Status': safe_get(prot_cte, './/cte:xMotivo')
        }

    except Exception as e:
        return {'error': f'Erro ao processar XML: {str(e)}'}

# ... [o resto do arquivo permanece igual]
