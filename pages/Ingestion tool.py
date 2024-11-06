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

def seleccionar_columnas(tipo_de_cliente, uploaded_file):

    if tipo_de_cliente == 'Coral Homes Wips & Suelos':
        df1 = pd.read_excel(uploaded_file,sheet_name=0, engine='openpyxl', header=0)
        df1 = df1.drop(["UR's Promo", "% Propiedad", f"% Ejecución", "Total Resi Units", "Posesión"], axis=1)
        df1.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'REFERENCIA CATASTRAL', 'CIUDAD', 'PROVINCIA', 'CCAA']
        df2 = pd.read_excel(uploaded_file,sheet_name=1, engine='openpyxl', header=0)
        df2 = df2.drop(["SECTOR", "Gestión UR", "Calificación", "Uso Principal", "% Particpación", "URs por Ámbito","Proindiviso", "Superficie Suelo Propiedad", "EDIFICABILIDAD TOTAL", "EDIFICABILIDAD RESID. LIBRE", "VIVIENDAS TOTALES PROPIEDAD", "VIVIENDAS VPP PROPIEDAD", "VIVIENDAS LIBRES PROPIEDAD"], axis=1)
        df2.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'REFERENCIA CATASTRAL', 'CIUDAD', 'PROVINCIA', 'CCAA', 'TIPOLOGIA INMUEBLE']
        df = pd.concat([df2, df1])
        df_subido = df.reset_index(drop=True)
        return df_subido
    
    elif tipo_de_cliente == 'Coral Homes':
        df = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
        df_subido = df.drop(['Promoción conjunta', 'Unidades Promoción conjunta','Promoción comercial', 'Unidades Promoción comercial', 'Superficie Solar'], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'DIRECCION COMPLETA', 'CIUDAD', 'PROVINCIA', 'CCAA', 'CODIGO POSTAL', 'REFERENCIA CATASTRAL', 'TIPOLOGIA INMUEBLE', 'SUPERFICIE', 'ASKING PRICE']
        return df_subido
    
    elif tipo_de_cliente == 'Anticipa & Aliseda':
        df = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
        df_subido = df.drop(['ID ATENEA', 'CODIGO SOCIEDAD'], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'EMPRESA PROPIETARIA', 'TIPOLOGIA INMUEBLE', 'REFERENCIA CATASTRAL', 'CCAA', 'PROVINCIA', 'CIUDAD', 'DIRECCION COMPLETA', 'CODIGO POSTAL', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
        return df_subido
    
    elif tipo_de_cliente == 'Producto Libre OXI':
        df = pd.read_excel(uploaded_file)
        df_subido = df.drop(["Portfolio", "Construcción", "Año Construcción", "Escalera", "Piso", "FR",  "Coef. Particip", "Expediente Judicial", "Situación"], axis=1)
        df_subido.columns= ['CODIGO INMUEBLE COMPLETO', 'TIPOLOGIA INMUEBLE', 'CCAA', 'PROVINCIA', 'CIUDAD',  'DIRECCION COMPLETA', 'CODIGO POSTAL', 'REFERENCIA CATASTRAL', 'SUPERFICIE', 'ASKING PRICE']
        return df_subido

def actualizar_perimetro(df1, df2, cliente,operacion):
    df1 = df1.astype(str)
    # df1 = df1[(df1['ASSET STATUS'] != 'EXCLUDED')]
    df1_tmp = df1[(df1['CLIENTE'] == cliente)]
    df1 = df1_tmp[(df1_tmp['TIPO DE OPERACIÓN'] == operacion)]
    st.write(f"###### Activos {cliente}: {len(df1_tmp)} --> Activos {cliente} {operacion}: {len(df1)}")
    df2 = df2.astype(str)
    columnas_float = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_float:
        if columna in df1:
            df1[columna] = pd.to_numeric(df1[columna], errors='coerce').astype(float)
        if columna in df2:
            df2[columna] = pd.to_numeric(df2[columna], errors='coerce').astype(float)

    # Nuevos activos
    nuevos_activos= df2[~df2['CODIGO INMUEBLE COMPLETO'].isin(df1['CODIGO INMUEBLE COMPLETO'])]
    # Reemplazar NaN por 0 en las columnas especificadas
    columnas_a_reemplazar = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_a_reemplazar:
        nuevos_activos[columna] = nuevos_activos[columna].fillna(0)
    nuevos_activos["ASSET STATUS"] = "AVAILABLE"

    # Activos excluidos
    activos_excluidos = df1[(~df1['CODIGO INMUEBLE COMPLETO'].isin(df2['CODIGO INMUEBLE COMPLETO']))]
    activos_excluidos = activos_excluidos[(activos_excluidos['ASSET STATUS'] == 'AVAILABLE')]
    activos_excluidos["ASSET STATUS"] = "EXCLUDED"
    
    # Activos modificados
    filas_comunes = df1.merge(df2, on='CODIGO INMUEBLE COMPLETO', suffixes=('_df1', '_df2'))

    filas_modificadas = filas_comunes[
        (filas_comunes['ASKING PRICE_df1'] != filas_comunes['ASKING PRICE_df2']) |
        (filas_comunes['NUMERO DORMITORIOS_df1'] != filas_comunes['NUMERO DORMITORIOS_df2']) |
        (filas_comunes['NUMERO BAÑOS_df1'] != filas_comunes['NUMERO BAÑOS_df2']) |
        (filas_comunes['SUPERFICIE_df1'] != filas_comunes['SUPERFICIE_df2'])
    ][['id', 'id_numerico', 'CODIGO INMUEBLE COMPLETO', 'ASKING PRICE_df2', 'NUMERO DORMITORIOS_df2', 'NUMERO BAÑOS_df2', 'SUPERFICIE_df2', 'ASSET STATUS']]
    print(list(filas_modificadas.columns))
    filas_modificadas.columns = ['id', 'id_numerico', 'CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE', 'ASSET STATUS']
    columnas_a_reemplazar = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_a_reemplazar:
        filas_modificadas[columna] = filas_modificadas[columna].fillna(0)
    filas_modificadas = filas_modificadas[(filas_modificadas['ASSET STATUS'] != 'EXCLUDED')]

    # Activos no modificados
    filas_no_modificadas = filas_comunes[
        (filas_comunes['ASKING PRICE_df1'] == filas_comunes['ASKING PRICE_df2']) &
        (filas_comunes['NUMERO DORMITORIOS_df1'] == filas_comunes['NUMERO DORMITORIOS_df2']) &
        (filas_comunes['NUMERO BAÑOS_df1'] == filas_comunes['NUMERO BAÑOS_df2']) &
        (filas_comunes['SUPERFICIE_df1'] == filas_comunes['SUPERFICIE_df2'])
    ][['CODIGO INMUEBLE COMPLETO', 'ASKING PRICE_df2', 'NUMERO DORMITORIOS_df2', 'NUMERO BAÑOS_df2', 'SUPERFICIE_df2']]
    filas_no_modificadas.columns = ['CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']

    # filas_no_modificadas = filas_no_modificadas[(filas_no_modificadas['ASSET STATUS'] != 'EXCLUDED')]



    return nuevos_activos, activos_excluidos, filas_modificadas, filas_no_modificadas

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

    # st.write(final_data)

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

        # print(final_data)

        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        response = requests.post(url, headers=create_headers(), json=final_data)

        if response.status_code == 200:
            print("Record create successfully!")
            # st.write("Record create successfully!")
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

st.set_page_config(page_title="OXI Realty Tech Hub"
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

col1, col2 = st.columns(2)
with col1:
    tipo_de_cliente = st.selectbox(
            'Selecciona el tipo de perímetro:',
            ['Seleccionar tipo de perímetro', 'Coral Homes Wips & Suelos', 'Coral Homes', 'ANTICIPA', 'SINTRA', 'Producto Libre OXI']
        )
with col2:
    tipo_de_operacion = st.selectbox(
            'Selecciona el tipo de operacion:',
            ['Seleccionar tipo de operacion', 'REO SIN POSESION', 'REO', 'LIBRE', 'CONCURSO DE ACREEDORES', 'LIBRE PROVINIENTE DE UN PROCESO JUDICIAL', 'VENTA DE CREDITO', 'CDR', 'POA']
        )

if tipo_de_cliente != 'Seleccionar tipo de perímetro':

    if tipo_de_operacion != 'Seleccionar tipo de operacion':

        uploaded_files = st.file_uploader("",accept_multiple_files=True)

        if uploaded_files:
            for uploaded_file in uploaded_files:
                df_perimetro = pd.read_excel(uploaded_file, engine='openpyxl', header=1)
                st.markdown(f"##### {df_perimetro.shape[0]} activos en el perimetro subido")
                
                resultado = actualizar_perimetro(df_AT, df_perimetro, tipo_de_cliente, tipo_de_operacion)
                
                st.markdown(f"Activos nuevos: {resultado[0]['CODIGO INMUEBLE COMPLETO'].nunique()}")
                numeros_crecientes = list(range(numero_activos+1, 1+numero_activos + len(resultado[0])))
                resultado[0]['id_numerico'] = numeros_crecientes
                st.write(resultado[0])

                st.write(f"Activos modificados: {resultado[2]['CODIGO INMUEBLE COMPLETO'].nunique()}")
                st.write(resultado[2])
        
                st.write(f"Activos no modificados: {resultado[3]['CODIGO INMUEBLE COMPLETO'].nunique()}")

                st.markdown(f"Activos excluidos: {resultado[1]['CODIGO INMUEBLE COMPLETO'].nunique()}")
                st.write(resultado[1])

col1, col2 = st.columns(2)
with col1:
    if st.button('Crear los activos', type="primary"):
        with st.spinner('Creando...'):
            # Número de filas a imprimir en cada iteración
            filas_por_iteracion = 9
            indice_inicial = 0
            while indice_inicial < len(resultado[0]):

                if len(resultado[0])-indice_inicial < filas_por_iteracion:
                    filas_por_iteracion = len(resultado[0])-indice_inicial
                    print("ultima")

                grupo_filas = resultado[0].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                create_data(grupo_filas)
                indice_inicial = indice_inicial + filas_por_iteracion+1

    st.write("Activos creados correctamente.")

with col2:
    if st.button('Actualizar los activos', type="primary"):
        with st.spinner('Uploading...'):
            filas_por_iteracion = 10
            indice_inicial = 0
            while indice_inicial < len(resultado[2]):
                grupo_filas = resultado[2].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                update_data(grupo_filas)
                indice_inicial += filas_por_iteracion
    st.write("Activos actualizados correctamente.")