import json
from pprint import pprint
import pandas as pd
import numpy as np
import datetime
from dateutil import relativedelta

def parseUser(user : dict):
    userFormData = [
        'member_id', 'date_of_birth', 'gender', 'membership', 'gallery', 'status',
        'marital_status', 'permanent_country', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect'
    ]
    userFormData = dict(zip(userFormData, userFormData))
    userFormData['status'] = 'approve_status'
    userFormData['gallery'] = 'gallery_display'
    userFormData['highest_education'] = 'education'
    userFormData['sect'] = 'sub_caste'
    userFormData['occupation'] = 'designation'
    userFormData['employed'] = 'occupation'

    missing_columns = []
    values = []
    for col, key in userFormData.items():
        try:
            if key in user:
                val = user[key]
                values.append(val if (val is not None) or (val != '') else np.nan)
            else:
                raise Exception('missing column')                
        except:
            missing_columns.append(col)

    if missing_columns:
        return {}
        raise Exception(f'missing columns: {", ".join(missing_columns)}')

    newUser = dict(zip(list(userFormData.keys()), values))
    
    if newUser['gender'] == '1':
        newUser['gender'] = 'Male'
    elif newUser['gender'] == '2':
        newUser['gender'] = 'Female'
    else:
        genderVal = newUser["gender"]
        raise Exception(f'invalid gender! : {genderVal}')

    strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
    MAX_STRING_LENGTH_IN_DATA = 30
    for col in strings:
        newUser[col] = newUser[col][:MAX_STRING_LENGTH_IN_DATA] if (newUser[col] is not None) and (newUser[col] != '') else np.nan


    return newUser

def prepareDF(updatedUsersJson : dict) -> pd.DataFrame:
    int8s = ['gallery', 'status']
    int32s = ['member_id']
    int64s = ['lastonline', 'date_of_birth']
    strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']

    df = pd.DataFrame([parseUser(user['userData']) for user in updatedUsersJson['data']])
    df = df[~ (df.member_id.isna() | df.gender.isna() | df.date_of_birth.isna() | df.membership.isna() | df.marital_status.isna())]

    df['gallery'] = (df.gallery == 'yes').astype(int)
    df['status'] = (df.status == 'approved').astype(int)
    df['lastonline'] = int(datetime.datetime.now().timestamp())

    for cols, cols_type in zip([strings, int8s, int32s, int64s], ["category", np.int8, np.int32, np.int64]):
        for col in cols:
            df[col] = df[col].astype(cols_type)

    df.loc[:, 'permanent_state'] = df.apply(lambda row: 'Foreign' if row.permanent_country != 'India' else row.permanent_state, axis=1)
    return df.drop_duplicates(subset=['member_id'], keep='last')

def loadBadFileIntoJson(filename : str):
    textData = ''
    with open(filename,'r') as file:
        textData = file.read()    
    if textData:
        return json.loads('{"data":[' + textData.replace(r'}}', r'}},')[:-1] + ']}')
    else:
        raise Exception('invalid bad file:', filename)

#example        
# if __name__ == '__main__':
#     df_1 = prepareDF(loadBadFileIntoJson('updated_members_info'))
#     df_2 = prepareDF(loadBadFileIntoJson('updated_members_info2'))
#     df_1_only = df_1[~df_1.member_id.isin(df_2.member_id)]
#     df = pd.concat([df_1_only, df_2])
#     df.to_csv('updatedUsersFinalPull.csv', index=False)
#     print(df)
#     print(df.iloc[0])
#     print(f'shape: {df.shape}, df_1: {df_1.shape}, df_2: {df_2.shape}, unique: {len(df.member_id.unique())}')
