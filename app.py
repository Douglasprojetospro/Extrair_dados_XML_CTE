import streamlit as st
from extrator_atributos import ExtratorAtributos

# Corrige comportamentos antigos do Streamlit
st.set_option('deprecation.showfileUploaderEncoding', False)
st.set_option('deprecation.showPyplotGlobalUse', False)

# Inicia a aplicação principal
if __name__ == "__main__":
    ExtratorAtributos()
