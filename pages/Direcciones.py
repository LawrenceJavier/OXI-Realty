import requests
import json
import streamlit as st
from pyairtable import Api
import pandas as pd
from pyproj import Proj, transform
import warnings
import time
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


base_id = st.secrets["base_id"]
table_id = st.secrets["table_id"]
AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]


st.set_page_config(page_title="OXI Realty Tech Hub"
                   , layout="wide",
                   page_icon="oxi.png")
st.title("Extracción de direcciones")

def create_headers():
    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }
    return headers

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

    cols_to_convert_float = ['SUPERFICIE texto']
    for col in cols_to_convert_float:
        if col in list(df.columns):
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.drop(columns=['OXI_ID'])
    df_to_upload = df

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
        fields_to_replace = [key for key, value in record["fields"].items() if value == "nan" or value == None]
        for field in fields_to_replace:
            record["fields"][field] = ""

    response = requests.patch(url, headers=headers, json=final_data)

    if response.status_code == 200:
        print("Record updated successfully!")
    else:
        print("Failed to update record.", response, response.text)

def update_error_data(df):
    url = f'https://api.airtable.com/v0/{base_id}/{table_id}'
    headers =  create_headers()
    
    df = df.astype(str)

    try:
        df = df.drop(columns=['OXI_ID'])
    except:
        pass

    df_to_upload = df

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
        fields_to_replace = [key for key, value in record["fields"].items() if value == "nan" or value is None]
        for field in fields_to_replace:
            record["fields"][field] = ""

    response = requests.patch(url, headers=headers, json=final_data)

    if response.status_code == 200:
        print("Record updated successfully!")
    else:
        print("Failed to update record.", response, response.text)



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





df_AT = get_data()

df_AT = df_AT[df_AT["Extraccion direciones"] != "DONE"]
df_AT = df_AT[df_AT["Extraccion direciones"] != "ERROR"]
df_AT = df_AT[df_AT["ASSET STATUS"] != "EXCLUDED"]

st.write(df_AT.shape) 

df_direcciones = df_AT[["id", "OXI_ID", "REFERENCIA CATASTRAL"]]

df_direcciones_mal = df_direcciones[df_direcciones["REFERENCIA CATASTRAL"].str.len() != 20]
                       
df_direcciones = df_direcciones[df_direcciones["REFERENCIA CATASTRAL"].str.len() == 20]

df_direcciones = df_direcciones.head(367)
df_direcciones_mal = df_direcciones_mal.head(100)
st.write(df_direcciones_mal.shape) 
st.write(df_direcciones)

indice_inicial = 0
filas_por_iteracion = 367


while indice_inicial < len(df_direcciones):
    df_error_catastro = pd.DataFrame()
    id = []
    direccion = []

    sub_df = df_direcciones.iloc[indice_inicial:indice_inicial + filas_por_iteracion]
    

    for index, row in sub_df.iterrows():
        try:
            catastro = row["REFERENCIA CATASTRAL"]
            r = get_informacion_catastro(catastro)
            try:
                sub_df.at[index, "CODIGO POSTAL texto"] = r["cp"]
                sub_df.at[index, "provincia texto"] = r["prov"]
                sub_df.at[index, "ciudad text"] = r["mun"]
                sub_df.at[index, "DIRECCION COMPLETA texto"] = f'{r["calle"]}, {r["num"]}'
                sub_df.at[index, "SUPERFICIE texto"] = r["sup_const"]
                sub_df.at[index, "Cartografia"] = r["cartografia"]
                ubicacion = []
                if r["usos_list"]:
                    for uso in r["usos_list"]:
                        try:
                            ubicacion.append(uso["ubicacion"])
                        except:
                            pass
                sub_df.at[index, "Ubicacion"] = str(ubicacion)
                sub_df.at[index, "Extraccion direciones"] = "DONE"
            except:
                id.append(row["id"])
                direccion.append("ERROR")
                sub_df.at[index, "Extraccion direciones"] = "ERROR"
                print("Error en la extracción de la dirección", catastro, sub_df.at[index, "id"], sub_df.at[index, "Extraccion direciones"])

        except Exception as e:
            print("Falla la conexión", e)

    indice_inicial += filas_por_iteracion

    df_error_catastro["id"] = id
    df_error_catastro["Extraccion direciones"] = direccion

    st.write(sub_df)
    st.write(df_error_catastro)

    with st.spinner('Actualizando...'):
        filas_por_iteracion = 9
        indice_inicial = 0
        while indice_inicial < len(sub_df):
            print(indice_inicial, len(sub_df))
            if len(sub_df) - indice_inicial < filas_por_iteracion:
                filas_por_iteracion = len(sub_df) - indice_inicial
            grupo_filas = sub_df.iloc[indice_inicial:indice_inicial + filas_por_iteracion]
            update_data(grupo_filas)
            indice_inicial = indice_inicial + filas_por_iteracion