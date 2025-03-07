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

sql_setup=get_sql('FLOWBYTE')

# Define databases with corresponding environment variables
# FLOWBYTE= {
#         "server": os.getenv('FLOWBYTE_SERVER'),
#         "user": os.getenv('FLOWBYTE_USER'),
#         "password": os.getenv('FLOWBYTE_PASSWORD'),
#         "database": os.getenv('FLOWBYTE_DATABASE')
#     }

# sql_setup= MSSQL(
#     host=FLOWBYTE['server'],
#     username=FLOWBYTE['user'],
#     password=FLOWBYTE['password'] ,
#     database=FLOWBYTE['database'],
#     connection_type="sqlalchemy" ,
#     driver="ODBC Driver 17 for SQL Server"
# )

#sql_setup.connect()

# Streamlit UI
st.set_page_config(
    page_title="GMRL Database Explorer",
    page_icon="📊",  
)
st.sidebar.image("logo.png", width=100)
st.sidebar.title("GMRL Database Explorer")
st.sidebar.write("This tool allows you to explore the databases and tables available in the GMRL environment.")

# Select Credentials
query= "SELECT * FROM [data].[database_credentials] " 
CREDENTIALS= sql_setup.get_data(query=query,chunksize=100)
st.write(query)
st.write(CREDENTIALS)
 
# Select Databases and Servers
query= "SELECT [name],[host] FROM [data].[database] "
st.write(query)
DATABASES= sql_setup.get_data(query=query,chunksize=100)
SERVER_LIST= set(DATABASES['host'])
st.write(DATABASES)
st.write(SERVER_LIST)
server_choice = st.sidebar.selectbox("Select a Server:", SERVER_LIST)
st.write(server_choice)

#sql_setup.connect()

# Function to establish connection to the database
def connect(server, database, user, password, connection_type="pyodbc"):
    if connection_type == "pyodbc":
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};DATABASE={database};"
            f"UID={user};PWD={password};CHARSET=UTF8"
        )
    elif connection_type == "sqlalchemy":
        connect_string = urllib.parse.quote_plus(
            f"DRIVER=ODBC Driver 17 for SQL Server;"
            f"SERVER={server};DATABASE={database};"
            f"UID={user};PWD={password};CHARSET=UTF8"
        )
        conn = sqlalchemy.create_engine(f'mssql+pyodbc:///?odbc_connect={connect_string}', fast_executemany=True)
    return conn


if  server_choice:
    st.success(f"Selected Server: **{server_choice}**")
    st.write("if 1")
    query= f"SELECT [name],[host] FROM [data].[database] WHERE [host]='{server_choice}' AND [name] not like '%_test'"
    st.write(query)
    DATABASES_CHOICE= sql_setup.get_data(query=query,chunksize=100)
    st.write(DATABASES_CHOICE)

    DATABASE_LIST= DATABASES_CHOICE['name'].tolist()
    SERVER_LIST= DATABASES_CHOICE['host'].tolist()
    st.write(DATABASE_LIST)
    st.write(SERVER_LIST)

    # Select Database
    database_choice = st.sidebar.selectbox("Select a Database:", DATABASE_LIST)

    #db_info = DATABASES[database_choice]
    db_info=DATABASES_CHOICE[(DATABASES_CHOICE['name']==database_choice) & (DATABASES_CHOICE['host']==server_choice)]
    st.write(db_info)
    #SERVER = db_info["server"].iloc[0]

    if database_choice:        
        # Connect to the selected database
        query= f"SELECT * FROM [data].[database_credentials] WHERE [host] = '{server_choice}' AND [database_name] = '{database_choice}' " #where added  WHERE [host] = '{server_choice}' AND [database_name] = '{database_choice}'
        st.write(query)
        CREDENTIALS_CHOICE= sql_setup.get_data(query=query,chunksize=100)
        #credentials= CREDENTIALS_CHOICE[(CREDENTIALS_CHOICE['database_name']==database_choice) & (CREDENTIALS_CHOICE['host']==server_choice)]
        st.write(CREDENTIALS_CHOICE)
        #st.write(credentials)

        USERNAME = CREDENTIALS["username"].iloc[0]
        PASSWORD = CREDENTIALS["password"].iloc[0]
        
        
        # Function to fetch schemas from the selected database
        def get_schemas():
            query = f"SELECT DISTINCT [schema] FROM [data].[table] WHERE [host]='{server_choice}' AND [database_name] = '{database_choice}' " #added where WHERE [database_name] = '{database_choice}'
            st.write(query)
            sql_setup.connect()
            df = sql_setup.get_data(query=query,chunksize=100)
            if df.empty:
                return st.write("No schema was found")
            else:
                st.write(df)
                return df['schema'].tolist()
            

        # Select Schema
        schemas = get_schemas()
        schema_choice = st.sidebar.selectbox("Select a Schema:", schemas)
        
        @st.cache_data
        def get_tables(schema_choice):
            query = f"""
            SELECT [name]
            FROM [data].[table]
            WHERE [schema] = '{schema_choice}'
            AND [database_name] = '{database_choice}'
            AND [host]='{server_choice}'  """ 
            #sql_setup.connect()
            df = sql_setup.get_data(query=query,chunksize=100)
            return df['name'].tolist()
        
        if schema_choice:
            tables = get_tables(schema_choice)
            table = st.sidebar.selectbox("Select a Table:", tables)

            if table:
              
                sql_setup_1 = get_sql(f'{database_choice.upper()}')

                # Fetch data
                query = f"SELECT TOP 1000 * FROM [{schema_choice}].[{table}]"
                st.write(query)
                df = sql_setup_1.get_data(query)

                if df.empty:
                    st.warning("No data found in the table.")
                else:
                    # Display Raw Data
                    st.subheader("Raw Data")
                    st.write(df)

                    # Separate Sidebar for Filtering
                    with st.sidebar.expander("🔍 Advanced Filtering", expanded=True):
                        st.markdown("#### Enter a filter query")
                        st.write("Example: ```Brand == 'MARS' and `Variant Code` == 'V002'```")

                        # Get Column Names
                        columns = df.columns.tolist()
                        st.write("Columns:", columns)

                        # User inputs query
                        user_query = st.text_area(
                            "Enter your filter query:", 
                            value="", 
                            placeholder="e.g., `Brand` == 'MARS' and `Variant Code` == 'V002'"
                        )

                        # Convert AND/OR to lowercase for Pandas**
                        user_query = user_query.replace(" AND ", " and ").replace(" OR ", " or ").lower()

                        # Ensure column name consistency
                        df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
                        columns = df.columns.tolist()  # Get updated column names
                        st.write("Updated Columns:", columns)

                        # Replace spaces with backticks
                        for col in columns:
                            if " " in col:
                                user_query = re.sub(rf'\b{col}\b', f"`{col}`", user_query)

                        # Convert AND/OR to Pandas-compatible format
                        user_query = user_query.replace(" AND ", " and ").replace(" OR ", " or ").strip()


                        # Apply filtering safely
                        try:
                            if user_query.strip():  # Ensure the query is not empty
                                df_filtered = df.query(user_query)
                                st.subheader("Filtered Data")
                                st.write(df_filtered)
                            else:
                                df_filtered = df  # If no query, show full dataset
                        except Exception as e:
                            st.error(f"❌ Error in query: {e}")