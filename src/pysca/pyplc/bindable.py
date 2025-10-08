class Property():
    def __init__(self,init_val=None,read=None, write=None):
        self.__binds = []
        if isinstance(init_val,type):
            self.value = init_val( )
        else:
            self.value = init_val
        self._read = read
        self._write = write

    def bind(self,__sink,no_init:bool=False):  
        self.__binds.append( __sink )
        if not no_init:
            __sink(self.read())
        return self.write

    def unbind(self,__sink = None):
        self.__binds = list(filter( lambda x: not (x==__sink or __sink is None)), self.__binds )

    def read(self):
        if self._read:
            self.value = self._read( )
        return self.value

    def write(self,value):
        if self.value!=value:
            if type(self.value)!=type(value) and self.value is not None and value is not None:
                self.value = type(self.value)(value)
            else:
                self.value = value
            if self._write:
                self._write(self.value)
            for b in self.__binds:
                b(self.value)

    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self.read()

    def __get__(self, obj, _=None):
        if obj is None:
            return self        
        return self.read( )
        
    def __set__(self,_,value):
        self.write(value)
        
    def __repr__(self) -> str:
        return f'Property <{self.value}|lazy={self._read is not None}>'
    
class Expressions(dict):
    class Expression(Property):
        def __init__(self, ctx, source: str) -> None:
            self.value = None
            self.ctx = ctx
            self.source = source
            self.crossreferences = []
            super().__init__( )

        def isDependsOn(self,key:str):
            return key in self.crossreferences
        
        def reference( self, key: str, prop: Property):
            self.crossreferences.append(key)
            prop.bind(self.evaluate,True)

        def evaluate(self,*_):
            try:
                saved = self.ctx.last
            except:
                saved = None
            self.ctx.last = self
            ret = eval( self.source, self.ctx )
            self.ctx.last = saved
            self.write( ret )
            return ret
        
    def __init__(self):
        self.last = None
        self.items = { }
        pass

    def __getitem__(self, __key):
        if self.last is not None and not self.last.isDependsOn(__key):
            self.last.reference(__key,self.items[__key])
        return self.items[__key].read()
    
    def __setitem__(self, __key, __value) -> None:
        if __key in self.items:
            self.items[__key].write(__value)
    
    def keys(self):
        return self.items.keys()
    
    def append(self,name, prop: Property ):
        self.items[name] = prop

    def create(self,source: str):
        ret = self.Expression( self, source )
        ret.evaluate()
        return ret
