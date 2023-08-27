import pandas as pd
import numpy as np
from utils import performWithFileLock
import requests
import subprocess
import gc

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

logger = setup_logger("cronJobRefresh.log", logging.DEBUG)

USER_URI = '../userExport.feather'
UPDATES_URI = '../userUpdation.csv'
INTEREST_URI = '../interestExport.feather'
INTEREST_API = 'https://nikahforever.com/Ml/sent_interests'
USERS_API = 'https://nikahforever.com/Ml/updated_members_info'
LAST_DELIVERY_JSON = 'lastUserDelivery.json'
LAST_TIMESTAMP_URI = 'lastTimestamp.json'

def updateUsers():
    global logger
    try:
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
        int64s = ['lastonline', 'date_of_birth']
        strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
        
        for cols, cols_type in zip([strings, int8s, int64s], ["category", np.int8, np.int64]):
            for col in cols:
                users[col] = users[col].astype(cols_type)

        performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
        logger.info(f'Updated Users added {newUsers.shape[0]} and changed {changedUsers.shape[0]}')
    
    except Exception as e:
        logger.error(e)

import updatedMembersParser as updateParser
import json
import datetime
from dateutil import relativedelta

def updateUsersViaApi():
    global logger
    try:
        users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))

        lastTimestamp = int((datetime.datetime.now() - relativedelta.relativedelta(days=1)).timestamp())
        try:
            with open(LAST_TIMESTAMP_URI, 'r') as file:
                lastTimestamp = json.load(file)
        except Exception as e:
            logger.error(f'Could not load last timestamp error: {e}')

        with open(LAST_TIMESTAMP_URI, 'w') as file:
            json.dump({"time" : int(datetime.datetime.now().timestamp())}, file)

        with open(LAST_DELIVERY_JSON, 'w') as file:
            #receiving invalid json from server
            file.write(requests.post(USERS_API, { 'time' : lastTimestamp}).text)

        newOrChangedUsers = updateParser.prepareDF(updateParser.loadBadFileIntoJson(LAST_DELIVERY_JSON))
        #only take approved users (need to delete deactivated)
        newOrChangedUsers = newOrChangedUsers[newOrChangedUsers.status == 1]

        idx = newOrChangedUsers.member_id.isin(users.member_id)
        newUsers = newOrChangedUsers[~idx]
        changedUsers = newOrChangedUsers[idx]
        
        users.set_index('member_id', inplace=True)
        users.update(changedUsers.set_index('member_id'))
        users.reset_index(inplace=True)
        users = pd.concat([users, newUsers]).reset_index().drop(columns=['index'])

        performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
        logger.info(f'Updated Users via api added {newUsers.shape[0]} and changed {changedUsers.shape[0]}')
    
    except Exception as e:
        logger.error(f'refreshing users via api error: {e}')

def updateInterest():
    global logger
    interest = performWithFileLock(INTEREST_URI, lambda: pd.read_feather(INTEREST_URI))
    
    try:
        lastTimestamp = interest.timestamp.max()
        if(lastTimestamp is None or lastTimestamp is np.nan):
            raise Exception('last timestamp is null')

        result = requests.post(INTEREST_API, data = {'time' : lastTimestamp}).json()
                
        result_df = pd.DataFrame(result).rename(
            columns={'sender' : 'sender_id', 'receiver' : 'receiver_id', 'time' : 'timestamp', 'status' : 'isAccepted'}
            )
        
        for col in result_df.columns:
            result_df = result_df[result_df[col] != '']

        result_df.isAccepted = (result_df.isAccepted != 'Pending').astype(int)

        result_df.sender_id = result_df.sender_id.astype(int)
        result_df.receiver_id = result_df.receiver_id.astype(int)
        result_df.timestamp = result_df.timestamp.astype(int)
        result_df.isAccepted = result_df.isAccepted.astype(int)

        interest = pd.concat([interest, result_df], ignore_index=True)

        performWithFileLock(INTEREST_URI, lambda : interest.to_feather(INTEREST_URI))
        logger.info(f'Updated Interests added {result_df.shape[0]}')

    except Exception as e:
        print('Error: ', e)

def restartServer():
    subprocess.check_call(['./restart.sh'], cwd='/root/recommendation/flask_recommendation', shell=True)

if __name__ == '__main__':
    #todo save updation timestamp
    updateUsers()   
    gc.collect()
    updateUsersViaApi()
    gc.collect()
    updateInterest()
    restartServer()
