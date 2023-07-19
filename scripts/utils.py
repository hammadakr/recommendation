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

    
from filelock import FileLock

def performWithFileLock(filepath : str, action : callable):
    lock = FileLock(filepath + '.lock')
    with lock:
        return action()