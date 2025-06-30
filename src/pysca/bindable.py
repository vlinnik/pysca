from typing import Any
from .__logging import console

_log = console('bindable')

class Converter():
    """Преобразование значений прямое и обратное. Property использует для преобразования из iec и обратно
    """
    def __init__(self):
        pass
    def raw2eu(self,raw: Any, property:'Property'=None):
        return raw
    def eu2raw(self,eu: Any, property: 'Property'=None):
        return eu

class Property():
    TYPE_ANY = 0
    TYPE_BOOL = 1
    TYPE_FLOAT = 2
    TYPE_STR = 3
    TYPE_INT = 4
    TYPE_LONG = 8
    """Хранение значения, с механизмом привязки к его изменениям.
    
    Значение может быть результатом функции. Контролируются изменения с помощью Property.write.
    """
    def __init__(self,init_val=None,read:callable=None, write: callable=None,iec_val=None):
        """Новое контролируемое значение(свойство).

        Args:
            init_val (Any, optional): Начальное значение. Фиксирует тип. Можно использовать типы, например init_val = bool. Defaults to None.
            read (callable, optional): Значение свойства=результат вызова функции read(). Defaults to None.
            write (callable, optional): Для изменения свойства используется функция write(<новое значение>). Defaults to None.
            iec_val (type|Any,optional): Тип переменной в физическом представлении. Например аналоговые сигналы обычно 16 бит-слово.
        """
        self.filter:Converter = None  #обработка значения (если необходима)
        self.__binds = []
        if isinstance(init_val,type):
            self._value = init_val( )
        else:
            self._value = init_val
        if isinstance(iec_val,type):
            self._iec = iec_val( )
        else:
            self._iec = iec_val
        self._read = read
        self._write = write
        self._iec_write:callable = None
        self.name: str = None
        self.source:str = None
        self.address:str = None
        self.properties:dict = None
        self.type = Property.TYPE_ANY    #< тип переменной (код, например 2 - float)

    def config(self, attr: dict = {}):
        try:
            for a in attr:
                setattr(self, a, attr[a])
        except AttributeError as e:
            pass

    def bind(self,__sink:callable,no_init:bool=False):  
        """Установить callback при изменении контролируемого значения. 

        Args:
            __sink (callable): при изменении контролируемого значения будет вызвана __sink(<новое значение>)
            no_init (bool, optional): надо или нет вызвать __sink с текущим значением. Defaults to False (надо).
        """
        self.__binds.append( __sink )
        if not no_init:
            __sink(self.read())

    def unbind(self,__sink: callable = None):
        """Удалить конкретный callback или все.

        Args:
            __sink (callable, optional): Если None, все будут удалены. Defaults to None.
        """
        self.__binds = list(filter( lambda x: not (x==__sink or __sink is None),self.__binds ) )

    def read(self)->Any:
        """Прочитать текущее значение.

        Returns:
            Any: текущее значение.
        """
        if self._read:
            self._value = self._read( )
        return self._value

    def write(self,value: Any,remote:bool=False):
        """Изменить текущее значение.

        Args:
            value (Any): Тип должен быть преобразуем к типу текущего значения.
            remote(bool): Если значение получено из-вне(запись через self.remote(...)) = True

        Raises:
            RuntimeWarning: Если value нельзя преобразовать к текущему типу Property.read()
        """
        if self._value!=value:
            if type(self._value)!=type(value) and self._value is not None and value is not None:
                try:
                    self._value = type(self._value)(value)
                except:
                    raise RuntimeWarning(f'cannot convert new value "{value}" to {type(self._value).__name__}')
            else:
                self._value = value
            if self._write:
                self._write(self._value)
            for b in self.__binds:
                try:
                    b(self._value)
                except Exception as e:
                    if self._value is not None: _log.warning(f'проблема при изменении значения {self.name}: {e}')
                
        if self._iec_write and not remote:
            self._iec_write(self.raw)

    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self.read()

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, self._value )

    def iec(self)->Any:
        if self.filter:
            try:
                return self.filter.eu2raw(self.read( ),what=self)
            except Exception as e:
                return self.read( )
        
        return self._value
    
    def changed(self,callback: callable):
        self._iec_write = callback

    def remote(self,iec_val: Any):
        if type(self._iec)!=type(iec_val) and self._iec is not None and iec_val is not None:
            try:
                self._iec = type(self._iec)(iec_val)
            except:
                raise RuntimeWarning(f'cannot convert new value "{iec_val}" to {type(self._iec).__name__}')
        else:
            self._iec = iec_val
        #теперь необходимо преобразовать iec в value
        if self.filter: 
            try:
                self.write( self.filter.raw2eu(self._iec,what=self),remote=True)
            except Exception as e:
                _log.warning( f'проблема в raw2eu {self.name}: {e}' )
                self.write( self._iec ,remote=True)
        else:
            self.write( self._iec,remote = True )
                
    value = property(read,write)
    raw = property(iec,remote)

class Expressions(dict):
    class Expression(Property,dict):
        def __init__(self, ctx, source: str, locals = None) -> None:
            super().__init__( )
            self.value = None
            self.ctx = ctx
            self.source = source
            self.locals = locals
            self.crossreferences = []

        def isDependsOn(self,key:str):
            return key in self.crossreferences
        
        def reference( self, key: str, prop: Property):
            self.crossreferences.append(key)
            prop.bind(self.evaluate,True)

        def evaluate(self,*_):
            ret = eval( self.source, self )
            self.write( ret )
            return ret
        
        def __getitem__(self, __key):
            if self.locals and __key in self.locals:
                return self.locals[__key]
            
            if __key not in self.ctx:
                raise KeyError(__key)
            prop = self.ctx [__key]
            if isinstance(prop,Property):
                if not self.isDependsOn(__key):
                        self.reference(__key,prop)
                return prop.read( )
                
            return self.ctx[__key]
        
        def __repr__(self):
            return '%s(%s)=%s' % (type(self).__name__, self.source ,self.value)
        
    def __init__(self):
        dict.__init__(self)
    
    def __setitem__(self, __key, __value) -> None:
        if __key in self.keys():
            dict.__getitem__(self,__key).write(__value)
        elif isinstance(__value,Property):
            dict.__setitem__(self,__key,__value)
        else:
            raise ValueError('Only for class Property-instances',__value)
        
    def __setattr__(self, name, value):
        if name in self:
            self.__setitem__(name,value)
            
        return super().__setattr__(name, value)

    def __getattribute__(self, name):
        if name in self:
            return self.__getitem__(name).read()
        
        return super().__getattribute__(name)
        
    def create(self,source: str,locals: dict = None):
        ret = self.Expression( self, source, locals = locals )
        ret.evaluate(  )
        return ret
