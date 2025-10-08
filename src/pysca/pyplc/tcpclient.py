import socket,sys
import errno,select
from .buffer import BufferInOut

"""
TCP клиент с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Chat клиент. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    client = TCPClient(9003) #запуск echo сервера на 9003 порте
    while True:
        client()             #логика работы сервера. 
"""
class TCPClient():
    TRY_LIMIT = 20
    @staticmethod
    def attention(e: Exception,hint: str=''):
        if hasattr(sys,'print_exception'): 
            print(f'Attention: {e}({hint})',end=':')
            sys.print_exception(e)
        else:
            print(f'Attention: {e}({hint})')
    
    def __init__(self,host: str, port:int ,i_size:int=256,o_size:int=256):
        """Инициализация и запуск клиента по указанному порту

        Args:
            port (int): номер порта
            b_size (int, optional): Максимальный размер получаемого пакета. Defaults to 256.
        """
        self.host = host
        self.port = port
        self.i_size = i_size
        self.o_size = o_size
        self.buf = bytearray()
        self.sock = None
        self._sock = None # на время установки соединения 
        self._tries = TCPClient.TRY_LIMIT

    def connected(self):
        print(f'Connected to {self.host}:{self.port}')

    def disconnected(self):
        print(f'Disconnected from {self.host}:{self.port}')

    def received(self,data:memoryview):
        self.send( data )
        return len(data)
        
    def routine(self):
        pass

    def send(self,data:memoryview):
        if self.sock:
            self.sock.tx.put(data)

    def connect(self):
        if self._sock:
            events = self._poll.poll(0)
            if events:
                sock = self._sock
                del self._poll
                self._poll = None
                self._sock = None
                if (events[0][1] & (select.POLLIN | select.POLLOUT))!=0:
                    sock.settimeout(0)
                    self.sock = BufferInOut(sock,i_size=self.i_size,o_size=self.o_size)
                    self.connected()
                    return
                else:
                    sock.close()
            else:
                return
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(6, 1, 1)    #IP_PROTOTCP,TCP_NODELAY, only on pc
            sock.setblocking(False)
            sock.connect((self.host, self.port))
        except OSError as e:
            if e.errno==errno.EINPROGRESS:
                self._sock = sock
                self._poll = select.poll()
                self._poll.register(sock,select.POLLIN | select.POLLOUT)
            else:
                sock.close( )
        except Exception as e:
            sock.close()
            
    def close(self):
        if self.sock is None:
            return
        self.disconnected()
        self.sock.close()
        self.sock = None

    def __call__(self,**kwds):
        sock = self.sock
        if self.sock is None:
            self.connect( )
            return
            
        try:
            if sock.read( ) == -1:
                if self._tries>0:
                    self._tries-=1
                else:
                    self.close()
                return
            else:
                self._tries = TCPClient.TRY_LIMIT
            
            if sock.rx.size()!=0:
                last_processed = processed = self.received( sock.rx.head( ) )
                if processed>0:
                    while last_processed>0 and sock.rx.size()>processed:
                        last_processed=self.received(sock.rx.head(-processed))
                        processed += last_processed
                    sock.rx.purge(processed)
        except OSError as e:
            pass                    
        except Exception as e:
            self.attention(e,'TCPClient')
            self.close()
        finally:
            if self.sock is None: 
                return
            
        try:
            self.routine()
        except Exception as e:
            self.attention(e,'TCPClient::routine')
            self.close() 
            
        sock.tx.flush( )
