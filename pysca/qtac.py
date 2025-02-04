from AnyQt.QtCore import QObject,QMetaObject,QEvent,QDynamicPropertyChangeEvent,cast
from AnyQt.QtWidgets import QGraphicsBlurEffect
from .flexeffect import FlexEffect
from typing import Callable
from .bindable import Property

class QObjectDynamicPropertyHelper(QObject):
    def __init__(self, parent:QObject = None):
        super().__init__(parent)
        self._map = {} 
        parent.installEventFilter(self)
    
    def mapping(self,prop: str, input: callable ):
        self._map[prop] = input
    
    def eventFilter(self, obj, e)->bool:
        if e.type()==QEvent.Type.DynamicPropertyChange:
            mp:QDynamicPropertyChangeEvent = cast(e,QDynamicPropertyChangeEvent)
            name = mp.propertyName().data().decode()
            if name in self._map:
                self._map[name]( self.parent().property(name))
            
        return super().eventFilter(obj, e)

class QObjectPropertyBinding():
    """QObjectPropertyBinding предназначен для анимирования свойств QObject-derived объектов с помощью callback или bindable.Property
    
    """
    def __init__(self,obj: QObject, prop: str, display: callable = None,input: callable = None , clean: callable = None) -> None:
        """Создать новую анимацию для свойства prop объекта obj
        
        - Если prop должна отображать какие-то значения: QObjectPropertyBinder.__update меняет prop. Параметр display должен быть !=None.
        display(d: callable) нужен для настройки вызова d при изменении того что нужно отображать. cleanup(d) должна останавливать связь.
        
        - Если все изменение prop должны где то регистрироваться: свойство prop должно иметь notifySignal, тогда при изменениях будет 
        вызвана input(<значение prop>). 

        Args:
            obj (QObject): Объект анимации
            prop (str): Свойство obj, которое анимируется
            display (callable, optional): Настройка чем менять prop. obj.prop будет отображать. Defaults to None.
            input (callable, optional): . Настройка что меняет prop. obj.prop будет изменять. Defaults to None.
            clean (callable, optional): Обратная display. Defaults to None.
        """
        self.connections = []
        self.prop = prop
        mo = obj.metaObject()
        mp = mo.property( mo.indexOfProperty(prop) )
        if input and obj.inherits('QAbstractButton') and prop=='down':
            self.connections.append(obj.pressed.connect( lambda: input(True) ))
            self.connections.append(obj.released.connect( lambda: input(False) ))
        elif input and obj.inherits('QLineEdit') and prop=='text':
            self.connections.append( obj.editingFinished.connect( lambda: input(obj.text()) ) )
        elif input and mp.hasNotifySignal():
            self.connections.append( getattr(obj,mp.notifySignal().name().data().decode()).connect( input ) )

        self.dynamic = False
        if input and not mp.isValid() and prop in obj.dynamicPropertyNames():
            self.dynamic = True

        self.mp = mp
        self.obj = obj
        self._isWidget = obj.inherits('QWidget') 

        if display:
            self.clean = clean
            display( self.update )
        else:
            self.clean = None
            
        self.obj.destroyed.connect(self.cleanup)
                
    def update(self,value):
        """Изменить свойство 

        Args:
            value (Any): новое значения для свойства
        """
        if self._isWidget:
            effect:FlexEffect = self.obj.property('_effect')
            if effect:
                if value is None: effect.push( QGraphicsBlurEffect(self.obj)  )
                if value is not None: effect.pop()
            
        if self.mp.isValid():
            self.mp.write(self.obj,value)
        elif self.dynamic:
            self.obj.setProperty(self.prop,value)
        
    def cleanup(self):
        """После вызова cleanup QObjectPropertyBinder-instance можно удалять. 
        """
        try:
            for i in self.connections:
                self.obj.disconnect(i)
                
            self.connections.clear( )
        except Exception as e:
            pass    
        
        if self.clean:
            self.clean(self.update)
            
        self.obj = None
        self.mp = None
        self.prop = None

    def __del__(self):
        pass
    
    @staticmethod
    def create(obj: QObject, prop: str, target: Property, readOnly: bool=False):
        """Создать новый QObjectPropertyBinding с привязкой к target
        
        target(bindable.Property) имеет механизм привязки к изменениям:
        
        - target.bind используется в качестве параметра display
        - target.unbind используется в качестве параметра cleanup
        - target.write используется в качестве параметра input

        Они будут использованы при вызове QObjectPropertyBinding.__init__
        
        Args:
            obj (QObject): Целевой obj
            prop (str): Свойство obj 
            target (Property): bindable.Property. 
            readOnly (bool, optional): Использовать только для отображения. Defaults to False.

        Returns:
            QObjectPropertyBinding: созданный объект
        """
        return QObjectPropertyBinding(obj,prop,target.bind,None if readOnly else target.write,target.unbind)

class QObjectSignalHandler():
    """Привязка signal-а к выполнению python-кода.
    
    Код может содержать ссылки на параметры signal, arg1 например первый параметр.
    """
    def __init__(self,obj: QObject, signal: str, code: str , globals: Callable[[],dict], ctx = None) -> None:
        mo = obj.metaObject()
        ms = mo.method( mo.indexOfSignal(QMetaObject.normalizedSignature(signal) ) )
        self.code = code
        self.obj = obj
        self.ctx = ctx
        self.globals = globals
        
        self.args = [ x[0].data().decode() if x[0].size()>0 else f'arg{x[1]+1}' for x in zip(list(ms.parameterNames( )),range(ms.parameterCount()))]
        self.connection = getattr(obj,ms.name().data().decode()).connect( self )
        
        self.obj.destroyed.connect(self.stop)
    
    def __del__(self):
        self.stop( )

    def stop(self):
        try:
            self.obj.disconnect(self.connection)
        except:
            pass

    def __call__(self, *_ ):
        args = { }
        for arg in zip(self.args,_):
            args[arg[0]] = arg[1]
        
        exec( self.code, dict(self.ctx, **self.globals()) , args )
