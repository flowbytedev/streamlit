import streamlit as st
import pyodbc
import pandas as pd
import urllib
import sqlalchemy
from flowbyte.sql import MSSQL
import re


# Function to establish connection to the database
def get_sql(prefix):
    """
    Create SQL Object
    """
    # get GMRLDW_SERVER from environment
    server = st.secrets["connections"][f"{prefix}"]["server"]
    database = st.secrets["connections"][f"{prefix}"]["database"]
    user = st.secrets["connections"][f"{prefix}"]["username"]
    password = st.secrets["connections"][f"{prefix}"]["password"]

    sql = MSSQL(
        connection_type="sqlalchemy",
        host = server,
        database = database,
        username = user,
        password = password,
        driver = "ODBC Driver 17 for SQL Server"
    )

    sql.connect()


    return sql

# Function to fetch schemas from the selected database
def get_schemas(server_choice, database_choice):
    schema_query = f"SELECT DISTINCT [schema] FROM [data].[table] WHERE [host]='{server_choice}' AND [database_name] = '{database_choice}' " 

    sql_setup.connect()
    
    df = sql_setup.get_data(query=schema_query, chunksize=100)

    if df.empty:
        return []
    else:
        # st.write(df)
        return df['schema'].tolist()

sql_setup=get_sql('FLOWBYTE')


def get_tables(server_choice, database_choice, schema_choice):

    tables_query = f"""
                        SELECT [name]
                        FROM [data].[table]
                        WHERE [schema] = '{schema_choice}'
                        AND [database_name] = '{database_choice}'
                        AND [host]='{server_choice}'  
                    """ 
    
    sql_setup.connect()

    df = sql_setup.get_data(query=tables_query, chunksize=100)
    
    return df['name'].tolist()


data_query = "SELECT TOP 1000 * FROM "

# Set up the Streamlit app
st.set_page_config(
    page_title="Database Explorer",
    page_icon="📊",  
    layout="wide",
    initial_sidebar_state="expanded",
)



st.sidebar.title("Database Explorer")
st.sidebar.write("This tool allows you to explore the databases and tables available in the GMRL environment.")

# Select Credentials
query= "SELECT * FROM [data].[database_credentials] " 
CREDENTIALS= sql_setup.get_data(query=query,chunksize=100)

 
# Select Databases and Servers
server_query = "SELECT [host], [type] FROM [data].[database] "

SERVERS = sql_setup.get_data(query=server_query, chunksize=100)
SERVER_LIST = set(SERVERS['host'])


server_choice = st.sidebar.selectbox("Select a Server:", SERVER_LIST)
SERVER_TYPE = SERVERS[SERVERS['host'] == server_choice]['type'].iloc[0]


if server_choice == None:
    st.stop()

if SERVER_TYPE  != 'mssql':
    st.warning(f"This tool only supports **MSSQL** databases at the moment. You selected a **{SERVER_TYPE}** database.")
    st.stop()


database_query= f"SELECT [name],[host] FROM [data].[database] WHERE [host]='{server_choice}'"

database_df = sql_setup.get_data(query=database_query,chunksize=100)

DATABASE_LIST = database_df['name'].tolist()
SERVER_LIST = database_df['host'].tolist()

# Select Database
database_choice = st.sidebar.selectbox("Select a Database:", DATABASE_LIST)

if database_choice == None or database_choice == "":
    st.stop()


credentials_query= f"SELECT * FROM [data].[database_credentials] WHERE [host] = '{server_choice}' AND [database_name] = '{database_choice}' " 

credentials_df = sql_setup.get_data(query=credentials_query, chunksize=100)

if credentials_df.empty:
    st.warning(f"No credentials found for the selected database: {database_choice}.")
    st.stop()

USERNAME = credentials_df["username"].iloc[0]
PASSWORD = credentials_df["password"].iloc[0]


# Select Schema
schemas = get_schemas(server_choice=server_choice, database_choice=database_choice)
schema_choice = st.sidebar.selectbox("Select a Schema:", schemas)

if schema_choice == None or schema_choice == "":
    st.warning(f"No schema was found for the selected database: {database_choice}.")
    st.stop()


tables = get_tables(server_choice=server_choice, database_choice=database_choice, schema_choice=schema_choice)
table_choice = st.sidebar.selectbox("Select a Table:", tables)


if table_choice == None or table_choice == "":
    st.stop()


sql_data = get_sql(f'{database_choice.upper()}')

# Fetch data
data_query =  data_query + f"[{schema_choice}].[{table_choice}]"

data_df = sql_data.get_data(data_query, chunksize=1000)



with st.sidebar.expander("🔍 Advanced Filtering", expanded=True):
    # User inputs query
    user_filter = st.text_area(
        "Enter your filter query:", 
        value="", 
        placeholder="e.g., brand = 'MARS' and `variant_code` = 'V002'"
    )


    if user_filter.strip():
        data_query = data_query + " WHERE " + user_filter
        data_df = sql_data.get_data(data_query, chunksize=1000)





st.dataframe(data_df, use_container_width=True, height=850, hide_index=True, key="data_df", row_height=30)