import math
import datetime
import calendar
import pandas as pd
import numpy as np
import time

from flask import Flask, render_template, request, Blueprint
from flask_cors import CORS

import json

import gc

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

# Usage example
logger = setup_logger("my_logfile.log", logging.DEBUG)

UPDATION_URI = 'userUpdation.csv'
USERS_URI = 'userExport.feather'
INTEREST_URI = 'interestExport.feather'

UPDATED_USERS_COLUMN_FORMAT = performWithFileLock(UPDATION_URI, lambda: pd.read_csv(UPDATION_URI, nrows=0).columns.tolist())
def addUpdation(updatedUser : pd.DataFrame) -> None:
    performWithFileLock(UPDATION_URI, lambda : updatedUser.drop(columns=['lastActiveDate', 'monthYear'])[UPDATED_USERS_COLUMN_FORMAT].to_csv(UPDATION_URI, mode='a', index=False, header=False))

def getReducedUsers():
    reducedUsers = performWithFileLock(USERS_URI, lambda : pd.read_feather(USERS_URI))
    reducedUsers['lastActiveDate'] = reducedUsers.lastonline.apply(datetime.date.fromtimestamp)
    reducedUsers['monthYear'] = (
        reducedUsers.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).year).astype(str) +
        " " +
        reducedUsers.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).month).astype(str) +
        " (" +
        reducedUsers.lastonline.apply(lambda x: calendar.month_abbr[datetime.date.fromtimestamp(x).month]).astype(str) +
        ")"
    )
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

    encodedUsersOneHot = {x: temp[temp.gender != x].drop(columns=['gender']).astype(pd.SparseDtype("int32", 0)).copy(deep=True) for x in ['Male', 'Female']}

    del temp
    gc.collect()
                
    return encodedUsersOneHot

def getInterest():
    return performWithFileLock(INTEREST_URI, lambda : pd.read_feather(INTEREST_URI))

reducedUsers = getReducedUsers()

dummyCols = ['marital_status', 'permanent_state', 'highest_education',
             'occupation', 'caste', 'sect', 'employed', 'income', 'permanent_city']
nanMap = buildNanMap()
encodedUsersOneHot = getEncodedUsers()

interest_df = getInterest()

PROFILE_HALF_LIFE_WEEKS = 26
PROFILE_DECAY_CONSTANT = math.log(2) / PROFILE_HALF_LIFE_WEEKS
LATEST_ONLINE_DAY = datetime.date.fromtimestamp(reducedUsers['lastonline'].max())

def getTimeDecay(lastActiveTimestamp: int):
    weeksSinceActive = (LATEST_ONLINE_DAY - datetime.date.fromtimestamp(lastActiveTimestamp)).days // 7
    decay = math.e**(-PROFILE_DECAY_CONSTANT*weeksSinceActive)
    return decay

@app.route("/past-interests/<member_id>", methods=['GET'])
def getPastInterests(member_id):
    member_id = int(member_id)
    global reducedUsers, interest_df
    return reducedUsers[reducedUsers.member_id.isin(
        interest_df[interest_df.sender_id == member_id].receiver_id
        )].to_dict(orient='records')

def getPopularCities():
    try:
        return pd.read_csv('popular_cities.csv') 
    except:
        global reducedUsers, interest_df
        popular_cities = pd.merge(
            interest_df,
            reducedUsers[['member_id', 'permanent_city']], left_on='receiver_id', right_on='member_id'
        ).groupby(
            by=['permanent_city']
        )['receiver_id'].count().reset_index().sort_values(
            'receiver_id', ascending=False
        ).head(100)
        popular_cities.to_csv('popular_cities.csv', index=False)
        return popular_cities

popular_cities = getPopularCities()

def prepareUserFormData(member_id, userData):
    if userData is None:
        raise Exception('userData is None')

    userFormData = [
        'age', 'gender', 'membership', 'gallery', 'status',
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
    
    if df_dict['gender'] == '1':
        df_dict['gender'] = 'Female'
    elif df_dict['gender'] == '2':
        df_dict['gender'] = 'Male'
    else:
        genderVal = df_dict["gender"]
        raise Exception(f'invalid gender! : {genderVal}')

    int8s = ['gallery', 'status']
    int32s = ['age']
    int64s = ['lastonline']
    strings = ['gender', 'membership', 'marital_status', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect']
    
    MAX_STRING_LENGTH_IN_DATA = 22
    for col in strings:
        df_dict[col] = df_dict[col][:MAX_STRING_LENGTH_IN_DATA] if (df_dict[col] is not None) and (df_dict[col] != '') else np.nan

    df = pd.DataFrame([df_dict])
    # if(df_dict['gallery'] not in ['Yes', 'No'])

    df['gallery'] = (df.gallery == 'yes').astype(int)
    df['status'] = (df.status == 'approved').astype(int)
    df['lastonline'] = int(datetime.datetime.now().timestamp())

    for cols, cols_type in zip([strings, int8s, int32s, int64s], [np.str_, np.int8, np.int32, np.int64]):
        for col in cols:
            df[col] = df[col].astype(cols_type)

    df.loc[:, 'permanent_state'] = df.apply(lambda row: 'Foreign' if row.permanent_country != 'India' else row.permanent_state, axis=1)
    global popular_cities
    df.loc[(~df.permanent_city.isin(popular_cities.permanent_city)) & (~df.permanent_city.isna()), 'permanent_city'] = 'Others'
    
    df['lastActiveDate'] = df.lastonline.apply(datetime.date.fromtimestamp)
    df['monthYear'] = (
        df.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).year).astype(str) +
        " " +
        df.lastonline.apply(lambda x: datetime.date.fromtimestamp(x).month).astype(str) +
        " (" +
        df.lastonline.apply(lambda x: calendar.month_abbr[datetime.date.fromtimestamp(x).month]).astype(str) +
        ")"
    )

    return df.drop(columns=['permanent_country'])

