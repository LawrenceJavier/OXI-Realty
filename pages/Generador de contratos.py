import requests
import pandas as pd
import streamlit as st
from pyairtable import Api
from fpdf import FPDF

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

    pdf.output('/home/lawrence/Escritorio/OXI-Realty/contract.pdf')


#############
#    Main   #
#############

st.set_page_config(page_title="OXI Realty", layout="wide")

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



if st.button("Generate Contract PDF"):
    input_data = {column: st.session_state[column] for column in selected_data.columns}
    generate_contract(input_data)
    st.success("Contract PDF generated successfully!")