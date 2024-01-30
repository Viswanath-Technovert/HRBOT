# Import Statements
import urllib
from langchain.sql_database import SQLDatabase

from langchain.agents import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai.chat_models.azure import AzureChatOpenAI
from langchain.agents.agent_types import AgentType

import os

os.environ['OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_OPENAI_API_KEY'] = 'e63ed695495543d58595fab4e27e4ff1'

def get_connection_string():
    server = 'mysqlserver16666.database.windows.net'
    database = 'GMBOT'
    username = 'Azureuser'
    password = 'Azure@23498'   
    driver= '{ODBC Driver 17 for SQL Server}'

    conn = f"""Driver={driver};Server=tcp:{server},1433;Database={database};
    Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"""

    params = urllib.parse.quote_plus(conn)
    conn_str = 'mssql+pyodbc:///?autocommit=true&odbc_connect={}'.format(params)

    return conn_str

def sql_query(question):
    conn_str = get_connection_string()

    db = SQLDatabase.from_uri(conn_str)

    sql_llm = AzureChatOpenAI(azure_deployment='gpt-16k',
                              azure_endpoint='https://tv-llm-applications.openai.azure.com/')

    toolkit = SQLDatabaseToolkit(db=db, llm=sql_llm)
    agent_executor = create_sql_agent(
        llm=sql_llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS
    )

    response = agent_executor.invoke(question)

    return response