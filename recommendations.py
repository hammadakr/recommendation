import math
import datetime
from dateutil import relativedelta
import calendar
import time
from functools import wraps
import json
import gc

import pandas as pd
import numpy as np

from flask import Flask, render_template, request, Blueprint, Response, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


from scripts.utils import Timer, performWithFileLock

import logging

def setup_logger(log_file, log_level=logging.DEBUG):
    # Create a logger
    logger = logging.getLogger("MyLogger")

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

logger = setup_logger("my_logfile.log", logging.DEBUG)

def topLevelCatcher(action_func):
    @wraps(action_func)
    def wrapper(*args, **kwargs):
        global logger
        try:
            return action_func(*args, **kwargs)
        except Exception as e:
            logger.error(e)
            return f'Internal Error: {e}', 400
    return wrapper

# UPDATION_URI = 'userUpdation.csv'
USERS_URI = 'userExport.feather'
INTEREST_URI = 'newInterestExport.feather'

# UPDATED_USERS_COLUMN_FORMAT = performWithFileLock(UPDATION_URI, lambda: pd.read_csv(UPDATION_URI, nrows=0).columns.tolist())
# def addUpdation(updatedUser : pd.DataFrame) -> None:
#     performWithFileLock(UPDATION_URI, lambda : updatedUser.drop(columns=['lastActiveDate', 'monthYear'])[UPDATED_USERS_COLUMN_FORMAT].to_csv(UPDATION_URI, mode='a', index=False, header=False))

USER_ACTIVATION_FILE = 'userActivation.list'
def activateUser(member_id : int):
    def activationFunc():
        try:
            with open(USER_ACTIVATION_FILE, 'a') as file:
                file.write(str(member_id) + '\n')
        except FileNotFoundError:
            with open(USER_ACTIVATION_FILE, 'w') as file:
                file.write(str(member_id) + '\n')
    performWithFileLock(USER_ACTIVATION_FILE, activationFunc)


"""
NOT IN USE
USER_CATEGORY_LIMITS = {
 'caste': 644,
 'employed': 8,
 'highest_education': 466,
 'income': 20,
 'occupation': 545,
 'permanent_country': 146,
 'permanent_state': 50,
 'sect': 4,
}
"""

USER_CATEGORY_LIMITS = {
 'caste': 100,
 'employed': 20,
 'highest_education': 100,
 'income': 30,
 'occupation': 100,
 'permanent_country': 100,
 'permanent_state': 100,
 'sect': 20,
}

def getReducedUsers():
    reducedUsers = performWithFileLock(USERS_URI, lambda : pd.read_feather(USERS_URI))

    for col, limit in USER_CATEGORY_LIMITS.items():
        allowedVals = reducedUsers[col].value_counts().nlargest(limit).index
        reducedUsers.loc[~reducedUsers[col].isin(allowedVals), col] = 'Others'

    reducedUsers['lastActiveDate'] = reducedUsers.lastonline.apply(datetime.date.fromtimestamp)
    reducedUsers['monthYear'] = (
        reducedUsers.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).year).astype(str) +
        " " +
        reducedUsers.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).month).astype(str) +
        " (" +
        reducedUsers.lastonline.apply(lambda x: calendar.month_abbr[datetime.date.fromtimestamp(x).month]).astype(str) +
        ")"
    )
    today = datetime.date.today()
    reducedUsers['age'] = reducedUsers.date_of_birth.apply(lambda x: relativedelta.relativedelta(today, datetime.date.fromtimestamp(x)).years)
    reducedUsers.drop(columns=['date_of_birth', 'permanent_country', 'permanent_city'], inplace=True)
    return reducedUsers

def buildNanMap():
    global reducedUsers

    return dict(zip(dummyCols, [[f'{y}_{x}' for x in reducedUsers[y].astype(str).unique() if (x.endswith('nan'))] for y in dummyCols]))

def getEncodedUsers():
    global dummyCols, nanMap, reducedUsers

    temp = pd.get_dummies(reducedUsers[['member_id', 'age', 'gender'] + dummyCols], columns=dummyCols, dummy_na=True)
    for col in dummyCols:
        nanCols = nanMap[col]
        idx = np.sum(temp[nanCols].values, axis=1) > 0
        temp.loc[idx, nanCols] = 0

    temp = temp.loc[:, ~temp.columns.duplicated()].copy()
    encodedUsersOneHot = {x: temp[temp.gender != x].drop(columns=['gender']).astype(pd.SparseDtype("int32", 0)).copy(deep=True) for x in ['Male', 'Female']}

    del temp
    gc.collect()
                
    return encodedUsersOneHot

