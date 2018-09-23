import os
import re
import subprocess
import tempfile
from functools import wraps

import pyodbc
import pandas as pd
from pandas import DataFrame
from sqlalchemy import create_engine

def get_driver():
    for d in pyodbc.drivers():
        if 'SQL Server' in d:
            driver = d.replace(' ', '+')
    return driver

def get_engine(user, password, server, database):
    driver = get_driver()
    engine = create_engine(
        f'mssql+pyodbc://{user}:{password}@{server}/{database}?driver={driver}'
        )
    return engine

def monkeypatch_method(cls):
    @wraps(cls)
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator

def read_mssql(table, user, password, server, database, params=None):
    """Read MSSQL query or database table into a DataFrame."""
    engine = get_engine(user, password, server, database)
    df = pd.read_sql(table, engine, params=params)
    return df

@monkeypatch_method(DataFrame)
def to_mssql(
        self, table, user, password, server, database, 
        if_exists="fail", index=False, line_terminator = '±', sep = '§'
        ):
    """Write records stored in a DataFrame to a MSSQL database using BCP."""

    # set file and stdout encodings based on platform
    if os.name == 'nt':
        encoding = 'cp1252'
        stdout_encoding = 'ascii'
        code_page = ['-C', '1252']
    elif os.name == 'posix':
        encoding = 'utf_8'
        stdout_encoding = encoding
        code_page = []

    # get an engine with the SQL Server driver
    engine = get_engine(user, password, server, database)
            
    # get the name of a temporary file we can use to write to for BCP to read
    with tempfile.NamedTemporaryFile(delete=False) as f:
        filename = f.name

    try:
        # write the data to the temporary file
        self.to_csv(
            path_or_buf=filename, 
            sep=sep, 
            header=False, 
            index=index, 
            encoding=encoding,
            line_terminator=line_terminator
            )

        # use the pandas to_sql method to write the empty dataframe to the table
        self[0:0].to_sql(
            name=table, con=engine, if_exists=if_exists, index=index
            )
        
        # compile the BCP args
        bcp_cmd = [
            'bcp', table, 'in', filename,
            '-S', server, '-d', database, '-U', user,  '-P', password,
            '-c', '-t',  sep,  '-r', line_terminator
            ] + code_page

        # run the BCP command and capture the output
        completed_process = subprocess.run(
            bcp_cmd, check=True, stdout=subprocess.PIPE
            )
            
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    # check how many rows have been copied
    stdout = completed_process.stdout.decode(stdout_encoding)
    rows_copied = int(re.search(r'(\d+) rows copied', stdout).group(1))

    # check all rows have been inserted
    try:
        assert rows_copied == len(self)
    except AssertionError:
        raise AssertionError('Some rows not copied')
