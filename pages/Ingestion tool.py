import os
from pyairtable import Api
import pandas as pd
import streamlit as st
import re
import json
import requests
import openpyxl

#############
#  Secrets  #
#############

base_id = st.secrets["base_id"]
table_id = st.secrets["table_id"]
AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]

#############
# Funciones #
#############

def create_headers():
    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }
    return headers

def seleccionar_columnas(tipo_de_perimetro, uploaded_file):

    if tipo_de_perimetro == 'Coral Homes Wips & Suelos':
        df1 = pd.read_excel(uploaded_file,sheet_name=0, engine='openpyxl', header=0)
        df1 = df1.drop(["UR's Promo", "% Propiedad", f"% Ejecución", "Total Resi Units", "Posesión"], axis=1)
        df1.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'REFERENCIA CATASTRAL', 'CIUDAD', 'PROVINCIA', 'CCAA']
        df2 = pd.read_excel(uploaded_file,sheet_name=1, engine='openpyxl', header=0)
        df2 = df2.drop(["SECTOR", "Gestión UR", "Calificación", "Uso Principal", "% Particpación", "URs por Ámbito","Proindiviso", "Superficie Suelo Propiedad", "EDIFICABILIDAD TOTAL", "EDIFICABILIDAD RESID. LIBRE", "VIVIENDAS TOTALES PROPIEDAD", "VIVIENDAS VPP PROPIEDAD", "VIVIENDAS LIBRES PROPIEDAD"], axis=1)
        df2.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'REFERENCIA CATASTRAL', 'CIUDAD', 'PROVINCIA', 'CCAA', 'TIPOLOGIA INMUEBLE']
        df = pd.concat([df2, df1])
        df_subido = df.reset_index(drop=True)
        return df_subido
    
    elif tipo_de_perimetro == 'Coral Homes':
        df = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
        df_subido = df.drop(['Promoción conjunta', 'Unidades Promoción conjunta','Promoción comercial', 'Unidades Promoción comercial', 'Superficie Solar'], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'CIUDAD', 'PROVINCIA', 'CCAA', 'CODIGO POSTAL', 'REFERENCIA CATASTRAL', 'TIPOLOGIA INMUEBLE', 'SUPERFICIE', 'ASKING PRICE']
        return df_subido
    
    elif tipo_de_perimetro == 'Anticipa & Aliseda':
        df = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
        df_subido = df.drop(['ID ATENEA', 'CODIGO SOCIEDAD'], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'EMPRESA PROPIETARIA', 'TIPOLOGIA INMUEBLE', 'REFERENCIA CATASTRAL', 'CCAA', 'PROVINCIA', 'CIUDAD', 'DIRECCION COMPLETA', 'CODIGO POSTAL', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
        return df_subido
    
    elif tipo_de_perimetro == 'Producto Libre OXI':
        df = pd.read_excel(uploaded_file)
        df_subido = df.drop(["Portfolio", "Construcción", "Año Construcción", "Escalera", "Piso", "FR",  "Coef. Particip", "Expediente Judicial", "Situación"], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'TIPOLOGIA INMUEBLE', 'CCAA', 'PROVINCIA', 'CIUDAD',  'DIRECCION COMPLETA', 'CODIGO POSTAL', 'REFERENCIA CATASTRAL', 'SUPERFICIE', 'ASKING PRICE']
        return df_subido

def actualizar_perimetro(df1, df2):
    df1 = df1.astype(str)
    df2 = df2.astype(str)
    columnas_float = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_float:
        if columna in df1:
            df1[columna] = pd.to_numeric(df1[columna], errors='coerce').astype(float)
        if columna in df2:
            df2[columna] = pd.to_numeric(df2[columna], errors='coerce').astype(float)

    # Mostrar las filas idénticas en ambos DF's
    columnas_fusion = ['CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    columnas_fusion_presentes = [col for col in columnas_fusion if col in df1.columns and col in df2.columns]
    filas_iguales = df1.merge(df2, on=columnas_fusion_presentes)
    ids_coincidentes = filas_iguales['CODIGO INMUEBLE COMPLETO']


    # Filas que solo están en el primer DataFrame
    filas_solo_df1 = df1[~df1['CODIGO INMUEBLE COMPLETO'].isin(df2['CODIGO INMUEBLE COMPLETO'])]
    id_filas_solo_df1 = list(filas_solo_df1["CODIGO INMUEBLE COMPLETO"])


    # Filas que solo están en el segundo DataFrame
    filas_solo_df2 = df2[~df2['CODIGO INMUEBLE COMPLETO'].isin(df1['CODIGO INMUEBLE COMPLETO'])]
    id_filas_solo_df2 = list(filas_solo_df2["CODIGO INMUEBLE COMPLETO"])
    columnas_numericas = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_numericas:
        if columna in filas_solo_df2:
            filas_solo_df2[columna] = filas_solo_df2[columna].fillna(0)

    st.markdown(f"##### {len(ids_coincidentes)} activos ya existentes no modificados")
    st.markdown(f"##### {len(id_filas_solo_df2)} activos nuevos")
    st.markdown(f"##### {len(id_filas_solo_df1)} activos que no aparecen en el nuevo DT")
    
    # Filas en ambos DataFrames pero con al menos un campo modificado
    lista_total = []
    lista_total.extend(ids_coincidentes)
    lista_total.extend(id_filas_solo_df1)
    lista_total.extend(id_filas_solo_df2)
    df2_extendido = pd.merge(df2, df1[['CODIGO INMUEBLE COMPLETO', 'id_numerico', 'id', 'OXI_ID']], on='CODIGO INMUEBLE COMPLETO', how='left')
    df_concatenado = pd.concat([df2_extendido, df1], ignore_index=True)
    df_concatenado = df_concatenado.drop_duplicates(subset=['CODIGO INMUEBLE COMPLETO'], keep='first')
    filas_no_en_lista = df_concatenado[~df_concatenado['CODIGO INMUEBLE COMPLETO'].isin(lista_total)]
    id_filas_diferentes = list(filas_no_en_lista["CODIGO INMUEBLE COMPLETO"])
    
    return filas_iguales, ids_coincidentes, filas_solo_df1, id_filas_solo_df1, filas_solo_df2, id_filas_solo_df2, filas_no_en_lista, id_filas_diferentes

@st.cache_data
def get_data():
    api = Api(AIRTABLE_API_KEY)
    table = api.table(base_id, table_id)
    df_AT = pd.json_normalize(table.all())
    df_AT.columns = df_AT.columns.str.replace('fields.', '')
    df_AT = df_AT.drop(columns=['createdTime', 'DESCUENTO SOBRE ASKING PRICE.specialValue'])
    return df_AT

def update_data(df):
    url = f'https://api.airtable.com/v0/{base_id}/{table_id}'
    headers =  create_headers()
    
    df = df.astype(str)
    cols_to_convert_float = ['SUPERFICIE', 'ASKING PRICE']
    for col in cols_to_convert_float:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    cols_to_convert = ['id_numerico', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS']
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(pd.Int64Dtype())

    df_to_upload = df[['id', 'id_numerico', 'ASKING PRICE', 'SUPERFICIE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS']] 

    records = []
    for _, row in df_to_upload.iterrows():
        record = {"fields": {}}
        for col in df_to_upload.columns:
            if pd.notnull(row[col]) and col != "id":
                record["fields"][col] = row[col]
        record["id"] = row["id"]
        records.append(record)

    # Formato final deseado
    final_data = {"records": records}

    for record in final_data["records"]:
        fields_to_remove = [key for key, value in record["fields"].items() if value == "nan" or value == None]
        for field in fields_to_remove:
            del record["fields"][field]

    st.write(final_data)

    response = requests.patch(url, headers=headers, json=final_data)

    if response.status_code == 200:
        print("Record updated successfully!")
    else:
        print("Failed to update record.")

def create_data(df):

    try:

        df = df.astype(str)

        cols_to_convert_float = ['SUPERFICIE', 'ASKING PRICE']
        cols_to_convert_int = ['id_numerico', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS']

        # Convertir columnas a float si existen
        for col in cols_to_convert_float:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Convertir columnas a Int64 si existen
        for col in cols_to_convert_int:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(pd.Int64Dtype())

        records = df.to_dict(orient='records')
        final_data = {"records": [{"fields": record} for record in records]}

        for record in final_data["records"]:
            fields_to_remove = [key for key, value in record["fields"].items() if value == "nan" or value == None]
            for field in fields_to_remove:
                del record["fields"][field]

        print(final_data)

        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        response = requests.post(url, headers=create_headers(), json=final_data)

        if response.status_code == 200:
            print("Record create successfully!")
            st.write("Record create successfully!")
        else:
            # print("Failed to create record.", response.status_code)
            try:
                error_message = response.json()
                # print(f"Error message: {error_message}")
                st.write(f"Error message: {error_message}")
            except ValueError:
                # print("Failed to parse error message.")
                st.write("Failed to parse error message.")
    except: pass


#############
#    Main   #
#############

st.set_page_config(page_title="OXI Realty"
                   , layout="wide",
                   page_icon="oxi.png")
st.title("Actualización de perímetro")

st.sidebar.title("OXI REALTY")
st.sidebar.write("[https://oxirealty.com/](https://oxirealty.com/)")
st.sidebar.write("[OXI Operations AT](https://airtable.com/app3vwLcsaEjJGPl6/tblCzTZXgoRu9Dypt/viwZLRBG5OF3Jp9dW?blocks=hide)")

df_AT = get_data()
numero_activos = df_AT.id_numerico.max()
st.markdown(f"##### {len(df_AT)} activos totales")
st.markdown(f"##### {df_AT.id_numerico.max()}:    Max id")
st.write("Todos los activos:")
st.dataframe(df_AT)

st.markdown('##')

st.header("Nuevos activos:", divider= 'gray')
uploaded_files = st.file_uploader("",accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # df_subido = seleccionar_columnas(tipo_de_perimetro, uploaded_file)
        # # st.write(df_subido)
        df_perimetro = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
        st.markdown(f"##### {df_perimetro.shape[0]} activos en el perimetro subido")
        
        resultado = actualizar_perimetro(df_AT, df_perimetro)
        
        st.write("Nuevos activos:")
        numeros_crecientes = list(range(numero_activos+1, 1+numero_activos + len(resultado[4])))
        resultado[4]['id_numerico'] = numeros_crecientes
        st.write(resultado[4])

        st.write("Activos modificados:")
        st.write(resultado[6][['id', 'OXI_ID', 'CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE', 'id_numerico']])


col1, col2 = st.columns(2)
with col1:
    if st.button('Crear los activos', type="primary"):
        with st.spinner('Uploading...'):
            # Número de filas a imprimir en cada iteración
            filas_por_iteracion = 3
            indice_inicial = 0
            while indice_inicial < len(resultado[4]):
                grupo_filas = resultado[4].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                create_data(grupo_filas)
                indice_inicial += filas_por_iteracion

with col2:
    if st.button('Actualizar los activos', type="primary"):
        with st.spinner('Uploading...'):
            filas_por_iteracion = 3
            indice_inicial = 0
            while indice_inicial < len(resultado[4]):
                grupo_filas = resultado[6].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                update_data(grupo_filas)
                indice_inicial += filas_por_iteracion
                