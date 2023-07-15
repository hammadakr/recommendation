import pymysql
import pandas as pd
import numpy as np
import datetime

def readExecute(action : callable):
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        return action(cursor)
    except Exception as e:
        print('Error:', e)

    finally:
        # Close the connection
        connection.close()

def writeExecute(action : callable) -> None:
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

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

def readUsers() -> pd.DataFrame:
    # def action(cursor):
    #     # Query to retrieve data from the database
    #     select_query = 'SELECT * FROM Users WHERE status = 1'
    #     # Execute the query
    #     cursor.execute(select_query)
    #     # Fetch all the rows as a list of tuples
    #     rows = cursor.fetchall()
    #     # Get column names from cursor description
    #     column_names = [desc[0] for desc in cursor.description]
    #     # Create a DataFrame from the fetched rows and column names
    #     df = pd.DataFrame(rows, columns=column_names)
    #     # Replace None values with NaN
    #     df = df.where(pd.notnull(df), np.nan)
    #     return df

    # readExecute(action=action)

    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Query to retrieve data from the database
        select_query = 'SELECT * FROM Users WHERE status = 1'
        
        # Execute the query
        cursor.execute(select_query)
        
        # Fetch all the rows as a list of tuples
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        column_names = [desc[0] for desc in cursor.description]
        
        # Create a DataFrame from the fetched rows and column names
        df = pd.DataFrame(rows, columns=column_names)
        
        # Replace None values with NaN
        df = df.where(pd.notnull(df), np.nan)

        return df

    except Exception as e:
        print('Error:', e)

    finally:
        # Close the connection
        connection.close()

def updateUser(df : pd.DataFrame):
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Extract the values from the DataFrame
        values = tuple(df.values[0])
        
        # Construct the update query
        cols = [f'{x} = %s' for x in df.columns]

        update_query = f'UPDATE Users SET {", ".join(cols)} WHERE member_id = {df.member_id.iat[0]}'
    
        # Execute the update query with the values
        cursor.execute(update_query, values)
        
        # Commit the changes to the database
        connection.commit()
        
    except Exception as e:
        print('Error:', e)
        connection.rollback()

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()

def insertUsers(df : pd.DataFrame):
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Insert DataFrame records into the table
        insert_query = f'INSERT INTO Users ({", ".join(df.columns)}) VALUES ({", ".join(["%s" for x in df.columns])})'
        records = df.values.tolist()
        cursor.executemany(insert_query, records)
        
        # Commit the changes to the database
        connection.commit()
        
    except Exception as e:
        print('Error:', e)
        connection.rollback()

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()

def setUserStatus(member_id : int, val : int):
    if val != 0 and val != 1:
        raise Exception('INVALID STATUS VALUE')
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()

        update_query = f'UPDATE Users SET status = %s, lastonline = %s WHERE member_id = %s'
    
        # Execute the update query with the values
        cursor.execute(update_query, [val, int(datetime.datetime.timestamp()), member_id])
        
        # Commit the changes to the database
        connection.commit()
        
    except Exception as e:
        print('Error:', e)
        connection.rollback()

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()

#not caching since it requires memiozation (taking function args into account) and we dont regenerate that often for same person
def getUserInterests(member_id : int):
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Query to retrieve data from the database
        select_query = 'SELECT receiver_id FROM Interests WHERE sender_id = %s'
        
        # Execute the query
        cursor.execute(select_query, member_id)
        
        # Fetch all the rows as a list of tuples
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        column_names = [desc[0] for desc in cursor.description]
        
        # Create a DataFrame from the fetched rows and column names
        df = pd.DataFrame(rows, columns=column_names)
        
        # Replace None values with NaN
        df = df.where(pd.notnull(df), np.nan)
        
        return df

    except Exception as e:
        print('Error:', e)
        raise e

    finally:
        # Close the connection
        connection.close()

def getAllInterest():
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Query to retrieve data from the database
        select_query = 'SELECT * FROM Interests'
        
        # Execute the query
        cursor.execute(select_query)
        
        # Fetch all the rows as a list of tuples
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        column_names = [desc[0] for desc in cursor.description]
        
        # Create a DataFrame from the fetched rows and column names
        df = pd.DataFrame(rows, columns=column_names)
        
        # Replace None values with NaN
        df = df.where(pd.notnull(df), np.nan)
        
        return df

    except Exception as e:
        print('Error:', e)
        raise e

    finally:
        # Close the connection
        connection.close()

def insertInterests(df : pd.DataFrame):
    # MySQL connection details
    host = 'localhost'
    user = 'root'
    password = 'password'
    database = 'nfdb'

    # Establish a connection to MySQL
    connection = pymysql.connect(host=host, user=user, password=password, database=database)

    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Insert DataFrame records into the table
        insert_query = f'INSERT INTO Interests ({", ".join(df.columns)}) VALUES ({", ".join(["%s" for x in df.columns])})'
        records = df.values.tolist()
        cursor.executemany(insert_query, records)
        
        # Commit the changes to the database
        connection.commit()
        
    except Exception as e:
        print('Error:', e)
        connection.rollback()

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()
