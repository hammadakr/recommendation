import pandas as pd
import pymysql
import numpy as np
import datetime

DB_CHUNK_SIZE = 10_000

def getConnection():
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'
    # Establish a connection to MySQL
    return pymysql.connect(host=host, user=user, password=password, database=database)


# def readExecute(action : callable):
#     connection = getConnection()
#     try:
#         # Create a cursor object to interact with the database
#         cursor = connection.cursor(pymysql.cursors.SSCursor)
#         return action(cursor)
#     except Exception as e:
#         print('Error:', e)
#     finally:
#         # Close the connection
#         connection.close()


def readExecuteConn(action : callable):
    connection = getConnection()
    try:
        # Create a cursor object to interact with the database
        return action(connection)
    except Exception as e:
        print('Error:', e)
    finally:
        # Close the connection
        connection.close()

def writeExecute(action : callable) -> None:
    connection = getConnection()
    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        action(cursor)
        # Commit the changes to the database
        connection.commit()
    except Exception as e:
        print('Error:', e)
        connection.rollback()
    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()

def updateUser(df : pd.DataFrame):
    def action(cursor):
        # Extract the values from the DataFrame
        values = tuple(df.values[0])
        # Construct the update query
        cols = [f'{x} = %s' for x in df.columns]
        update_query = f'UPDATE Users SET {", ".join(cols)} WHERE member_id = %s'
        # Execute the update query with the values
        cursor.execute(update_query, values.tolist() + [df.member_id.iat[0]])
    
    writeExecute(action=action)

def insertUsers(df : pd.DataFrame):
    def action(cursor):
        # Insert DataFrame records into the table
        insert_query = f'INSERT INTO Users ({", ".join(df.columns)}) VALUES ({", ".join(["%s" for x in df.columns])})'
        records = df.values.tolist()
        cursor.executemany(insert_query, records)

    writeExecute(action=action)

def setUserStatus(member_id : int, val : int):
    if val != 0 and val != 1:
        raise Exception('INVALID STATUS VALUE')

    def action(cursor):
        update_query = f'UPDATE Users SET status = %s, lastonline = %s WHERE member_id = %s'
        # Execute the update query with the values
        cursor.execute(update_query, [val, int(datetime.datetime.timestamp()), member_id])
    
    writeExecute(action=action)

def insertInterests(df : pd.DataFrame):
    def action(cursor):
        # Insert DataFrame records into the table
        insert_query = f'INSERT INTO Interests ({", ".join(df.columns)}) VALUES ({", ".join(["%s" for x in df.columns])})'
        records = df.values.tolist()
        cursor.executemany(insert_query, records)
        
    writeExecute(action=action)


def readUsers() -> pd.DataFrame:
    def action(connection):
        # Query to retrieve data from the database
        select_query = 'SELECT * FROM Users WHERE status = 1'

        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize = DB_CHUNK_SIZE):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
        
        df = df.where(pd.notnull(df), np.nan)
        return df

    return readExecuteConn(action=action)

#not caching since it requires memiozation (taking function args into account) and we dont regenerate that often for same person
def getUserInterests(member_id : int):
    def action(connection):
        # Query to retrieve data from the database
        select_query = 'SELECT receiver_id FROM Interests WHERE sender_id = %s'
        
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize = DB_CHUNK_SIZE, params=[member_id]):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
        
        df = df.where(pd.notnull(df), np.nan)
        return df

    return readExecuteConn(action=action)

def getAllInterest():
    def action(connection):
        # Query to retrieve data from the database
        select_query = 'SELECT * FROM Interests'
        
        chunks=[]
        for chunk in pd.read_sql(select_query, connection, chunksize = DB_CHUNK_SIZE):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
        
        df = df.where(pd.notnull(df), np.nan)
        return df

    return readExecuteConn(action=action)