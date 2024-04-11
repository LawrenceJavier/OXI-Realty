import pandas as pd
import streamlit as st
import openpyxl

#############
# Funciones #
#############

def get_df(file_buffer):
    df = pd.read_excel(file_buffer, engine='openpyxl')
    return df

def excel_preview(file_buffer):
    try:
        # Cargar el archivo Excel en un DataFrame de Pandas
        df = pd.read_excel(file_buffer, engine='openpyxl')
        
        # Mostrar una tabla con una vista previa de los datos
        st.write(df.head())
        
    except Exception as e:
        st.error("Ocurrió un error al cargar el archivo Excel: {}".format(e))

def join_excels(df_new, df_total):
    result = pd.concat([df_new, df_total], ignore_index=True)
    merged_df = result.drop_duplicates(subset='CODIGO INMUEBLE COMPLETO', keep='first')
    return merged_df


#############
#  Paginas  #
#############

def page_inicio():
    nombres = ["OXI_ID","CODIGO INMUEBLE COMPLETO","EMPRESA PROPIETARIA","TIPOLOGIA INMUEBLE","REFERENCIA CATASTRAL","CCAA","PROVINCIA","CIUDAD","DIRECCIÓN COMPLETA","CODIGO POSTAL","ASKING PRICE","NUMERO DORMITORIOS","NUMERO BAÑOS","SUPERFICIE","SITUACIÓN OCUPACIONAL","FIELD AGENT ASSIGNED","FASE JUDICIAL","CLIENTE" ,"TIPO DE OPERACIÓN","PUBLISHED","OFFER STATUS","IBI","GASTOS COMUNIDAD","RESERVA-ARRAS AGREEMENT","OFFER QUANTITY","OXI FEES","NET FEES OXI","FIELD AGENTE FEES","OXI FEES (VAT)","FIELD AGENT FESS (VAT)","FASE RESERVA","FASE PBC","NOTARY","COMENTARIOS","HONORARIOS","ACTIVO EN COLABORACIÓN","OCUPACIÓN","VULNERABILIDAD","COMENTARIO GENERAL"]
    df = pd.DataFrame(columns=nombres)

    st.title("Actualización de perímetro")

    uploaded_files = st.file_uploader("Elige archivos", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            df_subido = get_df(uploaded_file)
            st.write(f"    {uploaded_file.name}")
            st.write(df_subido.head())
            df = join_excels(df_subido, df)

    st.header('Crear nuevo perimetro')
    if st.button('Crear nuevo perimetro'):
        st.write("Nuevo perímetro:")
        st.write(df)

def page_funcion1():
    st.title("Página de Función 1")
    st.write("Esta es la página de la Función 1.")

def page_funcion2():
    st.title("Página de Función 2")
    st.write("Esta es la página de la Función 2.")

st.set_page_config(page_title="OXI Realty")

# Configura la barra lateral
st.sidebar.title('Navegación')
page = st.sidebar.selectbox('Seleccione una página',
                            ['Perímetro', 'Función 1', 'Función 2'])

# Mostrar la página seleccionada
if page == 'Perímetro':
    page_inicio()
elif page == 'Función 1':
    page_funcion1()
elif page == 'Función 2':
    page_funcion2()
