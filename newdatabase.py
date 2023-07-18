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

def writeToCsv(csv_file_path, cursor) -> None:
    # Open the file in 'write' mode with newline=''
    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        
        columns = [desc[0] for desc in cursor.description]
        writer.writerow(columns)

        writer.writerows(cursor.fetchall())
        
        # # Iterate over the generator and write each tuple as a row
        # row = cursor.fetchone()
        # while(row is not None):
        #     writer.writerow(row)
        #     row = cursor.fetchone()

def exportUsers():
    connection = getConnection()
    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor(pymysql.cursors.SSCursor)
        select_query = 'SELECT * FROM Users WHERE status = 1'
        cursor.execute(select_query)
        writeToCsv('userExport', cursor)
    except Exception as e:
        print('Error:', e)
    finally:
        # Close the connection
        connection.close()

def exportUsers2():
    connection = getConnection()
    try:
        select_query = 'SELECT * FROM Users WHERE status = 1'
        # select_query = 'SELECT * FROM Users WHERE status = 1 AND DATE(`lastonline`) = CURDATE()'
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize=1000):
            chunks.append(chunk)

        pd.concat(chunks, ignore_index=True).to_csv('userExport', index=False)  

    except Exception as e:
        print('Error:', e)
    finally:
        # Close the connection
        connection.close()

def exportInterest():
    connection = getConnection()
    try:
        select_query = 'SELECT * FROM Interests'
        # select_query = 'SELECT * FROM Interests WHERE DATE(`lastonline`) = CURDATE()'
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize=1000):
            chunks.append(chunk)
        
        pd.concat(chunks, ignore_index=True).to_csv('interestExport', index=False)  

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