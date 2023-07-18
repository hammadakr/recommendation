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

class Timer: 
    def __init__(self) -> None:
        self.timeStack = []
    def start(self):
        self.timeStack.append( (time.time(), 'start') )
    def check(self, name : str = ''):
        self.timeStack.append( (time.time(), name if name else f'check no. {len(self.timeStack)}') )
    def log(self):
        print('Start')
        for (t0, name0), (t1, name1) in zip(self.timeStack, self.timeStack[1::]):
            print(f'{name1} took  {(t1 - t0)*1000} ms')
        print('End')
        total = (self.timeStack[-1][0] - self.timeStack[0][0]) * 1000
        print(f'Total Time: {total} ms')
    def end(self):
        self.timeStack.clear()

def addUpdation(updatedUser : pd.DataFrame) -> None:
    updationURI = 'userUpdation.csv'
    updatedUser.to_csv(updationURI, mode='a', index=False, header=False)

def getReducedUsers():
    print('running reduced users')
    reducedUsers = pd.read_feather('userExport.feather')
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

reducedUsers = getReducedUsers()

dummyCols = ['marital_status', 'permanent_state', 'highest_education',
             'occupation', 'caste', 'sect', 'employed', 'income', 'permanent_city']

def buildNanMap():
    global reducedUsers
    return dict(zip(dummyCols, [[f'{y}_{x}' for x in reducedUsers[y].astype(str).unique() if (x.endswith('nan'))] for y in dummyCols]))

nanMap = buildNanMap()

def getEncodedUsers():
    global dummyCols, nanMap, reducedUsers

    encodedUsersOneHot = {}
    for senderIsFemme in [True, False]:
        tag = ('Female' if senderIsFemme else 'Male')
        temp = reducedUsers[(reducedUsers.gender != (
            'Female' if senderIsFemme else 'Male'))]
        encodedUsersOneHot[tag] = pd.get_dummies(
            temp[['member_id', 'age'] + dummyCols], columns=dummyCols, dummy_na=True)

        for col in dummyCols:
            nanCols = nanMap[col]
            dummiedCols = [
                x for x in encodedUsersOneHot[tag].columns if x.startswith(col)]
            idx = np.sum(encodedUsersOneHot[tag][nanCols].values, axis=1) > 0
            encodedUsersOneHot[tag].loc[idx, nanCols] = 0

        encodedUsersOneHot[tag] = encodedUsersOneHot[tag].astype(
            pd.SparseDtype("int32", 0))
        
    return encodedUsersOneHot

encodedUsersOneHot = getEncodedUsers()

interest_df = pd.read_feather('interestExport.feather')

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
    userFormData = [
        'age', 'gender', 'membership', 'gallery', 'status',
        'marital_status', 'permanent_country', 'permanent_state', 'permanent_city', 'highest_education', 'occupation', 'employed', 'income', 'caste', 'sect'
    ]
    values = [member_id]
    for col in userFormData:
        val = userData[col]
        values.append(val if val is not None else np.nan)

    df = pd.DataFrame([dict(zip(['member_id'] + userFormData, values))])
    df.age = df.age.astype(int)

    df.loc[:, 'permanent_state'] = df.apply(lambda row: 'Foreign' if row.permanent_country != 'India' else row.permanent_state, axis=1)
    global popular_cities
    df.loc[(~df.permanent_city.isin(popular_cities.permanent_city)) & (~df.permanent_city.isna()), 'permanent_city'] = 'Others'
    
    df['gallery'] = df.gallery == 'Yes'
    df['status'] = df.status == 'Approved'

    df['lastonline'] = int(datetime.datetime.now().timestamp())
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


