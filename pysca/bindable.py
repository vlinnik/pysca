from typing import Any

class Property():
    """Хранение значения, с механизмом привязки к его изменениям.
    
    Значение может быть результатом функции. Контролируются изменения с помощью Property.write.
    """
    def __init__(self,init_val=None,read:callable=None, write: callable=None):
        """Новое контролируемое значение(свойство).

        Args:
            init_val (Any, optional): Начальное значение. Фиксирует тип. Можно использовать типы, например init_val = bool. Defaults to None.
            read (callable, optional): Значение свойства=результат вызова функции read(). Defaults to None.
            write (_type_, optional): Для изменения свойства используется функция write(<новое значение>). Defaults to None.
        """
        self.__binds = []
        if isinstance(init_val,type):
            self._value = init_val( )
        else:
            self._value = init_val
        self._read = read
        self._write = write

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

    def write(self,value: Any):
        """Изменить текущее значение.

        Args:
            value (Any): Тип должен быть преобразуем к типу текущего значения.

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
                b(self._value)

    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self.read()

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, self._value )
    
    value = property(read,write)

class Expressions(dict):
    class Expression(Property,dict):
        def __init__(self, ctx, source: str) -> None:
            super().__init__( )
            self.value = None
            self.ctx = ctx
            self.source = source
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
        
    def create(self,source: str):
        ret = self.Expression( self, source )
        ret.evaluate()
        return ret
