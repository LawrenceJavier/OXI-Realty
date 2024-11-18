import os
from pyairtable import Api
import pandas as pd
import streamlit as st
import re
import json
import requests
import openpyxl
from pyproj import Proj, transform
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

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
    columnas_a_reemplazar = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_a_reemplazar:
        nuevos_activos[columna] = nuevos_activos[columna].fillna(0)
    nuevos_activos["ASSET STATUS"] = "AVAILABLE"

    # Activos excluidos
    activos_excluidos = df1[(~df1['CODIGO INMUEBLE COMPLETO'].isin(df2['CODIGO INMUEBLE COMPLETO']))]
    activos_excluidos = activos_excluidos[(activos_excluidos['ASSET STATUS'] == 'AVAILABLE')]
    activos_excluidos["ASSET STATUS"] = "EXCLUDED"
    
    # Activos modificados
    columnas_a_reemplazar = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    for columna in columnas_a_reemplazar:
        if columna in df2.columns:
            df2[columna] = df2[columna].fillna(0)

    filas_comunes = df1.merge(df2, on='CODIGO INMUEBLE COMPLETO', suffixes=('_df1', '_df2'))

    filas_modificadas = filas_comunes[
        (filas_comunes['ASKING PRICE_df1'] != filas_comunes['ASKING PRICE_df2']) |
        (filas_comunes['NUMERO DORMITORIOS_df1'] != filas_comunes['NUMERO DORMITORIOS_df2']) |
        (filas_comunes['NUMERO BAÑOS_df1'] != filas_comunes['NUMERO BAÑOS_df2']) |
        (filas_comunes['SUPERFICIE_df1'] != filas_comunes['SUPERFICIE_df2'])
    ][['id', 'id_numerico', 'CODIGO INMUEBLE COMPLETO', 'ASKING PRICE_df2', 'NUMERO DORMITORIOS_df2', 'NUMERO BAÑOS_df2', 'SUPERFICIE_df2', 'ASSET STATUS', 'REFERENCIA CATASTRAL_df2']]
    filas_modificadas.columns = ['id', 'id_numerico', 'CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE', 'ASSET STATUS', 'REFERENCIA CATASTRAL']
    columnas_a_reemplazar = ['ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']
    # for columna in columnas_a_reemplazar:
    #     filas_modificadas[columna] = filas_modificadas[columna].fillna(0)
    filas_modificadas = filas_modificadas[(filas_modificadas['ASSET STATUS'] != 'EXCLUDED')]

    # Activos no modificados
    filas_no_modificadas = filas_comunes[
        (filas_comunes['ASKING PRICE_df1'] == filas_comunes['ASKING PRICE_df2']) &
        (filas_comunes['NUMERO DORMITORIOS_df1'] == filas_comunes['NUMERO DORMITORIOS_df2']) &
        (filas_comunes['NUMERO BAÑOS_df1'] == filas_comunes['NUMERO BAÑOS_df2']) &
        (filas_comunes['SUPERFICIE_df1'] == filas_comunes['SUPERFICIE_df2'])
    ][['CODIGO INMUEBLE COMPLETO', 'ASKING PRICE_df2', 'NUMERO DORMITORIOS_df2', 'NUMERO BAÑOS_df2', 'SUPERFICIE_df2']]
    filas_no_modificadas.columns = ['CODIGO INMUEBLE COMPLETO', 'ASKING PRICE', 'NUMERO DORMITORIOS', 'NUMERO BAÑOS', 'SUPERFICIE']

    return nuevos_activos, activos_excluidos, filas_modificadas, filas_no_modificadas

@st.cache_data
def get_data():
    api = Api(AIRTABLE_API_KEY)
    table = api.table(base_id, table_id)
    df_AT = pd.json_normalize(table.all())
    df_AT.columns = df_AT.columns.str.replace('fields.', '')
    df_AT = df_AT.drop(columns=['createdTime', 'DESCUENTO SOBRE ASKING PRICE.specialValue'])
    return df_AT

def exclude_data(df):
    url = f'https://api.airtable.com/v0/{base_id}/{table_id}'
    headers =  create_headers()
    
    df = df.astype(str)
    df_to_upload = df[['id', 'ASSET STATUS']]

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

    response = requests.patch(url, headers=headers, json=final_data)

    if response.status_code == 200:
        print("Record updated successfully!")
    else:
        print("Failed to update record.")
        
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
            else:
                print("fallo", col)
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