@app.route("/get-user-info/<member_id>", methods=['GET'])
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
        return "Exception Encountered: supplied 'member_id' is not an integer!"
    except Exception as exc:
        return "Invalid input!"


def split_dataframe(df, chunk_size): 
    chunks = list()
    num_chunks = math.ceil(len(df) / chunk_size)
    for i in range(num_chunks):
        chunks.append(df[i*chunk_size:(i+1)*chunk_size])
    return chunks

def createRecommendationResults(member_id, userData, offset, count, withInfo, timeMix, premiumMix, galleryMix, errors = []):
    timer = Timer()
    timer.start()
    global reducedUsers, encodedUsersOneHot, interest_df, dummyCols

    senderInfo = userData.to_dict(orient='records')[0]
    senderIsFemme = senderInfo['gender'] == 'Female'
    senderGender = ('Female' if senderIsFemme else 'Male')

    oneHotTieredUsers = encodedUsersOneHot[senderGender]
    match_df = oneHotTieredUsers[oneHotTieredUsers.member_id.isin(
        interest_df[interest_df.sender_id == member_id].receiver_id)]
    preferences = match_df.mean(axis=0)

    values = []
    cols = []
    for category in [x for x in dummyCols if x != 'permanent_city']:
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

    scores = pd.Series()
    for u_df in split_dataframe(oneHotTieredUsers, 1_00_000):
        scores = pd.concat([scores, oneHotTieredUsers[vector.index].dot(vector)])
    scores.reset_index(inplace=True, drop=True)
    # scores = oneHotTieredUsers[vector.index].dot(vector)
    scores += oneHotTieredUsers.age.between(
        ageLowerBound, ageUpperBound).astype(float) * 2
    
    timer.check('Calculating base score')

    scoredUsers = pd.DataFrame(
        {'member_id': oneHotTieredUsers.member_id, 'score': scores})

    predictions = pd.merge(
        scoredUsers[['member_id', 'score']].sparse.to_dense(),
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
    return {
        # 'error': errors,
        # 'user': senderInfo,
        'userInterestCount': match_df.shape[0],
        'percentageResultsPremium' : percentageRecommendationsPremium,
        'percentageResultsHaveGallery' : percentageRecommendationsGallery,
        'userRecommendations': predictions[predictions.columns if withInfo else ['member_id', 'score']].to_dict(orient='records'),
        # 'timeframeCounts' : predictions.monthYear.value_counts().to_dict()
    }

@app.route("/recommendation", methods=['POST'])
def recommendation():
    global logger
    timer = Timer()		
    timer.start()
    errors = []
    timer.check('Fetching data')
    
    member_id = None
    try:
        member_id = int(request.form['member_id'])
    except ValueError as verr:
        return "Recommendation: Exception Encountered: supplied 'member_id' is not an integer!", 400
    except Exception as exc:
        return "Recommendation: Invalid input!", 400

    formUserData = json.loads(request.form['userData'])
    userData = None
 
    try:
        userData = prepareUserFormData(member_id=member_id, userData=formUserData)
    except Exception as e:
        logger.error(e)
        return f'Recommendation: Error: {e}\n{json.dumps(formUserData)}', 400

    # return f'userdata: {userData.to_dict(orient="records")[0]}\nreceiveddata: {formUserData}'
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
    if (userData.status == 1).sum():
        #only add if user is approved
        addUpdation(userData)

    gc.collect()
    return createRecommendationResults(member_id=member_id, userData=userData, errors=errors, **controlParams)
 

def setUserStatus(status):
    member_id = None
    try:
        member_id = int(request.form['member_id'])
    except ValueError as verr:
        return "Recommendation: Exception Encountered: supplied 'member_id' is not an integer!", 400
    except Exception as exc:
        return "Recommendation: Invalid input!", 400
    
        #Not updating in-flight right now since it eats up memory, the updates will take place after the refresh data script
    # global reducedUsers, encodedUsersOneHot
    # if (reducedUsers.member_id == member_id).sum() == 0:
    #     return "member_id not in data!", 400
    # idx = (reducedUsers.member_id == member_id)
    # reducedUsers.loc[idx, 'status'] = status
    # reducedUsers.loc[idx, 'lastonline'] = int(datetime.datetime.now().timestamp())

    # encodedUsersOneHot = {}
    # gc.collect()
    # encodedUsersOneHot = getEncodedUsers()

    addUpdation(reducedUsers[reducedUsers.member_id == member_id])
    return {}, 200

@app.route('/deactivate', methods=['POST'])
def deactivate():
    return setUserStatus(status=0);
 
@app.route('/activate', methods=['POST'])
def activate():
    return setUserStatus(status=1);

@app.route('/', methods=['GET'])
def home():
    return """
    <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Hello, world!</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="description" content="" />
  <link rel="icon" href="favicon.png">
</head>
<body>
  <h1>nf-recommendation api!</h1>
  <h2>endpoints:</h2>
  <h3>/test_recommendation [POST]</h3>
  <h3>/past-interests/"member_id" [GET]</h3>
</body>
</html>
    """