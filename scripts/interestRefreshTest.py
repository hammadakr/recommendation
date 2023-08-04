from utils import performWithFileLock
import pandas as pd
import requests
import numpy as np

def updateInterest():
    INTEREST_URI = '../interestExport.feather'
    INTEREST_API = 'https://nikahforever.com/Ml/sent_interests'


    interest = performWithFileLock(INTEREST_URI, lambda: pd.read_feather(INTEREST_URI))
    
    try:
        lastTimestamp = interest.timestamp.max()
        if(lastTimestamp is None or lastTimestamp is np.nan):
            raise Exception('last timestamp is null')

        result = requests.post(INTEREST_API, data = {'timestamp' : lastTimestamp}).json()
        print(result)
        result_df = pd.DataFrame(result).rename(
            columns={'sender' : 'sender_id', 'receiver' : 'receiver_id', 'time' : 'timestamp', 'status' : 'isAccepted'}
            )
        result_df.isAccepted = (result_df.isAccepted != 'Pending').astype(int)

        result_df.sender_id = result_df.sender_id.astype(int)
        result_df.receiver_id = result_df.receiver_id.astype(int)
        result_df.timestamp = result_df.timestamp.astype(int)
        result_df.isAccepted = result_df.isAccepted.astype(int)

        interest = pd.concat([interest, result_df]).reset_index().drop(columns=['index'])
        performWithFileLock(INTEREST_URI, lambda : interest.to_feather(INTEREST_URI))
        print(f'Updated Interests added {result_df.shape[0]}')

    except Exception as e:
        print('Error: ', e)

updateInterest()