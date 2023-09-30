DELETED_USERS_API = 'https://nikahforever.com/Ml/delted_members'
LAST_DELETE_DELIVERY = 'lastUserDeleteDelivery.json'
USER_URI = '../userExport.feather'
UPDATES_URI = '../userUpdation.csv'
INTEREST_URI = '../interestExport.feather'
INTEREST_API = 'https://nikahforever.com/Ml/sent_interests'
USERS_API = 'https://nikahforever.com/Ml/updated_members_info'
LAST_DELIVERY_JSON = 'lastUserDelivery.json'
LAST_TIMESTAMP_URI = 'lastTimestamp.json'
USER_ACTIVATION_FILE = '../userActivation.list'


import pandas as pd
import numpy as np
from utils import performWithFileLock
import requests
import subprocess
import gc

import logging

import updatedMembersParser as updateParser
import json
import datetime
from dateutil import relativedelta
import os



def updateDeletedUsers():
        try:
            deletedJson = {}
            with open(LAST_DELETE_DELIVERY, 'r') as file:
                deletedJson = json.load(file)

            if 'deleted_members' in deletedJson and len(deletedJson['deleted_members']) > 0:
                deleted_df = pd.DataFrame(deletedJson['deleted_members'])
                deleted_df['member_id'] = deleted_df['member_id'].astype(np.int32)

                users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))
                print(f'old num users: {len(users)}')
                oldLength = len(users)
                users = users[~users.member_id.isin(deleted_df.member_id)].reset_index(drop=True)
                print(f'new num users: {len(users)}')
                performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))
                print(f'deleted: {len(users) - oldLength}')
            else:
                print(f'No users to delete!')
        except Exception as e:
            print(f'refreshing deleted users via api error: {e}')

updateDeletedUsers()
