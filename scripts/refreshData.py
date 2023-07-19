import pandas as pd
from utils import performWithFileLock

def updateUsers():
    USER_URI = '../userExport.feather'
    UPDATES_URI = '../userUpdation.csv'
    
    users = performWithFileLock(USER_URI, lambda : pd.read_feather(USER_URI))

    def readAndClearUpdates():
        read = pd.read_csv(UPDATES_URI)
        pd.DataFrame(columns=read.columns).to_csv(UPDATES_URI, index=False)
        return read

    randomUsers = performWithFileLock(UPDATES_URI, readAndClearUpdates)
    randomUsers = randomUsers.sort_values('lastonline', ascending=False).drop_duplicates(['member_id'])

    idx = randomUsers.member_id.isin(users.member_id) & (randomUsers.status == 1)
    deleted_member_ids = randomUsers[randomUsers.status == 0].member_id
    randomNewUsers = randomUsers[~idx]
    randomChangedUsers = randomUsers[idx]
    users.set_index('member_id', inplace=True)
    users.update(randomChangedUsers.set_index('member_id'))
    users.reset_index(inplace=True)

    users = pd.concat([users[~users.member_id.isin(deleted_member_ids)], randomNewUsers]).reset_index()

    # print(randomChangedUsers)
    # print(randomNewUsers)
    performWithFileLock(USER_URI, lambda: users.to_feather(USER_URI))

def updateInterest():
    pass

if __name__ == '__main__':
    #todo save updation timestamp
    updateUsers()
    updateInterest()
