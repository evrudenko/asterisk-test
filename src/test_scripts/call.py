import socket
import time

def originate_call():
    s = socket.socket()
    s.connect(('localhost', 5038))

    # Авторизация
    s.send(b'Action: Login\r\nUsername: admin\r\nSecret: mypassword\r\n\r\n')
    time.sleep(0.2)

    # SIP-вызов (вызываем SIP/1001)
    s.send(b'''
Action: Originate
Channel: SIP/1001
Context: default
Exten: 1001
Priority: 1
CallerID: Python <1000>
Timeout: 30000
\r\n''')
    time.sleep(0.5)

    # Завершаем сессию
    s.send(b'Action: Logoff\r\n\r\n')

    # Читаем ответ
    print(s.recv(4096).decode())
    s.close()

originate_call()
