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
USER_ACTIVATION_FILE = '../userActivation.list'

DELETED_USERS_API = 'https://nikahforever.com/Ml/delted_members'
LAST_DELETE_DELIVERY = 'lastUserDeleteDelivery.json'
def fetchActivatedUsers() -> list:
    def readActivationsFunc():
        activations = []
        try:
            with open(USER_ACTIVATION_FILE, 'r') as file:
                activations = [int(x) for x in file.readlines()]
        except FileNotFoundError:
            activations = []
        return activations
    return performWithFileLock(USER_ACTIVATION_FILE, readActivationsFunc)


import updatedMembersParser as updateParser
import json
import datetime
from dateutil import relativedelta
import os

def activateUsers():
    try:      
        users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))  
        activatedUsers = list(set(fetchActivatedUsers()))
        users.loc[users.member_id.isin(activatedUsers), 'status'] = 1
        performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
        os.remove(USER_ACTIVATION_FILE)
        print(f'Updated Users activated {len(activatedUsers)}')
    except Exception as e:
        print(e)

def updateUsersViaApi():
    try:
        try:
            jsonData = {}
            with open(LAST_DELIVERY_JSON, 'w') as file:
                jsonData = requests.post(USERS_API).json()
                if 'response' in jsonData:
                    print('nothing received to update users')
                    return
                json.dump(jsonData, file)
        except Exception as e:
            print(f'Error parsing user update json: {e}')
            raise e
        newOrChangedUsers = updateParser.prepareDF(jsonData)
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
        print(f'Updated Users via api added {newUsers.shape[0]} and changed {changedUsers.shape[0]}')
    
    except Exception as e:
        print(f'refreshing users via api error: {e}')


def updateDeletedUsers():
        try:
            deletedJson = {}
            with open(LAST_DELETE_DELIVERY, 'w') as file:
                deletedJson = requests.get(DELETED_USERS_API).json()
                json.dump(deletedJson, file)
            
            if 'deleted_members' in deletedJson and len(deletedJson['deleted_members']) > 0:
                deleted_df = pd.DataFrame(deletedJson['deleted_members'])
                deleted_df['member_id'] = deleted_df['member_id'].astype(np.int32)

                users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))
                print(f'old num users: {len(users)}')
                users = users[~users.member_id.isin(deleted_df.member_id)]
                print(f'new num users: {len(users)}')
                performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
            else:
                print(f'No users to delete!')
        except Exception as e:
            print(f'refreshing deleted users via api error: {e}')

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
    activateUsers()
    updateDeletedUsers()   
    gc.collect()
    updateUsersViaApi()
    gc.collect()
    updateInterest()
    restartServer()