reducedUsers = getReducedUsers()
gc.collect()

def getInterest():
    global reducedUsers
    i_df = performWithFileLock(INTEREST_URI, lambda : pd.read_feather(INTEREST_URI))
    # i_df = i_df[i_df.sender_id.isin(reducedUsers.member_id) & i_df.receiver_id.isin(reducedUsers.member_id)]
    i_df = i_df[i_df.receiver_id.isin(reducedUsers.member_id)]
    return i_df

dummyCols = ['marital_status', 'permanent_state', 'highest_education',
             'occupation', 'caste', 'sect', 'employed', 'income']
nanMap = buildNanMap()
print('building encoded')
encodedUsersOneHot = getEncodedUsers()
gc.collect()
print('building interest')

interest_df = getInterest()

PROFILE_HALF_LIFE_WEEKS = 26
PROFILE_DECAY_CONSTANT = math.log(2) / PROFILE_HALF_LIFE_WEEKS
LATEST_ONLINE_DAY = datetime.date.fromtimestamp(reducedUsers['lastonline'].max())
gc.collect()
print('all done')

# discovery: reducedUsers actually takes up enormous amounts of memory (188MB in tests)
# when I changed the types to categorical it went down to 36MB
# interest df also takes 78MB if i drop timestamp it goes down to 53
# strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
# for s in strings:
    # reducedUsers[s] = reducedUsers[s].astype("category")
# print(f'reducedUsers: \n{reducedUsers.memory_usage(deep=True)}\n{reducedUsers.memory_usage(deep=True).sum()//(1000*1000)}\n{reducedUsers.dtypes}')
# print(f'encodedUsers Male: \n{encodedUsersOneHot["Male"].memory_usage(deep=True).sum()//(1000*1000)}')
# print(f'encodedUsers Female: \n{encodedUsersOneHot["Female"].memory_usage(deep=True).sum()//(1000*1000)}')
# print(f'interest: \n{interest_df.memory_usage(deep=True)}\n{interest_df.memory_usage(deep=True).sum()//(1000*1000)}\n{interest_df.dtypes}')

def getTimeDecay(lastActiveTimestamp: int):
    weeksSinceActive = (LATEST_ONLINE_DAY - datetime.date.fromtimestamp(lastActiveTimestamp)).days // 7
    decay = math.e**(-PROFILE_DECAY_CONSTANT*weeksSinceActive)
    return decay

@app.route("/past-interests/<member_id>", methods=['GET'])
def getPastInterests(member_id):
    try:
        member_id = int(member_id)
    except Exception as e:
        return f'Error: {e}', 400
    global reducedUsers, interest_df
    return reducedUsers[reducedUsers.member_id.isin(
        interest_df[interest_df.sender_id == member_id].receiver_id
        )].to_dict(orient='records')