@app.route("/recommendation", methods=['POST'])
def recommendation():
    timer = Timer()
    timer.start()
    errors = []
    global reducedUsers, encodedUsersOneHot, interest_df
    timer.check('Fetching data')

    member_id = None
    try:
        member_id = int(request.form['member_id'])
    except ValueError as verr:
        return "Exception Encountered: supplied 'member_id' is not an integer!"
    except Exception as exc:
        return "Invalid input!"

    formUserData = json.loads(request.form['userData'])
    userData = prepareUserFormData(member_id=member_id, userData=formUserData)

    offset = 0
    try:
        offset = int(request.form['offset'])
    except:
        errors.append(f'Error: invalid offset using default values {offset}')

    count = 50
    try:
        count = int(request.form['count'])
    except:
        errors.append(f'Error: invalid count using default values {count}')

    withInfo = False
    try:
        withInfo = bool(request.form['withInfo'])
    except:
        errors.append(
            f'Error: invalid withInfo using default values {withInfo}')
        
    timeMix = 0.25
    try:
        timeMix = float(request.form['timeMix'])
    except:
        errors.append(
            f'Error: invalid timeMix using default values {timeMix}')
    
    premiumMix = 0.05
    try:
        premiumMix = float(request.form['premiumMix'])
    except:
        errors.append(
            f'Error: invalid premiumMix using default values {premiumMix}')

    galleryMix = 0.01
    try:
        galleryMix = float(request.form['galleryMix'])
    except:
        errors.append(
            f'Error: invalid galleryMix using default values {galleryMix}')

    if (reducedUsers.member_id == member_id).sum() == 0:
        pass
        # changedUsers = pd.concat([changedUsers, userData.drop(columns=['lastActiveDate', 'monthYear'])])
    else:
        pass
        # print('comparision:')
        # print(userData)
        # print(reducedUsers[reducedUsers.member_id == member_id])
        # print(np.equal(userData.values[0], reducedUsers[reducedUsers.member_id == member_id][userData.columns].values[0]))        
        # changedUsers = pd.concat([changedUsers, userData.drop(columns=['lastActiveDate', 'monthYear'])])
    addUpdation(userData.drop(columns=['lastActiveDate', 'monthYear']))

    timer.check('Input processing')

    senderInfo = userData.to_dict(orient='records')[0]
    senderIsFemme = senderInfo['gender'] == 'Female'
    senderGender = ('Female' if senderIsFemme else 'Male')

    oneHotTieredUsers = encodedUsersOneHot[senderGender]
    match_df = oneHotTieredUsers[oneHotTieredUsers.member_id.isin(
        interest_df[interest_df.sender_id == member_id].receiver_id)]
    preferences = match_df.mean(axis=0)

    values = []
    cols = []
    for category in ['marital_status', 'permanent_state', 'highest_education', 'occupation', 'caste', 'sect', 'employed']:
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
    # ageLowerBound, ageUpperBound = (match_df.age.quantile(q=0.4), match_df.age.quantile(q=0.6))
    scores = oneHotTieredUsers[vector.index].dot(vector)
    # scores -= (oneHotTieredUsers.age - preferences.age).abs()
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
    yesGallery = predictions.gallery == 'Yes'
    #reordering final predictions
    
    predictions.score *= (1 - premiumMix) + premiumMemberships * premiumMix
    predictions.score *= (1 - galleryMix) + yesGallery * galleryMix

    predictions.insert(1, 'already_liked', predictions.member_id.isin(match_df.member_id))
    percentageRecommendationsPremium = round(100 * premiumMemberships.sum() / predictions.shape[0])
    percentageRecommendationsGallery = round(100 * yesGallery.sum() / predictions.shape[0])
    
    predictions.sort_values(by='score', inplace=True, ascending=False)
    timer.check('Calculating final metrics')
    # timer.log()
    timer.end() 
    gc.collect()
    return {
        'ci/cd' : 'success! 5 time',
        'error': errors,
        'user': senderInfo,
        'userInterestCount': match_df.shape[0],
        'percentageResultsPremium' : percentageRecommendationsPremium,
        'percentageResultsHaveGallery' : percentageRecommendationsGallery,
        'userRecommendations': predictions[predictions.columns if withInfo else ['member_id', 'score']].to_dict(orient='records'),
        'timeframeCounts' : predictions.monthYear.value_counts().to_dict()
    }

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