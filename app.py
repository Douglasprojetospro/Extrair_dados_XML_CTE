#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess
import streamlit as st
from extrator_atributos import ExtratorAtributos

def verifica_instalacoes():
    """Verifica e instala pacotes necessários"""
    pacotes_necessarios = ['streamlit', 'pandas', 'openpyxl', 'XlsxWriter']
    
    for pacote in pacotes_necessarios:
        try:
            __import__(pacote)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

def configuracao_pagina():
    """Configurações iniciais da página"""
    st.set_page_config(
        page_title="Sistema de Extração de Atributos",
        page_icon=":mag:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Correções de compatibilidade
    st.set_option('deprecation.showfileUploaderEncoding', False)
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.set_option('deprecation.showPyplotGlobalUse', False)

def main():
    """Função principal da aplicação"""
    verifica_instalacoes()
    configuracao_pagina()
    
    try:
        extrator = ExtratorAtributos()
    except Exception as e:
        st.error(f"Erro ao iniciar a aplicação: {str(e)}")
        st.error("Por favor, verifique os logs para mais detalhes.")
        sys.exit(1)

if __name__ == "__main__":
    # Modo de execução compatível com Render
    try:
        main()
    except Exception as e:
        st.error(f"Falha crítica: {str(e)}")
        # Tentativa de reinicialização automática
        st.warning("Tentando reiniciar a aplicação...")
        subprocess.call([sys.executable, "-m", "streamlit", "run", __file__])
