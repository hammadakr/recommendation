import pandas as pd
import pymysql
import numpy as np
import datetime
import csv

def getConnection():
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'
    # Establish a connection to MySQL
    return pymysql.connect(host=host, user=user, password=password, database=database)

def exportUsers2():
    connection = getConnection()
    try:
        select_query = 'SELECT * FROM Users WHERE status = 1'
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize=1000):
            chunks.append(chunk)

        pd.concat(chunks, ignore_index=True).to_feather('userExport.feather')  

    except Exception as e:
        print('Error:', e)
    finally:
        # Close the connection
        connection.close()

def exportInterest():
    connection = getConnection()
    try:
        select_query = 'SELECT * FROM Interests'
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize=50000):
            chunks.append(chunk)
        pd.concat(chunks, ignore_index=True).to_feather('interestExport.feather')  

    except Exception as e:
        print('Error:', e)
    finally:
        # Close the connection
        connection.close()

import time
start = time.time()
exportUsers2()
print(f'User export took {time.time() - start}')
start = time.time()
exportInterest()
print(f'Interest export took {time.time() - start}')