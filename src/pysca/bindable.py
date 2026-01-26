from types import NoneType
from typing import Any,Type,cast
from .__logging import console
from .monitor import Monitor

_log = console('bindable')

class Filter():
    """Преобразование значений прямое и обратное. 
    Property использует для преобразования из iec(получено новое значение) и обратно (надо отправить новое значение)
    """
    def __init__(self,*,what: 'Property|None' = None, next: 'Filter|None' = None):
        super().__init__( )
        self._next: 'Filter|None' = next
        self._prop: 'Property|None' = what
        
    def raw2eu(self,raw: Any):
        if self._next is not None:
            return self._next.raw2eu(raw)
        return raw
    def eu2raw(self,eu: Any):
        if self._next is not None:
            return self._next.eu2raw(eu)
        return eu
    def __setattr__(self, name: str, value: Any) -> None:
        try:
            super().__setattr__(name,value)
        except AttributeError as e:
            if self._next is not None: 
                setattr(self._next,name,value)
            else:
                pass
    def config(self, attr: str, value: Any):
        if hasattr(self,attr):
            setattr(self, attr, value)
        elif self._next:
            self._next.config(attr,value)

from typing import TypeVar, Generic, Callable, Union,List
T = TypeVar('T', str, bool, float, int)
            
class Property(Generic[T]):
    """ Переменная I/O или обычная. Хранит 2 значения: физическое (iec) и логическое (value).
    
    changed - настроить callback, для записи в контроллер (iec значение). Для драйверов
    write - изменить переменную. если remote != True, то вызовет changed (передать в драйвер)
    read - прочитать логическое значение.
    bind - установить callback, который будет вызван при изменении значения.(логического)
    """
    TYPE_ANY = 0
    TYPE_BOOL = 1
    TYPE_FLOAT = 2
    TYPE_STR = 3
    TYPE_INT = 4
    TYPE_LONG = 8
    """Хранение значения, с механизмом привязки к его изменениям.
    
    Значение может быть результатом функции. Контролируются изменения с помощью Property.write.
    """
    def __init__(self,t: Type[T],*_,init_val:Union[T,None]=None,read:Union[Callable[[],T | None],None]=None, write: Callable[[T|None],None]|None=None):
        """Новое контролируемое значение(свойство).

        Args:
            init_val (Any, optional): Начальное значение. Фиксирует тип. Можно использовать типы, например init_val = bool. Defaults to None.
            read (callable, optional): Значение свойства=результат вызова функции read(). Defaults to None.
            write (callable, optional): Для изменения свойства используется функция write(<новое значение>). Defaults to None.
            iec_val (type|Any,optional): Тип переменной в физическом представлении. Например аналоговые сигналы обычно 16 бит-слово.
        """
        self._filter:Filter|None = None  #обработка значения (если необходима)
        self.__binds = []
        self._eu_type = t   #< тип переменной в представлении с нашей стороны (для преобразований при записи)
        self._value: Union[T,None] = init_val or t()
        self._iec: Any = None
        self._read = read
        self._write = write
        self._iec_write:Callable[[Any],None]|None = None
        self._monitors: List[Monitor] = [ ]
        self._good: bool = True
        self._good_changed: List[Callable[[bool],None]] = []
        self.name: str|None = None
        self.source:str|None = None
        self.address:str|None = None
        self.properties:dict|None = None
        self.comment: str|None = None
        self.type = Property.TYPE_ANY    #< тип переменной (код, например 2 - float)

    def config(self, attr: dict = {}):
        try:
            for a in attr:
                if hasattr(self,a):
                    setattr(self, a, attr[a])
                elif self.filter:
                    self.filter.config(a,attr[a])
        except AttributeError as e:
            pass
    
    #Переменная имеет осознанное значение
    @property
    def good(self)->bool:
        return self._good
    
    @good.setter
    def good(self,good: bool):
        if self._good==good:
            return
        self._good = good
        for f in self._good_changed:
            f(good)
        
    def on_good_changed(self,callback:Callable[[bool],None],*_,remove: bool = False):
        if not remove:
            callback(self.good)
            self._good_changed.append(callback)
        else:
            self._good_changed = list(filter( lambda x: id(x)==id(callback), self._good_changed ))
        pass
        
    @property
    def monitor(self)->None:
        raise RuntimeWarning('.monitor is write-only property')
    
    @monitor.setter
    def monitor(self,obj: Monitor ):
        """Установить мониторинг значений. Мониторинг при любом изменении переменной производит обработку нового значения. 
        Также при обработке есть возможность узнать причину изменения (пользователь или система)

        Args:
            obj (Monitor): Объект, который будет вызван с новым значением и причиной изменения
        """
        self._monitors.append(obj)

    def bind(self,__sink:Callable[[T|None],None],no_init:bool=False):  
        """Установить callback при изменении контролируемого значения. 

        Args:
            __sink (callable): при изменении контролируемого значения будет вызвана __sink(<новое значение>)
            no_init (bool, optional): надо или нет вызвать __sink с текущим значением. Defaults to False (надо).
        """
        self.__binds.append( __sink )
        if not no_init:
            __sink(self.read())

    def unbind(self,__sink: Callable[[T],None]|None = None):
        """Удалить конкретный callback или все.

        Args:
            __sink (callable, optional): Если None, все будут удалены. Defaults to None.
        """
        self.__binds = list(filter( lambda x: not (x==__sink or __sink is None),self.__binds ) )

    def read(self)->Union[T,None]:
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
        if isinstance(value,Property):
            value = cast(Property,value).read()
        if self._value!=value:
            if self._eu_type!=type(value) and value is not None and self._eu_type is not NoneType:
                try:
                    self.good = True
                    self._value = self._eu_type(value)
                except:
                    raise RuntimeWarning(f'cannot convert new value "{value}" to {self._eu_type.__name__}({self.name})')
            else:
                if value is not None: 
                    self.good = True
                    self._value = value 
                else: self.good = False
            if self._write:
                self._write( self._value)
            for b in self.__binds:
                try:
                    b(self._value)
                except Exception as e:
                    if self._value is not None: _log.warning(f'проблема при изменении значения {self.name}: {e}')
            for m in self._monitors:
                try:
                    m(self._value,user=not remote)
                except Exception as e:
                    _log.warning(f'Проблема мониторинга значения: {e}, монитор {m}')
        else:
            self.good = value is not None
                    
        if self._iec_write and not remote:
            self._iec_write(self.raw)

    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self.read()

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, self._value)

    def iec(self)->Any:
        if self._filter is not None:
            try:
                return self._filter.eu2raw(self.read( ))
            except Exception as e:
                return self.read( )
        
        return self._value
    
    def changed(self,callback: Callable[[Any],None]):
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
        if self._filter: 
            try:
                self.write( self._filter.raw2eu(self._iec),remote=True)
            except Exception as e:
                _log.warning( f'проблема в raw2eu {self.name}: {e}' )
                self.write( self._iec ,remote=True)
        else:
            self.write( self._iec,remote = True )
    @property
    def filter(self)->Filter|None:
        return self._filter
    @filter.setter
    def filter(self,cls: Type[Filter]):
        self._filter = cls(what=self, next = self._filter)
        
    value = property(read,write)
    raw = property(iec,remote)

