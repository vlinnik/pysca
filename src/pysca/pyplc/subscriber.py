from .tcpclient import TCPClient
from .bindable import Property
import time
import struct

class Subscription(Property):
    next_id = 0
    """Подписка на данные python-программы 
    """

    def __init__(self, item: str):
        """Создание подписки
        Args:
            item (str): Идентификатор подписки
        """
        super().__init__()
        self.item = item            # идентификатор подписки: например motor.ison
        self.modified = False       # флаг что есть изменения и надо отправить удаленной стороне
        self.remote_id = None       # номер подписки на удаленной стороне
        self.filed = False          # флаг что подписка оформлена
        self.local_id = Subscription.next_id    # номер подписки на этой стороне
        self.tx = 0                 #сколько раз отправлено
        self.rx = 0                 #сколько раз получено
        Subscription.next_id += 1

    def __str__(self) -> str:
        return f'{self.item}({self.local_id}) = {self.read()}'

    def cleanup(self):
        self.__sinks.clear( )

    def write(self, value):  # modify current value for underlying subscription's item
        if self.read()!=value:
            self.modified = True     #нужно отправить удаленной стороне
        super().write(value)

    # subscribed item changed on remote side
    def remote(self, value):
        """Значение изменено где-то на другом конце (у клиента)

        Args:
            value (Any): новое значение
        """
        if not self.modified:
            self.write(value)     # произведем
            self.modified = False # не надо отправлять на удаленную сторону
        else:
            pass    #отклоняем, тк. есть локальные изменения
        self.rx +=1            

class Subscriber(TCPClient):
    def __init__(self, host, port=9004,i_size:int=512,o_size:int=1024):
        self.items = {}
        self.unsubscribed = []
        self.subscriptions = {}
        self.keepalive = time.time_ns()
        self.online = False
        self.stat = [None]*3
        super().__init__( host,port, i_size=i_size,o_size=o_size )

    def connected(self):
        pass

    def disconnected(self):
        self.online = False
        for i in self.subscriptions:
            s = self.subscriptions[i]
            s.remote(None)
            s.remote_id = None
            s.filed = False
            if s.local_id not in self.unsubscribed:
                self.unsubscribed.append(s.local_id)

    def subscribe(self, item: str, local_id: str = None):
        s = Subscription(item)
        self.subscriptions[s.local_id] = s
        if local_id is None:    #локальное имя не должно содержать .
            hidden = True
            path = item.split('.')
            if len(path) > 1:
                local_id = '.'.join(path[1:])
            else:
                local_id = item
            local_id.replace('.', '_')
        else:
            hidden = False
        self.items[local_id] = s.local_id
        self.unsubscribed.append(s.local_id)
        if not hidden: setattr(self.__class__, local_id, s)
        return s

    def received(self, data: memoryview):
        if len(data) < 8:
            return 0
        cmd, size = struct.unpack('ii', data[:8])
        if size+8 > len(data):
            return 0
        size += 8
        off = 8
        if cmd == 0:  # subscribe response
            while off < size:
                local_id, remote_id = struct.unpack_from('!HH', data, off)
                off += struct.calcsize('!HH')
                if local_id in self.subscriptions:
                    s = self.subscriptions[local_id]
                    s.remote_id = remote_id
                    s.filed = False
                    if local_id in self.unsubscribed:
                        self.unsubscribed.remove(local_id)
                    s.remote(None)
            if len(self.unsubscribed) == 0:
                self.online = True
            return off
        elif cmd == 2:  # data changed
            HBH = struct.calcsize('!HBH')
            while off+HBH <= size:
                value = None
                local_id, type_id, d_size = struct.unpack_from(
                    '!HBH', data, off)
                off += HBH
                if type_id == 0 and off+1 <= size:  # bool
                    value, = struct.unpack_from('!b', data, off)
                    value = value != 0
                elif type_id == 1 and off+8 <= size:  # int
                    value, = struct.unpack_from('!q', data, off)
                elif type_id == 2 and off+8 <= size:  # double
                    value, = struct.unpack_from('!d', data, off)
                elif type_id == 3 and off+d_size <= size:  # string
                    value, = struct.unpack_from(f'{d_size}s', data, off)
                    value = str(value,'utf-8')

                off += d_size
                if local_id in self.subscriptions and value is not None:
                    s = self.subscriptions[local_id]
                    s.remote(value)
        elif cmd == 3:  # keepalive
            payload = self.sock.tx.data()
            if size < 24:
                struct.pack_into('ii', payload, 0, 3, size)
                payload[8:size] = data[8:size]
                struct.pack_into('q', payload, size, time.time_ns())
                self.sock.tx.grow(8+size)
            else:
                # ts_0 - мы посылали ts_1 - нам в ответ когда отправили ts_2 - мы снова туда отправили ts_3 - нам в ответ
                ts_0,  = struct.unpack_from('q', data, off)
                ts_2 = time.time_ns()
                self.stat = [(ts_2-ts_0) >> 1]

        return size

    def routine(self):
        if len(self.unsubscribed) > 0:
            payload = self.sock.tx.data()
            filed = []
            end = 8
            for i in self.unsubscribed:
                if end > self.o_size/2:
                    break
                s = self.subscriptions[i]
                if s.filed:
                    continue
                struct.pack_into(f'!HH{len(s.item)}s', payload, end, i, len(
                    s.item), s.item.encode())
                end += struct.calcsize(f'!HH{len(s.item)}s')
                filed.append(s)
            try:
                if len(filed) > 0:
                    struct.pack_into('ii', payload, 0, 0, end-8)
                    self.sock.tx.grow(end)
                for item in filed:
                    item.filed = True
            except:
                pass
        else:
            modified = list(filter(lambda s: s.modified,
                            self.subscriptions.values()))
            if len(modified) > 0:
                payload = self.sock.tx.data()
                end = 8
                for s in modified:
                    value = s()
                    remote_id = s.remote_id
                    if value is None or end > self.o_size-32 or remote_id is None:
                        continue
                    elif type(value) is bool:
                        struct.pack_into('!HBHb', payload, end,
                                         remote_id, 0, 1, value)
                        end += struct.calcsize('!HBHb')
                    elif type(value) is int:
                        struct.pack_into('!HBHq', payload, end,
                                         remote_id, 1, 8, value)
                        end += struct.calcsize('!HBHq')
                    elif type(value) is float:
                        struct.pack_into('!HBHd', payload, end,
                                         remote_id, 2, 8, value)
                        end += struct.calcsize('!HBHd')
                    elif type(value) is str:
                        struct.pack_into('!HBHs', payload, end,
                                         remote_id, 3, len(value), value)
                        end += struct.calcsize('!HBHs')
                    s.modified = False

                if end > 8:
                    struct.pack_into('ii', payload, 0, 2, end-8)
                    self.sock.tx.grow(end)
            else:
                payload = self.sock.tx.data()
                if time.time_ns() > self.keepalive+1000000000:
                    struct.pack_into('iiq', payload, 0, 3, 8,
                                     time.time_ns())  # keep alive
                    self.sock.tx.grow(16)
                    self.keepalive = time.time_ns()