def prepareUserFormData(member_id, userData):
    if userData is None:
        raise Exception('userData is None')

    userFormData = [
        'age', 'gender', 'membership', 'gallery', 'status',
        'marital_status', 'permanent_country', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect'
    ]
    #todo replace age with dob
    userFormData = dict(zip(userFormData, userFormData))
    userFormData['status'] = 'approve_status'
    userFormData['gallery'] = 'gallery_display'
    userFormData['highest_education'] = 'education'
    userFormData['sect'] = 'sub_caste'
    userFormData['occupation'] = 'designation'
    userFormData['employed'] = 'occupation'

    missing_columns = []
    values = [member_id]
    for col, key in userFormData.items():
        try:
            if key in userData:
                val = userData[key]
                values.append(val if (val is not None) or (val != '') else np.nan)
            else:
                raise Exception('missing column')                
        except:
            missing_columns.append(col)

    if missing_columns:
        raise Exception(f'missing columns: {", ".join(missing_columns)}')

    df_dict = dict(zip(['member_id'] + list(userFormData.keys()), values))
    
    #switched 
    if df_dict['gender'] == '1':
        df_dict['gender'] = 'Male'
    elif df_dict['gender'] == '2':
        df_dict['gender'] = 'Female'
    else:
        genderVal = df_dict["gender"]
        raise Exception(f'invalid gender! : {genderVal}')

    int8s = ['gallery', 'status']
    int32s = ['age']
    int64s = ['lastonline']
    strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
    
    MAX_STRING_LENGTH_IN_DATA = 30
    for col in strings:
        df_dict[col] = df_dict[col][:MAX_STRING_LENGTH_IN_DATA] if (df_dict[col] is not None) and (df_dict[col] != '') else np.nan

    df = pd.DataFrame([df_dict])

    df['gallery'] = (df.gallery == 'yes').astype(int)
    df['status'] = (df.status == 'approved').astype(int)
    df['lastonline'] = int(datetime.datetime.now().timestamp())

    for cols, cols_type in zip([strings, int8s, int32s, int64s], ["category", np.int8, np.int32, np.int64]):
        for col in cols:
            df[col] = df[col].astype(cols_type)

    df.loc[:, 'permanent_state'] = df.apply(lambda row: 'Foreign' if row.permanent_country != 'India' else row.permanent_state, axis=1)
    
    df['lastActiveDate'] = df.lastonline.apply(datetime.date.fromtimestamp)
    df['monthYear'] = (
        df.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).year).astype(str) +
        " " +
        df.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).month).astype(str) +
        " (" +
        df.lastonline.apply(lambda x: calendar.month_abbr[datetime.date.fromtimestamp(x).month]).astype(str) +
        ")"
    )

    df['date_of_birth'] = df['age'].apply(lambda x: (datetime.datetime.now() - relativedelta.relativedelta(years=x)).timestamp())

    return df.drop(columns=['permanent_country', 'age'])

@app.route("/get-user-info/<member_id>", methods=['GET'])
@topLevelCatcher
def getUserInfo(member_id):
    global reducedUsers
    unnecessaryCols = ['monthYear', 'lastonline', 'lastActiveDate']
    try:
        member_id = int(member_id)
        results = reducedUsers[reducedUsers.member_id == int(member_id)].drop(columns=unnecessaryCols).to_dict(orient='records')
        if results:
            return results[0]
        else:
            return "Member id not in data!"
    except ValueError as verr:
        return "Exception Encountered: supplied 'member_id' is not an integer!", 400
    except Exception as exc:
        return "Invalid input!", 400


def split_dataframe(df, chunk_size): 
    num_chunks = math.ceil(df.shape[0] / chunk_size)
    for i in range(num_chunks):
        yield df[i*chunk_size:(i+1)*chunk_size]

