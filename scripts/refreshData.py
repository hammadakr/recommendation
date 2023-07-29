import pandas as pd
import numpy as np
from utils import performWithFileLock
import requests

import logging

def setup_logger(log_file, log_level=logging.DEBUG):
    # Create a logger
    logger = logging.getLogger("CronRefreshLogger")

    # Set the log level
    logger.setLevel(log_level)

    # Create a file handler that logs to the specified file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)

    # Create a console handler that logs to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create a formatter to format the log messages
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set the formatter for both handlers
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Usage example
logger = setup_logger("cronJobRefresh.log", logging.DEBUG)

def updateUsers():
    global logger
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
        #only take approved users (need to delete deactivated)
        newOrChangedUsers = newOrChangedUsers[newOrChangedUsers.status == 1]

        idx = newOrChangedUsers.member_id.isin(users.member_id)
        newUsers = newOrChangedUsers[~idx]
        changedUsers = newOrChangedUsers[idx]
        users.set_index('member_id', inplace=True)
        users.update(changedUsers.set_index('member_id'))
        users.reset_index(inplace=True)

        users = pd.concat([users, newUsers]).reset_index().drop(columns=['index'])
        users = users[users.gender.notna()]

        int8s = ['gallery', 'status']
        int32s = ['age']
        int64s = ['lastonline']
        strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
        
        for cols, cols_type in zip([strings, int8s, int32s, int64s], [np.str_, np.int8, np.int32, np.int64]):
            for col in cols:
                users[col] = users[col].astype(cols_type)

        performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
        logger.info(f'Updated Users added {newUsers.shape[0]} and changed {changedUsers.shape[0]}')
    
    except Exception as e:
        logger.error(e)

def updateInterest():
    global logger
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
        logger.info(f'Updated Interests added {result_df.shape[0]}')

    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    #todo save updation timestamp
    updateUsers()
    updateInterest()
    #todo add server restart