class Expressions(dict):
    class Expression(Property,dict):
        def __init__(self,t:Type[T], ctx, source: str, locals = None) -> None:
            super().__init__( t )
            self.value = t()
            self.ctx = ctx
            self.source:str = source
            self.locals = locals
            self.crossreferences:List[str] = []
            self._references: List[Property] = []   #список переменных, от которых зависит выражение

        def isDependsOn(self,key:str):
            return key in self.crossreferences
        
        def reference( self, key: str, prop: Property):
            self.crossreferences.append(key)
            prop.bind(self.evaluate,True)
            self._references.append(prop)
            prop.on_good_changed( self.on_update_good )
            
        def on_update_good(self,good: bool ):     #кто-то из _references изменил свой good
            self.good = good and all( [ x.good for x in self._references] ) # для оптимизации если good==False all не будет проверяться
            
        def evaluate(self,*_):
            ret = eval( self.source, self )
            self.write( ret )
            self.on_update_good( True )
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
        
        def __str__(self):
            return '%s(%s)=%s' % (type(self).__name__, self.source ,self.value)
        
        def __repr__(self):
            return f'Expressions.Expression({self._eu_type.__name__},source=\'{self.source}\')'
        
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
        
    def create(self,t: Type[T], source: str,locals: dict|None = None):
        ret = self.Expression( t, self, source, locals = locals )
        ret.evaluate(  )
        return ret