def get_informacion_catastro_api(df):

    for index, row in df.iterrows():
        try:
            catastro = row["REFERENCIA CATASTRAL"]
            r = get_informacion_catastro(catastro)
            try:
                df.at[index, "CODIGO POSTAL texto"] = r["cp"]
                df.at[index, "provincia texto"] = r["prov"]
                df.at[index, "ciudad text"] = r["mun"]
                df.at[index, "DIRECCION COMPLETA texto"] = f'{r["calle"]}, {r["num"]}'
                df.at[index, "SUPERFICIE texto"] = r["sup_const"]
                df.at[index, "Cartografia"] = r["cartografia"]
                ubicacion = []
                if r["usos_list"]:
                    for uso in r["usos_list"]:
                        try:
                            ubicacion.append(uso["ubicacion"])
                        except:
                            pass
                df.at[index, "Ubicacion"] = str(ubicacion)
                df.at[index, "Extraccion direciones"] = "DONE"
            except:
                df.at[index, "Extraccion direciones"] = "ERROR"
                print("Error en la extracción de la dirección", catastro, df.at[index, "id"], df.at[index, "Extraccion direciones"])
        except Exception as e:
            print("Falla la conexión", e)
    

# FUNCIONES DEL CATASTRO:

def crear_mapa_cartografico(prov, mun, catastro):
    return f"https://www1.sedecatastro.gob.es/Cartografia/mapa.aspx?del={prov}&mun={mun}&refcat={catastro}&final=&ZV=NO&anyoZV="

def encontrar_valor(valor, listas):
    return next((lista for lista in listas if valor in lista), None)

def get_coordenadas(x, y, uso):
    try:
        origen = Proj(init=uso)
        destino = Proj(init='EPSG:4326')
        longitud, latitud = transform(origen, destino, x, y)
        return [latitud, longitud]
    except:
        return [0,0]

def catastros_etl(catastro, return_list):

    url = f"https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/Consulta_DNPRC?RefCat={catastro}"
    response = requests.get(url, verify=False, timeout=10)
    if response.status_code == 200:
        response_text_latin1 = response.content.decode('utf-8')
        data = json.loads(response_text_latin1)
        data_jason = json.dumps(data, indent=4)
        
        if 'cuerr' in data["consulta_dnprcResult"]["control"]:
            print("error")
        else:
            # print("Existe:", catastro)

            cantidad = data["consulta_dnprcResult"]["control"]["cudnp"]
            # print(f"        ", cantidad)
            if int(cantidad)==1:

                # print(data_jason)

                clase = data["consulta_dnprcResult"]["bico"]["bi"]["idbi"]["cn"]
                ref = ''.join(list(data["consulta_dnprcResult"]["bico"]["bi"]["idbi"]["rc"].values()))
                prov = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["np"]
                cod_prov = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["loine"]["cp"]
                mun = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["nm"]
                cod_mun = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["loine"]["cm"]
                cod_cmc = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["cmc"]
                try:    calle = f'{data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["locs"]["lous"]["lourb"]["dir"]["tv"]} {data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["locs"]["lous"]["lourb"]["dir"]["nv"]}'
                except: calle = data["consulta_dnprcResult"]["bico"]["bi"]["ldt"]
                try:    num = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["locs"]["lous"]["lourb"]["dir"]["pnp"]
                except: num = 0
                try:    cp = data["consulta_dnprcResult"]["bico"]["bi"]["dt"]["locs"]["lous"]["lourb"]["dp"]
                except: cp = 0
                uso_ppal = data["consulta_dnprcResult"]["bico"]["bi"]["debi"]["luso"]

                try:    sup_const = data["consulta_dnprcResult"]["bico"]["bi"]["debi"]["sfc"]
                except: sup_const = 0
                try:    fecha_construccion = data["consulta_dnprcResult"]["bico"]["bi"]["debi"]["ant"]
                except: fecha_construccion = 0

                try:
                    usos_list = []
                    usos = data["consulta_dnprcResult"]["bico"]["lcons"]
                    for u in usos:
                        uso_dict = {}
                        uso_dict["uso"] = u["lcd"]
                        try:    uso_dict["ubicacion"] = u["dt"]["lourb"]["loint"]
                        except: pass
                        try:    uso_dict["metros"] = u["dfcons"]["stl"]
                        except: pass
                        usos_list.append(uso_dict)
                except: pass

                try:
                    cultivos_list = []
                    cultivos = data["consulta_dnprcResult"]["bico"]["lspr"]
                    for c in cultivos:
                        cultivo_dict = {}
                        cultivo_dict["cultivo"] = f'{c["dspr"]["ccc"]} {c["dspr"]["dcc"]}'
                        try:    cultivo_dict["intensidad"] = c["dspr"]["ip"]
                        except: pass
                        try:    cultivo_dict["metros"] = c["dspr"]["ssp"]
                        except: pass
                        cultivos_list.append(cultivo_dict)
                except: pass

                cat = [clase, ref, prov, cod_prov, mun, cod_mun, cod_cmc, calle, num, cp, uso_ppal, sup_const, fecha_construccion, usos_list, cultivos_list]

                return_list.append(cat)
            else:
                for e in data["consulta_dnprcResult"]["lrcdnp"]["rcdnp"]:
                    referencia_temporal = ''.join(list(e["rc"].values()))
                    catastros_etl(referencia_temporal, return_list)

    else:
        print("Error al realizar la solicitud. Código de estado:", response.status_code, response)
    
    # return_list = list(map(list, zip(*return_list)))
    return return_list

