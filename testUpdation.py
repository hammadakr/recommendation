import pandas as pd
import time

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

timer = Timer()
timer.start()
users = pd.read_feather('userExport.feather')
timer.check(f'read users of shape {users.shape}')
interests = pd.read_feather('interestExport.feather')
timer.check(f'read interest of shape {interests.shape}')
timer.log()
timer.end()

randomChangedUsers = users.sample(10_000)
randomNewUsers = users.sample(10_000)
randomNewUsers.member_id += 10_00_000
randomUsers = pd.concat([randomChangedUsers, randomNewUsers])

timer.start()

idx = randomUsers.member_id.isin(users.member_id) & (randomUsers.status == 1)
deleted_member_ids = randomUsers[randomUsers.status == 0].member_id
randomNewUsers = randomUsers[~idx]
randomChangedUsers = randomUsers[idx]
users.set_index('member_id', inplace=True)
users.update(randomChangedUsers.set_index('member_id'))
users.reset_index(inplace=True)
timer.check('updating existing users')

users = pd.concat([users[~users.member_id.isin(deleted_member_ids)], randomNewUsers]).reset_index()

timer.check('added new users')

users.to_feather('fakeUsersExport.feather')
timer.check('exporting new user feather file')

timer.log()



timer.end()