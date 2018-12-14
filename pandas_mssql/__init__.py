import os
import re
import subprocess
import tempfile
from functools import wraps

import pyodbc
import pandas as pd
from pandas import DataFrame
from sqlalchemy import create_engine

def monkeypatch_method(cls):
    @wraps(cls)
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator

def get_mssql_driver():
    for d in pyodbc.drivers():
        if 'SQL Server' in d:
            driver = d.replace(' ', '+')
    return driver

def create_mssql_engine(username, password, host, database):
    driver = get_mssql_driver()
    connection_sring = 'mssql+pyodbc://{}:{}@{}/{}?driver={}'.format(
        username, password, host, database, driver)
    return create_engine(connection_sring)

@monkeypatch_method(DataFrame)
def to_mssql(
    self, table, engine, schema=None, if_exists="fail", index=False, sep = '§', 
    line_terminator = '±'):
    """Write records stored in a DataFrame to an MSSQL database using BCP"""

    # under windows utf-8 isnt supported so we're using cp-1252. this has to 
    # specified in a switch. the stdout will be ascii 
    if os.name == 'nt':
        encoding = 'cp1252'
        stdout_encoding = 'ascii'
        code_page = ['-C', '1252']
    # under unix the file has to be formatted as utf-8, and no code page 
    # argument is required. the stdout will also be utf-8
    elif os.name == 'posix':
        encoding = 'utf_8'
        stdout_encoding = encoding
        code_page = []
            
    # we have to create a temporary file to write to and for bcp to read from
    # this has to be released without being deleted or bcp will see it as locked 
    with tempfile.NamedTemporaryFile(delete=False) as f:
        filename = f.name

    try:
        self.to_csv(
            path_or_buf=filename, sep=sep, header=False, index=index, 
            encoding=encoding, line_terminator=line_terminator)

        # we want to trick pandas into creating an empty table with correct
        # datatypes, by inserting an empty dataframe
        self[0:0].to_sql(
            name=table, con=engine, if_exists=if_exists, index=index, 
            schema=schema)
        
        # bcp wont accept a connection string so we extract the attributes from
        # the engine
        bcp_cmd = [
            'bcp', ('' if schema is None else schema + '.') + table,
            'in', filename, '-S', engine.url.host, '-d', engine.url.database,
            '-U', engine.url.username, '-P', engine.url.password,
            '-c', '-t', sep, '-r', line_terminator
            ]

        # the code page has to be specified under windows so we append the 
        # arguments here. this isnt supported under unix so we add an empty list
        bcp_cmd = bcp_cmd + code_page

        # we're letting the subprocess module compile the command to handle the
        # escaping of the switches
        completed_process = subprocess.run(
            bcp_cmd, check=True, stdout=subprocess.PIPE)
            
    # the delete=False prevents deltion of the temporary file, so we force it
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    # there's a possibility not all rows are copied so we parse it from the 
    # stdout...
    stdout = completed_process.stdout.decode(stdout_encoding)
    rows_copied = int(re.search(r'(\d+) rows copied', stdout).group(1))

    # ...and throw an error if it doesnt match the dataframe, so the caller can 
    # rollback etc
    try:
        assert rows_copied == len(self)
    except AssertionError:
        raise AssertionError('Some rows not copied')
