import requests
import pandas as pd
import streamlit as st
from pyairtable import Api
from fpdf import FPDF
import os

#############
#  Secrets  #
#############

base_id = st.secrets["base_id"]
table_id = st.secrets["table_id"]
AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]


#############
#    Class  #
#############

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'OXI Realty Contract', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(10)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

def generate_contract(data):
        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title("Contract Details")
        for key, value in data.items():
            pdf.chapter_body(f"{key}: {value}")
        return pdf.output(dest='S').encode('latin1')

#############
#    Main   #
#############

st.set_page_config(page_title="OXI Realty Tech Hub"
                   , layout="wide",
                   page_icon="oxi.png")

st.title("Generador de contratos")

st.sidebar.title("OXI REALTY")
st.sidebar.write("[https://oxirealty.com/](https://oxirealty.com/)")
st.sidebar.write("[OXI Operations AT](https://airtable.com/app3vwLcsaEjJGPl6/tblCzTZXgoRu9Dypt/viwZLRBG5OF3Jp9dW?blocks=hide)")


@st.cache_data
def get_data():
    api = Api(AIRTABLE_API_KEY)
    table = api.table(base_id, table_id)
    df_AT = pd.json_normalize(table.all())
    df_AT.columns = df_AT.columns.str.replace('fields.', '')
    df_AT = df_AT.drop(columns=['createdTime', 'DESCUENTO SOBRE ASKING PRICE.specialValue'])
    return df_AT


documents_dir = "./documents"
contract_types = [f for f in os.listdir(documents_dir) if os.path.isfile(os.path.join(documents_dir, f))]

col1, col2 = st.columns(2)
with col1:
    contract_type = st.selectbox("Select Contract Type", contract_types)
with col2:
    df_AT = get_data()
    oxi_id = st.selectbox("Select OXI ID", df_AT['OXI_ID'].unique())
    selected_data = df_AT[df_AT['OXI_ID'] == oxi_id]



st.write("Selected OXI ID Data:")



with st.container(border=True):
    st.write("Please fill in the following fields:")
    # Create input fields for each column in the selected data with 3 columns per row
    columns_per_row = 3
    columns = st.columns(columns_per_row)
    for idx, column in enumerate(selected_data.columns):
        value = selected_data[column].values[0] if not selected_data[column].isnull().values[0] else ""
        with columns[idx % columns_per_row]:
            st.text_input(label=column, value=value, key=column)


st.download_button(
    label="Generate and Download Contract PDF",
    data=generate_contract({column: st.session_state[column] for column in selected_data.columns}),
    file_name='contract.pdf',
    mime='application/pdf'
)