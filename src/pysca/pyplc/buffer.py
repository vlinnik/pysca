from io import IOBase
import sys,errno,socket

class Buffer(IOBase):
    @staticmethod
    def attention(e: Exception,hint: str=''):
        if hasattr(sys,'print_exception'): 
            print(f'Attention: {e}({hint})',end=':')
            sys.print_exception(e)
        else:
            print(f'Attention: {e}({hint})')
                
    def __init__(self,size: int = 1024):
        self.__size = size
        self.__data = bytearray(size)
        self.view = memoryview(self.__data)
        self.end = 0

    def close(self):
        del self.view
        del self.__data
        self.__data = None
        self.view = None
        self.end = 0

    def size(self):
        return self.end

    def purge(self,size:int=0):
        if size>=self.end or size==0:
            self.end = 0
        else:
            self.view[0:self.end-size] = self.view[size:self.end]
            self.end -= size
    
    def readinto(self,data):
        size = len(data) if len(data)<self.size( ) else self.size( )
        data[:size]=self.view[:size]
        self.purge(size)
        return size
    
    def data(self,max: int=0):
        if max==0:
            return self.view[self.end:]
        return self.view[self.end:self.end+max]
    
    def tail(self,size: int=0 ):
        if size>0:
            return self.view[self.end-size:self.end]
        return self.view[:self.end+size]
    
    def head(self,size: int = 0 ):
        if size>0:
            return self.view[:size]
        return self.view[-size:self.end]
    
    def mid(self,start:int=0,end:int=0,size:int=0):
        if start<0:
            start=self.end+start
        if end<=0:
            end=self.end+end
        if size>0:
            end=start+size
        return self.view[start:end]
    
    def grow(self,size:int):
        self.end+=size
        
    def put(self,data:memoryview, off: int=0):
        end = self.end+len(data)
        self.view[self.end-off:end-off] = data
        if off==0:
            self.grow(len(data))
            
    def pop(self,off:int =0):
        if off>0:
            self.view[self.end-off-1:self.end-1] = self.view[self.end-off:self.end]
        self.end-=1

class BufferOut(Buffer):
    def __init__(self,send: callable,size: int = 1024):
        super().__init__(size)
        self.__send = send
        self.write = send
                    
    def flush(self)->int:
        try:
            sent = self.size()
            if sent==0:
                return 0;
            self.__send( self.head( ) )
            self.purge(sent)
            return sent
        except OSError as e:
            if e.errno==errno.EAGAIN: return 0
            if e.errno==errno.EWOULDBLOCK: return 0
            return -1

    def putc(self,c:int,off:int=0,echo:bool = False):
        self.view[self.end-off:self.end-off+1]=c.to_bytes(1,'little')
        if echo:
            self.__send(self.view[self.end-off:self.end-off+1])
        if off==0:
            self.grow(1)
    
class BufferIn(Buffer):
    def __init__(self,readinto: callable,size: int = 1024):
        super().__init__(size)
        self.__recv = readinto
                    
    def read(self):
        try:
            size = self.__recv( self.data() )
            if size is not None:
                if size==0:
                    return -1
                self.grow(size)
                return size
            return 0
        except OSError as e:
            if e.errno==11: return 0
            if e.errno==35: return 0
            self.attention(e,'TCPServer::BufferIn::read')
            return -1
        except Exception as e:
            self.attention(e,'TCPServer::BufferIn::read')
        
        return -1   #fatal socket error

class BufferInOut(IOBase):
    def __init__(self,client: socket.socket , i_size: int = 1024, o_size: int=1024 ):
        """Конструктор буфферезированного ввода/вывода в socket

        Args:
            client (socket.socket): socket 
            i_size (int, optional): размер буфера in. Defaults to 1024.
            o_size (int, optional): размер буфера out. Defaults to 1024.
        """        
        self.client = client
        self.rx = BufferIn( client.readinto if hasattr(client,'readinto') else client.recv_into , size = i_size )
        self.tx = BufferOut( client.send , size=o_size  )
    
    def close(self):
        self.tx.close( )
        self.rx.close( )
        self.client.close( )
                        
    def read( self ):
        return self.rx.read( )
    
    def send( self, data ):
        self.tx.put( data )
        
    def fileno(self)->int:
        return self.client.fileno( )
