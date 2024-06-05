class Logger:
    def recv(self: 'Logger', value: str) -> None:
        pass

    def send(self: 'Logger', value: str) -> None:
        pass

    def log(self: 'Logger', value: str):
        pass

    def error(self: 'Logger', value: str):
        pass

    def event(self: 'Logger', value: str):
        pass

class LoggerPrint (Logger):
    def recv(self: 'LoggerPrint', value: str):
        print('RECV: \33[94m' + value + '\033[0m')

    def send(self: 'LoggerPrint', value: str):
        print('SEND: \33[95m' + value + '\033[0m')

    def log(self: 'LoggerPrint', value: str):
        print('Log: \33[93m' + value + '\033[0m')

    def error(self: 'LoggerPrint', value: str):
        print('Error: \33[91m' + value + '\033[0m')

    def event(self: 'LoggerPrint', value: str):
        print('Event: \33[92m' + value + '\033[0m')

if __name__ == '__main__':
    l = LoggerPrint()

    l.log("azeerty")
    l.recv('fsfgd')
    l.send('zgsdf')
    l.error('sfdf')
    l.event('regdfbd')

    l2 = Logger()
    l2.log('rsdv')
