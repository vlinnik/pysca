import os
import time
import sys,os,glob,re,types
import json
import loguru
import functools
from collections import ChainMap
from datetime import datetime
from types import FunctionType
from typing import Any,TypeVar,Dict,Optional,Callable,cast,TYPE_CHECKING,Generator,Tuple,Union
from pathlib import Path
from sqlalchemy import create_engine,select,or_,exc
from sqlalchemy.orm import Session
from .bindable import Expressions,Property
from .utils import LinearScale
from .types import Variables as _Variables,Animations as _Animations,Signals as _Signals
from .config import init_config,config

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget
    from qtpy.QtCore import QObject
    from .journal import MetricJournal
    from .events import MetricDairy
    from .alerts import AlertsJournal

log = loguru.logger
    
T = TypeVar('T', str, bool, float, int)
F = TypeVar('F', bound=Callable)

class App():
    def __init__(self):
        self.animations = []
        self.slots = []
        self.devices = { }          #устройства IO
        self.ctx = Expressions( )   #выражения и переменные, как локальный контекст используется
        self.session = None         #работа с базой 
        self._ = { }                #глобальный контекст приложения (передается через start(ctx=globals()))
        self.queued = []            #запланировано к анимированию. tuples параметров animate + objectID
        now = datetime.now()
        self.SECOND = self.var( Property(int,init_val=now.second),'SECOND')
        self.MINUTE = self.var( Property(int,init_val=now.minute),'MINUTE')
        self.HOUR = self.var( Property(int,init_val=now.hour),'HOUR')
        self.MSEC = self.var( Property(int,init_val=now.microsecond/1_000),'MSEC')
        self.NOW = self.var( Property(int, init_val=time.time()),'NOW')
        self.journal:Optional['MetricJournal'] = None
        self.events:Optional['MetricDairy'] = None
        self.alerts:Optional['AlertsJournal'] = None
        self._configured = False
        
    def _ensure_configured(self):
        if not self._configured:
            self.config(config().db)
            self.loadResources( )
    
    def __findChild(self,o: Optional['QObject'] , path: list[str] ):
        from qtpy.QtCore import QObject
        if o is None:
            return None
        
        if len(path)>1:
            child = o.findChild(QObject, path[1] )
            return self.__findChild(child,path[1:])
        return o

    def var(self,v: Property, name: str)->Property:
        self.ctx[name] = v
        return v
            
    def exec(self,code: str, ctx:dict[str,Any]={} ):
        try:
            exec( code, self._ , dict(self.ctx,**ctx) )
        except Exception as e:
            log.error(f'error in "{code}" - {e}')
    
    def eval(self,code: str, ctx:Optional[dict]=None )->Any:
        return eval( code, self.ctx,  ctx if ctx else self._  )

    def context(self)->dict:
        return self._
    
    def tick(self):
        now = datetime.now( )
        self.NOW(time.time())
        self.SECOND(now.second)
        self.MINUTE(now.minute)
        self.HOUR(now.hour)

    def start(self,ctx: dict ,use_asyncio: bool = False):
        from qtpy.QtWidgets import QApplication
        from qtpy.QtCore import QTimer
        self._.update(ctx)
        
        for name,dev in self.devices.items():
            log.debug(f'инициализация источника данных {name}')
            for p in list(self.ctx.values()):
                if p.source == name:
                    dev.subscribe(p)
        clock = QTimer()
        clock.timeout.connect( self.tick )
        clock.start(100)
        qApp = QApplication.instance()
        if not qApp:
            log.error('Запуск pysca.app возможен только после создания QApplication')
            return
        if not use_asyncio:
            if self.journal: self.journal.start( )
            for d in self.devices.values():
                d.start( )
            qApp.exec( )
            for d in self.devices.values():
                d.stop( )
        else:
            from qasync import QEventLoop
            import asyncio
            loop = QEventLoop(qApp)
            asyncio.set_event_loop(loop)
            
            for d in self.devices.values():
                d.start( )
            with loop:
                loop.run_forever( )
            for d in self.devices.values():
                d.stop( )
                        
        clock.stop( )
        
    def loadResources(self):
        from qtpy.QtCore import QResource 
        for rcc_dir in config().resources:        
            rcc_files = glob.glob('*.rcc',root_dir=rcc_dir)
            for rcc in rcc_files:
                mod_name = os.path.splitext(rcc)[0]+'_rc'
                sys.modules[mod_name] = types.ModuleType(mod_name)
                QResource.registerResource(f'{rcc_dir}/{rcc}')        
        
    def config(self,db:Path):
        if not os.path.isabs(db):
            db = db.absolute()
            
        if not os.path.exists(db):
            log.error(f'База анимаций {db} не найдена')
        else:        
            db_conn = f'sqlite:///{db}'
            log.debug(f'Открываем базу анимаций {db_conn}')
            engine = create_engine(db_conn, echo=False)

            self.session = session = Session(engine)
            vars = select(_Variables).order_by(_Variables.type)
            
            for var in session.scalars(vars):
                p = None
                
                if var.type==Property.TYPE_FLOAT:
                    p = Property( float ) 
                elif var.type==Property.TYPE_BOOL:
                    p = Property( bool ) 
                elif var.type==Property.TYPE_STR:
                    p = Property( str ) 
                elif var.type==Property.TYPE_INT:
                    p = Property( int ) 
                elif var.type==Property.TYPE_LONG:
                    p = Property( int ) 
                else:
                    raise ValueError('Переменная %s тип %d не поддерживается' % (str(var.name),int(var.type)))
                
                self.var(p,var.name)
                p.name = var.name
                p.source = var.source
                p.address = var.address
                p.type = var.type
                p.comment = var.comment

                try:
                    p.properties = cast(dict[str,Any],json.loads( cast(bytes,var.properties).decode() ) )
                except Exception as e:
                    p.properties = dict[str,Any]( )

                if var.type==Property.TYPE_FLOAT:
                    p.filter = LinearScale
                    
                if var.logging==True and self.journal:
                    p.filter = self.journal.factory()
                    
                if var.events==True and self.events:
                    p.filter = self.events.factory()
                    
                if var.alarms==True and self.alerts:
                    p.filter = self.alerts.factory( )
                
                rx = re.compile('^monitor.*')
                if any(rx.search(key) for key in p.properties):
                    from .monitor import Monitor
                    p.monitor = Monitor( self.exec, self.eval , comment=var.comment,subject=p,**p.properties )
                    pass

                p.config(p.properties)

        self._configured = True

    def ctxOf(self,target, ctx: Optional[dict] =None) -> Generator[Tuple[str,Any],Any,None]:
        """Lazy dict-factory: из результата можно получить dict(ctxOf(targe)), который
        используется для app.window/app.animate 

        Args:
            target (_type_): _description_
            ctx (Optional[dict], optional): _description_. Defaults to None.

        Yields:
            Generator[Tuple[str,Any],Any,None]: _description_
        """
        for key in target.dynamicPropertyNames():
            yield bytearray(key).decode(),target.property(key.data().decode())
        if ctx is not None:
            for key in ctx:
                yield key,ctx[key]
        
    def bindings( self, target: 'QObject',ctx: Optional[dict] = None, **kwargs):
        """Привязать свойства target к выражениям (python)
        
        Использование: 
        target = QPushButton()
        app.bindings(target, down = 'not AUGER_ON_1', enabled = 'MOTOR_ISON_1')

        Args:
            target (QObject): Объект чьи свойства будут автоматически вычисляться
            ctx (dict | None, optional): Контекст, в котором происходит вычисление выражения. Defaults to None.
        """
        from .qtac import QObjectPropertyBinding,QObjectDynamicPropertyHelper
        from .flexeffect import FlexEffect
        
        helper = None

        for prop in kwargs:
            if target.isWidgetType() and not target.property('_effect'):
                target.setProperty('_effect',(FlexEffect(cast(QWidget,target) )))
                            
            code = kwargs[prop]
            current = target.property(prop)
            
            rd_only = False
            wr_only = False
            expression = None
            if isinstance(code,Property):
                expression = code
            elif isinstance(code,str):
                expression = self.ctx.create(type(current),code,locals=ctx)
            elif callable(code) and code is not None:
                try:
                    init_val = code( )
                except TypeError as e:
                    init_val = None
                    wr_only = True
                _rd = cast(Callable[[],Any],code)
                _wr = cast(Callable[[Any],None],code)
                expression = Property(type(current),init_val, read=None if wr_only else _rd, write=_wr if not rd_only else None)
            else:
                log.warning('неизвестный тип анимации %s для свойства %s' % (type(code),prop))
                continue
                
            if rd_only:
                if not prop.startswith('__effect_'):
                    ani = QObjectPropertyBinding.create( target, prop, expression ,readOnly=True)
                else:
                    effect = target.property('_effect')
                    ani = QObjectPropertyBinding.create( effect, str(prop)[9:], expression ,readOnly=True)
                    
                self.animations.append( ani )
                ani.update(expression.value)
            else:
                ani = QObjectPropertyBinding.create( target, prop, expression )
                self.animations.append(ani)
                if ani.dynamic:
                    if not helper:
                        helper = QObjectDynamicPropertyHelper(target)   #TODO: надо где-то сохранить созданный объект
                    helper.mapping( prop, code )
            
    def animate(self,obj, ctx: Optional[Union[dict, Generator[Tuple[str,Any],Any,None] ]] = None,objectID:Optional[str] = None):
        """Настроить анимации свойств из базы

        Args:
            obj (QObject): что анимировать
            ctx (dict, optional): дополнительные переменные. Defaults to None.
            objectID (str, optional): с чего начинаются записи в базе. Defaults to None.
            later (bool, optional): для отложенной анимации (запланировать, анимирование произойдет при следующем вызове с later=False). Defaults to None.
        """
        from .qtac import QObjectPropertyBinding,QObjectDynamicPropertyHelper
        from .flexeffect import FlexEffect
        
        if not self.session:
            return
                    
        if not objectID:
            objectID = obj.objectName() 
        
        animation_ctx = { 'self': obj ,objectID:obj }

        self._ensure_configured( )
        helpers = dict[str,QObjectDynamicPropertyHelper]( )
        animations = select(_Animations).where( or_(_Animations.objectID.startswith(objectID+"."),_Animations.objectID==(objectID)) )
        
        for animation in self.session.scalars(animations):
            target = self.__findChild( obj, animation.objectID.split('.') )
            if target is None:
                log.error('анимируемый объект(%s) не найден' % (animation.objectID))
                continue
            
            if target.isWidgetType() and not target.property('_effect'):
                target.setProperty('_effect',FlexEffect(target))
                            
            code = animation.data
            try:
                resolved = eval(f'f\'{code}\'',None,dict(self.ctxOf(obj,ChainMap(animation_ctx,ctx or {}))))
                code = resolved
            except Exception as e:
                pass
            try:
                rd_only = False
                wr_only = False
                if re.match("@(\\w+(\\.\\w+)*)",code):
                    code = re.sub("@(\\w+(\\.\\w+)*)","\\1",code)
                    rd_only = True
                if re.match("&(\\w+(\\.\\w+)*)",code):
                    code = re.sub("&(\\w+(\\.\\w+)*)","\\1",code)
                    wr_only = True
                
                if code in self.ctx and not rd_only and not animation.prop.startswith('__effect_'):
                    ani = QObjectPropertyBinding.create( target, animation.prop, self.ctx[code])
                    expression = self.ctx[code]
                    self.animations.append(ani)
                    if ani.dynamic:
                        if animation.objectID not in helpers:
                            helpers[animation.objectID] = QObjectDynamicPropertyHelper(target)
                        helpers[animation.objectID].mapping( animation.prop,self.ctx[code] )
                else:
                    current = target.property(animation.prop)
                    expression = self.ctx.create(type(current),code,locals=dict(self.ctxOf(obj,ChainMap(animation_ctx,ctx or {}))))
                    if not animation.prop.startswith('__effect_'):
                        ani = QObjectPropertyBinding.create( target, animation.prop, expression ,readOnly=True)
                    else:
                        effect = target.property(b'_effect')
                        ani = QObjectPropertyBinding.create( effect, str(animation.prop)[9:], expression ,readOnly=True)
                        
                    self.animations.append( ani )
                    ani.update(expression.value)
                if ani:
                    expression.on_good_changed( ani.quality )
                    ani.on_destroy( lambda x: expression.on_good_changed(x.quality,remove=True))
                    pass
                    
            except Exception as e:
                log.error('ошибка при настройки анимации: объект(%s/%s), свойство(%s), выражение(%s): %s' % (animation.objectID,target.objectName(),animation.prop,animation.data,e) )
            
    def signals(self, obj, objectID: str = '',ctx: Optional[Union[dict, Generator[Tuple[str,Any],Any,None] ]] = None):
        from .qtac import QObjectSignalHandler

        if not obj:
            return
        
        if not self.session:
            return
        
        if not objectID:
            objectID = obj.objectName() 
                    
        signal_ctx = { 'self': obj }

        self._ensure_configured( )
        signals = select(_Signals).where( or_(_Signals.objectID.startswith(objectID+"."),_Signals.objectID==(objectID)) )
        for signal in self.session.scalars(signals):
            try:
                target = self.__findChild( obj,signal.objectID.split('.') )
                if target:
                    code = signal.data
                    try:
                        resolved = eval(f'f\'{code}\'',None,dict(self.ctxOf(obj,ChainMap(signal_ctx,ctx or {}))))
                        code = resolved
                    except Exception as e:
                        pass                    
                    if re.match("@(\\w+(\\.\\w+)*)",code):
                        code = re.sub("@(\\w+(\\.\\w+)*)","\\1.value",code)
                    self.slots.append(QObjectSignalHandler(target,signal.signal,code,self.context,self.ctx,this = obj,user_ctx=ctx))
                else:
                    log.error('для события нет объекта: объект(%s), событие(%s), выражение(%s)' % (signal.objectID,signal.signal,signal.data) )
                    
            except Exception as e:
                log.error('ошибка при настройке события: объект(%s), событие(%s), выражение(%s): %s' % (signal.objectID,signal.signal,signal.data,e) )
                
    def window(self,t: 'type|str|QWidget',*, objectID:str = '',ctx: Optional[Union[dict, Generator[Tuple[str,Any],Any,None] ]] = None, baseinstance: Any | None=None, later:bool=False, parent:Optional['QWidget'] = None, **kwargs)->Optional['QWidget']:
        try:
            from qtpy import uic
            from qtpy.QtWidgets import QWidget
            if isinstance(t,type):
                if len(kwargs)>0:
                    w = t( **kwargs )
                else:
                    w = t( )
            elif isinstance(t,str) or isinstance(t,Path):
                if config().ui.joinpath(t).exists():
                    t = str(config().ui.joinpath(t))
                else:
                    t = str(t)
                log.debug('Загрузка окна из UI-файла %s' % (t))
                if not os.path.exists( t ):
                    log.error(f'Файл {os.path.abspath(t)} не существует')
                    return None
                try:
                    if not later:
                        self._ensure_configured( )
                    t = os.path.abspath(t)
                    w = uic.loadUi( t ,baseinstance=baseinstance)
                    if w is None:
                        log.error(f'Не удалось загрузить UI {t}') 
                        return None
                except Exception as e:
                    log.error(f'Не удалось загрузить UI {t} - {e}') 
                    return None
            elif isinstance(t,QWidget):
                w = t  
            else:
                log.warning('Неизвестный тип параметра t %s' % (type(t)))

            for key,item in kwargs.items():
                w.setProperty(key,item)
                
            try:
                if not later:
                    self._ensure_configured()
                    self.animate(w,objectID=objectID,ctx=ctx)
                    self.signals(w,objectID=objectID,ctx=ctx)
                    self.flush( )
                else:
                    self.queued.append( (w,objectID,ctx) )
            except exc.SQLAlchemyError as e:
                log.error('Ошибка при инициализации анимации/события: %s' % (e._message()))
            
            if parent is not None:
                flags = w.windowFlags()
                w.setParent(parent)
                w.setWindowFlags(flags)
            
            return w
        except Exception as e:
            log.error(f'Ошибка при создании окна: {t} ({e})')
            import traceback; traceback.print_exc();
            
    def object(self,obj:'QObject',objectID:str = '',ctx:dict|None = None):
        if ctx is None:
            ctx = { }
        try:
            ctx=dict(ctx)
            self.animate(obj,objectID=objectID,ctx=ctx)
            self.signals(obj,objectID=objectID,ctx=ctx)
        except exc.SQLAlchemyError as e:
            log.error('error while initializing animations/signals: %s' % (e._message()))        
    
    def flush(self):
        for q,objectID,ctx in self.queued:
            try:
                if ctx is not None:
                    ctx = dict(ctx)
                else:
                    ctx = { } 
                    
                if objectID not in ctx:
                    ctx[objectID] = q
                    
                self.animate(q,objectID=objectID,ctx=ctx)
                self.signals(q,objectID=objectID,ctx=ctx)
            except Exception as e:
                log.warning(f'внимание: проблема в отложенном анимировании объекта object({objectID})')
        self.queued.clear()                        

    def inject(self,ctx: Optional[Dict[str,Any]]=None)->F:
        """В теле функции сделать доступными IO переменные, окна и загруженные модули

        применять
        ```
        @app.inject()
        def on_start():
            #тут уже доступны переменные ввода-вывода, например SECOND
            pass
        ```

        Args:
            ctx (Optional[Dict[str,Any]], optional): Что должно быть доступно вместо self.context(). Defaults to None.

        Returns:
            F: Декоратор для функций
        """
        def decorator(func: FunctionType):
            @functools.wraps(func)
            def wrapped(*args,**kwargs):
                new_globals = func.__globals__.copy( )
                new_globals.update(ctx or self._)
                new_globals.update(self.ctx)
                cloned = FunctionType(func.__code__,new_globals,func.__name__,argdefs=func.__defaults__,closure=func.__closure__)
                return cloned(*args,**kwargs)
            return wrapped
        return decorator                                
        # func.__globals__.update( dict(ChainMap(ctx or self.context(),self.ctx )) )
        # wrapped = FunctionType(func.__code__,func.__globals__,func.__name__,argdefs=func.__defaults__,closure=func.__closure__)
        # wrapped.__annotations__ = func.__annotations__
        # wrapped.__doc__ = func.__doc__
        # wrapped.__qualname__ = func.__qualname__
        # wrapped.__module__ = func.__module__
        # return cast(F,wrapped)