def get_informacion_catastro(catastro):

    matches = catastros_etl(catastro, [])
    for lista in matches:
        if lista[1].strip() == catastro.strip():
            lista.append(crear_mapa_cartografico(lista[3], lista[6], catastro))
            keys=["clase", "ref", "prov", "cod_prov", "mun", "cod_mun", "cod_cmc", "calle", "num", "cp", "uso_ppal", "sup_const", "fecha_construccion", "usos_list", "cultivos_list", "cartografia"]
            diccionario = dict(zip(keys, lista))
            return diccionario
    
    return 000

def crear_direcciones(df_direcciones):
    for index, row in df_direcciones.iterrows():
        try:
            catastro = row["REFERENCIA CATASTRAL"]
            r = get_informacion_catastro(catastro)
            df_direcciones.at[index, "provincia texto"] = r["prov"]
            df_direcciones.at[index, "ciudad text"] = r["mun"]
            df_direcciones.at[index, "DIRECCION COMPLETA texto"] = f'{r["calle"]}, {r["num"]}'
            df_direcciones.at[index, "CODIGO POSTAL texto"] = r["cp"]
            df_direcciones.at[index, "SUPERFICIE texto"] = r["sup_const"]
            df_direcciones.at[index, "Extraccion direciones"] = "DONE"
            df_direcciones.at[index, "Cartografia"] = r["cartografia"]
            ubicacion = []
            if r["usos_list"]:
                for uso in r["usos_list"]:
                    try:
                        ubicacion.append(uso["ubicacion"])
                    except:
                        pass
            df_direcciones.at[index, "Ubicacion"] = str(ubicacion)
            
        except Exception as e:
            print(f"Falla-{row['REFERENCIA CATASTRAL']}: {e}")
    return df_direcciones

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
            ['Seleccionar tipo de perímetro', 'Coral Homes Wips & Suelos', 'Coral Homes', 'ANTICIPA', 'ALISEDA', 'SINTRA', 'Producto Libre OXI']
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
                numero_activos = int(numero_activos)
                numeros_crecientes = list(range(numero_activos+1, 1+numero_activos + len(resultado[0])))
                resultado[0]['id_numerico'] = numeros_crecientes

                # get_informacion_catastro_api(resultado[0])

                st.write(resultado[0])

                st.write(f"Activos modificados: {resultado[2]['CODIGO INMUEBLE COMPLETO'].nunique()}")
                st.write(resultado[2])
        
                st.write(f"Activos no modificados: {resultado[3]['CODIGO INMUEBLE COMPLETO'].nunique()}")

                st.markdown(f"Activos excluidos: {resultado[1]['CODIGO INMUEBLE COMPLETO'].nunique()}")
                st.write(resultado[1])



# get_informacion_catastro(resultado[0])

st.markdown('#')

col1, col2, col3 = st.columns(3)
with col1:
    if st.button('Crear Activos', type="primary"):
        with st.spinner('Creando...'):
            filas_por_iteracion = 9
            indice_inicial = 0
            while indice_inicial < len(resultado[0]):
                if len(resultado[0])-indice_inicial < filas_por_iteracion:
                    filas_por_iteracion = len(resultado[0])-indice_inicial
                    print("ultima")
                grupo_filas = resultado[0].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                create_data(grupo_filas)
                indice_inicial = indice_inicial + filas_por_iteracion
    st.write("Activos creados correctamente.")

with col2:
    if st.button('Actualizar activos', type="primary"):
        with st.spinner('Actualizando...'):
            filas_por_iteracion = 9
            indice_inicial = 0
            while indice_inicial < len(resultado[2]):
                if len(resultado[2])-indice_inicial < filas_por_iteracion:
                    filas_por_iteracion = len(resultado[2])-indice_inicial
                    print("ultima")
                grupo_filas = resultado[2].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                update_data(grupo_filas)
                indice_inicial = indice_inicial + filas_por_iteracion
    st.write("Activos actualizados correctamente.")

with col3:
    if st.button('Excluir activos', type="primary"):
        with st.spinner('Excluyendo...'):
            filas_por_iteracion = 9
            indice_inicial = 0
            while indice_inicial < len(resultado[1]):
                if len(resultado[1])-indice_inicial < filas_por_iteracion:
                    filas_por_iteracion = len(resultado[1])-indice_inicial
                    print("ultima")
                grupo_filas = resultado[1].iloc[indice_inicial:indice_inicial + filas_por_iteracion]
                exclude_data(grupo_filas)
                indice_inicial = indice_inicial + filas_por_iteracion
    st.write("Activos actualizados correctamente.")