def createRecommendationResults(member_id, senderIsFemme, offset, count, withInfo, timeMix, premiumMix, galleryMix, errors = []):
    timer = Timer()
    timer.start()
    global reducedUsers, encodedUsersOneHot, interest_df, dummyCols

    senderGender = ('Female' if senderIsFemme else 'Male')

    oneHotTieredUsers = encodedUsersOneHot[senderGender]
    match_df = oneHotTieredUsers[oneHotTieredUsers.member_id.isin(
        interest_df[interest_df.sender_id == member_id].receiver_id)]
    preferences = match_df.mean(axis=0)

    values = []
    cols = []
    for category in [x for x in dummyCols]:
        idx = [x for x in preferences.index if x.startswith(category)]
        weight = 5**(preferences[idx].max())
        for tier in idx:
            values.append(weight * preferences[tier])
            cols.append(tier)

    vector = pd.Series(data=values, index=cols)
    ageLowerBound = match_df.age.quantile(
        q=0.5) if senderIsFemme else match_df.age.quantile(0.3)
    ageUpperBound = match_df.age.quantile(
        q=0.8) if senderIsFemme else match_df.age.quantile(0.7)
    
    timer.check('Gathering Preferences')

    # scores = pd.concat([(u_df @ vector) for u_df in split_dataframe(oneHotTieredUsers[vector.index], 10000)]).reset_index(drop=True)
    #performing the score calculation in chunks, to prevent out of memory
    chunk_size = 50000
    total_rows = oneHotTieredUsers.shape[0]
    results = []
    for i in range(0, total_rows, chunk_size):
        chunk = oneHotTieredUsers.iloc[i:i+chunk_size]        
        dot_product_chunk = chunk[vector.index].dot(vector)
        results.append(dot_product_chunk)
    # Concatenate the results into a single DataFrame
    scores = pd.concat(results)

    scores += oneHotTieredUsers.age.between(
        ageLowerBound, ageUpperBound).astype(float) * 2


    timer.check('Calculating base score')

    scoredUsers = pd.DataFrame(
            {'member_id': oneHotTieredUsers.member_id, 'score': scores}).sparse.to_dense()

    predictions = pd.merge(
        scoredUsers[['member_id', 'score']],
        reducedUsers, on='member_id'
    )

    timer.check('Merging dataframes')
    
    predictions['timeDecay'] = predictions.lastonline.apply(getTimeDecay)
    timeMixingFactor = timeMix
    predictions['score'] *= (1 - timeMixingFactor) + timeMixingFactor * predictions['timeDecay']

    timer.check('Applying time decay')

    predictions = predictions.nlargest(
        offset + count, columns='score'
    ).tail(count)

    premiumMemberships = predictions.membership == 'Premium'
    yesGallery = predictions.gallery == 1
    #reordering final predictions
    
    predictions.score *= (1 - premiumMix) + premiumMemberships * premiumMix
    predictions.score *= (1 - galleryMix) + yesGallery * galleryMix

    predictions.insert(1, 'already_liked', predictions.member_id.isin(match_df.member_id))
    percentageRecommendationsPremium = round(100 * premiumMemberships.sum() / predictions.shape[0])
    percentageRecommendationsGallery = round(100 * yesGallery.sum() / predictions.shape[0])
    
    predictions.loc[:, 'score'] = (predictions['score']/predictions['score'].max()).astype(float).round(2).fillna(0)
    predictions.sort_values(by='score', inplace=True, ascending=False)
    timer.check('Calculating final metrics')
    # timer.log()
    timer.end()

    if withInfo:
        for col in predictions:
            if predictions[col].dtype.name == 'category':
                predictions[col] = predictions[col].cat.add_categories([0])
        predictions.fillna(0, inplace=True)
    return {
        'userInterestCount': match_df.shape[0],
        'percentageResultsPremium' : percentageRecommendationsPremium,
        'percentageResultsHaveGallery' : percentageRecommendationsGallery,
        'userRecommendations': predictions[predictions.columns if withInfo else ['member_id', 'score']].to_dict(orient='records')
    }

@app.route("/recommendation", methods=['POST'])
@topLevelCatcher
def recommendation():
    global logger
    errors = []
    
    member_id = None
    try:
        member_id = int(request.form['member_id'])
    except ValueError as verr:
        logger.error("Recommendation: Exception Encountered: supplied 'member_id' is not an integer!");
        return "Recommendation: Exception Encountered: supplied 'member_id' is not an integer!", 400
    except Exception as exc:
        logger.error("Recommendation: Invalid input!")
        return "Recommendation: Invalid input!", 400

    formUserData = json.loads(request.form['userData'])
    if 'gender' not in formUserData:
        logger.error(f'invalid userData: {formUserData}')
        return f'Input userData has no key gender', 400
    
    formGender = str(formUserData['gender']).lower()
    senderIsFemme = False
    if formGender in ['1', 'male']:
        senderIsFemme = False
    elif formGender in ['2', 'female']:
        senderIsFemme = True
 
    controlParams = dict(
        offset = 0,
        count = 50,
        withInfo = False,
        timeMix = 0.25,
        premiumMix = 0,
        galleryMix = 0
    )
    for key, val in controlParams.items():
        try:
            controlParams[key] = type(val)(request.form[key])
        except:
            errors.append(f'Recommendation: Error: invalid {key} using default values {val}')

    gc.collect()
    activateUser(member_id=member_id)
    resultResponse = createRecommendationResults(member_id=member_id, senderIsFemme=senderIsFemme, errors=errors, **controlParams)
    #logger.info(str(resultResponse))
    return resultResponse

TESTING_WEBSITE_PATH = 'nf-recs-svelte/dist/'

@app.route('/test', methods=['GET'])
def testingWebsite():
    return send_file(f'{TESTING_WEBSITE_PATH}index.html')
    #print('maaz')

@app.route('/assets/<path:path>')
def send_asset(path):
    return send_from_directory(f'{TESTING_WEBSITE_PATH}/assets', path)

@app.route('/', methods=['GET'])
@topLevelCatcher
def home():
    return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8" /><title>nf!</title><meta name="viewport" content="width=device-width,initial-scale=1" /><meta name="description" content="" /></head><body><h1>nf-recommendation api!</h1></body></html>"""

