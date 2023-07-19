import pandas as pd
import numpy as np
from utils import performWithFileLock
import requests

def updateUsers():
    try:
        USER_URI = '../userExport.feather'
        UPDATES_URI = '../userUpdation.csv'

        users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))

        def readAndClearUpdates():
            read = pd.read_csv(UPDATES_URI)
            pd.DataFrame(columns=read.columns).to_csv(UPDATES_URI, index=False)
            return read

        newOrChangedUsers = performWithFileLock(UPDATES_URI, readAndClearUpdates)
        newOrChangedUsers = newOrChangedUsers.sort_values('lastonline', ascending=False).drop_duplicates(['member_id'])

        idx = newOrChangedUsers.member_id.isin(users.member_id) & (newOrChangedUsers.status == 1)
        # deleted_member_ids = newOrChangedUsers[newOrChangedUsers.status == 0].member_id
        newUsers = newOrChangedUsers[~idx]
        changedUsers = newOrChangedUsers[idx]
        users.set_index('member_id', inplace=True)
        users.update(changedUsers.set_index('member_id'))
        users.reset_index(inplace=True)

        users = pd.concat([users, newUsers]).reset_index().drop(columns=['index'])

        performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
        print(f'Updated Users added {newUsers.shape[0]} and changed {changedUsers.shape[0]}')
    except Exception as e:
        print('error: ', e)

def updateInterest():
    INTEREST_URI = '../interestExport/feather'
    INTEREST_API = ''

    #REMOVE WHEN INTEREST API IS AVAILABLE
    return

    interest = performWithFileLock(INTEREST_URI, lambda: pd.read_feather(INTEREST_URI))

    try:
        lastTimestamp = interest.timestamp.max()
        if(lastTimestamp is None or lastTimestamp is np.nan):
            raise Exception('last timestamp is null')

        result = requests.post(INTEREST_API, data = {'timestamp' : lastTimestamp}).json()
        result_df = pd.DataFrame(result)
        result_df.sender_id = result_df.sender_id.astype(int)
        result_df.receiver_id = result_df.receiver_id.astype(int)
        result_df.timestamp = result_df.timestamp.astype(int)
        result_df.isAccepted = result_df.isAccepted.astype(int)

        interest = pd.concat([interest, result_df]).reset_index().drop(columns=['index'])
        performWithFileLock(INTEREST_URI, lambda : interest.to_feather(INTEREST_URI))
        print(f'Updated Interests added {result_df.shape[0]}')

    except Exception as e:
        print('Error: ', e)

if __name__ == '__main__':
    #todo save updation timestamp
    updateUsers()
    updateInterest()
