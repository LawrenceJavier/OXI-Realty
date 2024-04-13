import os
from pyairtable import Api
import pandas as pd
import streamlit as st
import json
import requests
import openpyxl

#############
#  Secrets  #
#############

base_id = "app3vwLcsaEjJGPl6"
table_id = "tblCzTZXgoRu9Dypt"
AIRTABLE_API_KEY = "pat86Ki579uDzXanU.e3c6cfeeddfb5963697d0fe75cc1fe159ad7ce696aa0bc230f9e7e6f55748b9a"

#############
# Funciones #
#############

def create_headers():
    headers = {
        'Authorization': 'Bearer ' + str(AIRTABLE_API_KEY),
        'Content-Type': 'application/json',
    }
    return headers

def get_df(file_buffer, numero_columna_para_nombres):
    df = pd.read_excel(file_buffer, engine='openpyxl', header=numero_columna_para_nombres)
    return df

def join_excels(df_new, df_AT):
    print(len(df_AT.columns))
    result = pd.concat([df_AT, df_new], join='outer')
    print(len(df_AT.columns))
    # merged_df = result.drop_duplicates(subset='CODIGO INMUEBLE COMPLETO', keep='first')
    return result

def seleccionar_columnas(nombre_archivo):
    if nombre_archivo == "Coral homes WIP's & suelos.xlsx":
        return 0
    elif nombre_archivo == "Coral Homes REO.xlsx":
        return 1
    elif nombre_archivo == "Anticipa & Aliseda.xlsx":
        return 1
    elif nombre_archivo == "Producto Libre OXI.xlsx":
        return 0

def mapear_columnas(nombre_archivo, df_subido):
    if nombre_archivo == "Coral homes WIP's & suelos.xlsx":
        print()
    elif nombre_archivo == "Coral Homes REO.xlsx":
        print()
    elif nombre_archivo == "Anticipa & Aliseda.xlsx":
        df_subido = df_subido.drop('ID ATENEA', axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'EMPRESA PROPIETARIA', 'TIPOLOGIA INMUEBLE', 'REFERENCIA CATASTRAL', 'CCAA', 'PROVINCIA', 'CIUDAD', 'DIRECCION COMPLETA', 'CODIGO POSTAL', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE', 'SITUACIÓN OCUPACIONAL']
        return df_subido
    elif nombre_archivo == "Producto Libre OXI.xlsx":
        print()


#############
#  Paginas  #
#############

def page_ingestion():
    st.title("Actualización de perímetro")

    api = Api(AIRTABLE_API_KEY)
    table = api.table(base_id, table_id)
    df_AT = pd.json_normalize(table.all())
    df_AT.columns = df_AT.columns.str.replace('fields.', '')
    st.write(df_AT)
    
    # nombres = ["OXI_ID", "CODIGO INMUEBLE COMPLETO","EMPRESA PROPIETARIA","TIPOLOGIA INMUEBLE","REFERENCIA CATASTRAL","CCAA","PROVINCIA","CIUDAD","DIRECCIÓN COMPLETA","CODIGO POSTAL","ASKING PRICE","NUMERO DORMITORIOS","NUMERO BAÑOS","SUPERFICIE","SITUACIÓN OCUPACIONAL","FIELD AGENT ASSIGNED","FASE JUDICIAL","CLIENTE" ,"TIPO DE OPERACIÓN","PUBLISHED","OFFER STATUS","IBI","GASTOS COMUNIDAD","RESERVA-ARRAS AGREEMENT","OFFER QUANTITY","OXI FEES","NET FEES OXI","FIELD AGENTE FEES","OXI FEES (VAT)","FIELD AGENT FESS (VAT)","FASE RESERVA","FASE PBC","NOTARY","COMENTARIOS","HONORARIOS","ACTIVO EN COLABORACIÓN","OCUPACIÓN","VULNERABILIDAD","COMENTARIO GENERAL"]
    # df = pd.DataFrame(columns=nombres)
    
    uploaded_files = st.file_uploader("Selecciona archivo:", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            numero_columna_para_nombres = seleccionar_columnas(uploaded_file.name)
            df_subido = get_df(uploaded_file, numero_columna_para_nombres)
            df_subido = mapear_columnas(uploaded_file.name, df_subido)
            st.write(df_subido.head())
            # Falta mapear las columnas de los diferentes dfs a el formato estandar par unificarlos
            # Del df total descargado de AT me quedo solo 
            df = join_excels(df_subido, df_AT)

    st.header('Crear nuevo perimetro')
    if st.button('Crear nuevo perimetro', type="primary"):
        st.write("Nuevo perímetro:")
        st.write(df)

def page_contratos():
    st.title("Página de Función 1")
    st.write("Esta es la página de la Función 1.")

def page_funcion2():
    st.title("Página de Función 2")
    st.write("Esta es la página de la Función 2.")

#############
#    Main   #
#############

st.set_page_config(page_title="OXI Realty")

# Configura la barra lateral
st.sidebar.title("OXI REALTY")
page = st.sidebar.selectbox('Seleccione una página',
                            ['Perímetro', 'Generación de contratos', 'Otras funcionalidades'])

# Mostrar la página seleccionada
if page == 'Perímetro':
    page_ingestion()
elif page == 'Generación de contratos':
    page_contratos()
elif page == 'Otras funcionalidades':
    page_funcion2()
