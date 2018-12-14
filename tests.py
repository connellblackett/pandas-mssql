import os

import pandas as pd
import numpy as np
from dotenv import load_dotenv

from pandas_mssql import create_mssql_engine, to_mssql

os.chdir(os.path.dirname(__file__))
load_dotenv()

mssql_username = os.environ.get('MSSQL_USERNAME') 
mssql_password = os.environ.get('MSSQL_PASSWORD') 
mssql_host = os.environ.get('MSSQL_HOST') 
mssql_database = os.environ.get('MSSQL_DATABASE')

mssql_engine = create_mssql_engine(
    mssql_username, mssql_password, mssql_host, mssql_database)

df = pd.read_excel('faa_data_subset.xlsx', dtype='object')

df.to_mssql('faa_data_subset', mssql_engine, if_exists='replace')