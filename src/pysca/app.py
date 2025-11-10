import os
from datetime import datetime
import time
import sys,os,glob,re,types
import json
from typing import Any,TypeVar,Optional,cast,TYPE_CHECKING
from .bindable import Expressions,Property
from .utils import LinearScale

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget
    from qtpy.QtCore import QObject
    from .journal import MetricJournal
    from .events import MetricDairy
    from .alerts import AlertsJournal

import logging
def console(name: str,level = logging.DEBUG)->logging.Logger:
    """создать логгер на консоль с цветовым выделением
    
    можно вместо этого:
    .. highlight:: python
    .. code-block:: python
        
    logging.basicConfig( format = '%(name)s.%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.DEBUG )    

    Args:
        name (str): имя логгера
        level (_type_, optional): уровень логгера. logging.DEBUG.

    Returns:
        logging.Logger: использовать для вывода отладочных сообщениий
    """
    class ColoredFormatter(logging.Formatter):
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "   %(name)s.%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: yellow + format + reset,
            logging.WARNING: red + format + reset,
            logging.ERROR: bold_red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    stream = logging.StreamHandler()
    stream.setFormatter(ColoredFormatter())
    stream.setLevel(level)
    ret = logging.getLogger(name)
    ret.setLevel(level)
    ret.addHandler(stream)
    return ret

#работа с базой конфигурации проекта
from sqlalchemy import String,Boolean,BLOB,Integer,create_engine,select,or_,exc,__version__ as sqlalchemy_version
from sqlalchemy.orm import Session,Mapped
if sqlalchemy_version<'2':
    from sqlalchemy import Column as mapped_column
    from sqlalchemy.orm import declarative_base
    _Base = declarative_base()
else:
    from sqlalchemy.orm import mapped_column,DeclarativeBase
    class _Base(DeclarativeBase):
        pass

class _Variables(_Base):
    __tablename__ = "Variables"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(45))
    type: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(45))
    comment: Mapped[str] = mapped_column(String(45))
    address: Mapped[str] = mapped_column(String(128))
    logging: Mapped[bool] = mapped_column(Boolean)
    events: Mapped[bool] = mapped_column(Boolean)
    alarms: Mapped[bool] = mapped_column(Boolean)
    properties: Mapped[BLOB] = mapped_column(BLOB)

class _Animations(_Base):
    __tablename__ = "Animations"
    id: Mapped[int] = mapped_column(primary_key=True)
    objectID: Mapped[str] = mapped_column(String(128))
    className: Mapped[str] = mapped_column(String(45))
    prop: Mapped[str] = mapped_column('property',String(45))
    data: Mapped[str] = mapped_column(String(128))

class _Signals(_Base):
    __tablename__ = "Signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    objectID: Mapped[str] = mapped_column(String(128))
    className: Mapped[str] = mapped_column(String(45))
    signal: Mapped[str] = mapped_column(String(45))
    data: Mapped[str] = mapped_column(String(128))

log = console('pysca')
    
from typing import TypeVar,  Callable
T = TypeVar('T', str, bool, float, int)

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
            self.config('default.scada')
    
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
            log.error('error in exec-code: %s (%s)',code,e)
    
    def eval(self,code: str, ctx:dict|None=None )->Any:
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
            log.debug(f'инициализация источника {name}')
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
            qApp.exec( )
        else:
            from qasync import QEventLoop
            import asyncio
            loop = QEventLoop(qApp)
            asyncio.set_event_loop(loop)
            with loop:
                loop.run_forever( )
                        
        clock.stop( )
        
    def config(self,db:str):
        from qtpy.QtCore import QResource 
        if not os.path.isabs(db):
            workdir = os.getcwd()
            db = f'{workdir}/{db}'
            
        if not os.path.exists(db):
            log.error(f'configuration {db} not found')
            return
        
        db_conn = f'sqlite:///{db}'
        log.debug(f'opening database {db_conn}')
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
                raise ValueError('Variable %s type %d not supported' % (str(var.name),int(var.type)))
            
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
                p.monitor = Monitor( self.exec, comment=var.comment,subject=p,**p.properties )
                pass

            p.config(p.properties)
        
        rcc_dir = os.path.dirname(os.path.abspath(db))
        log.debug(f'searching resource files in {rcc_dir}')
        rcc_files = glob.glob('*.rcc',root_dir=rcc_dir)
        for rcc in rcc_files:
            mod_name = os.path.splitext(rcc)[0]+'_rc'
            log.debug(f'loading resources file {rcc_dir}/{rcc}/{mod_name}')
            sys.modules[mod_name] = types.ModuleType(mod_name)
            QResource.registerResource(f'{rcc_dir}/{rcc}')
        self._configured = True

    def ctxOf(self,target, ctx: dict|None =None):
        for key in target.dynamicPropertyNames():
            yield bytearray(key).decode(),target.property(key)
        if ctx is not None:
            for key in ctx:
                yield key,ctx[key]
        
    def bindings( self, target: 'QObject',ctx: dict|None = None, **kwargs):
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
            
    def animate(self,obj, ctx: Optional[dict] = None,objectID:Optional[str] = None):
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
                    
        if not ctx:
            ctx = { }

        if not objectID:
            objectID = obj.objectName() 
        
        if objectID not in ctx:
            ctx[objectID] = obj
            
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
                resolved = eval(f'f\'{code}\'',None,dict(self.ctxOf(obj,ctx)))
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
                    self.animations.append(ani)
                    if ani.dynamic:
                        if animation.objectID not in helpers:
                            helpers[animation.objectID] = QObjectDynamicPropertyHelper(target)
                        helpers[animation.objectID].mapping( animation.prop,self.ctx[code] )
                else:
                    current = target.property(animation.prop)
                    expression = self.ctx.create(type(current),code,locals=ctx)
                    if not animation.prop.startswith('__effect_'):
                        ani = QObjectPropertyBinding.create( target, animation.prop, expression ,readOnly=True)
                    else:
                        effect = target.property(b'_effect')
                        ani = QObjectPropertyBinding.create( effect, str(animation.prop)[9:], expression ,readOnly=True)
                        
                    self.animations.append( ani )
                    ani.update(expression.value)
                    
                    
            except Exception as e:
                log.error('ошибка при настройки анимации: объект(%s), свойство(%s), выражение(%s): %s' % (animation.objectID,animation.prop,animation.data,e) )
            
    def signals(self, obj, objectID: str = '',ctx:dict|None = None):
        from .qtac import QObjectSignalHandler

        if not obj:
            return
        
        if not self.session:
            return
        
        if not objectID:
            objectID = obj.objectName() 
        
        if ctx is None:
            ctx = { }

        self._ensure_configured( )
        signals = select(_Signals).where( or_(_Signals.objectID.startswith(objectID+"."),_Signals.objectID==(objectID)) )
        for signal in self.session.scalars(signals):
            try:
                target = self.__findChild( obj,signal.objectID.split('.') )
                if target:
                    code = signal.data
                    try:
                        resolved = eval(f'f\'{code}\'',None,ctx)
                        code = resolved
                    except Exception as e:
                        pass                    
                    if re.match("@(\\w+(\\.\\w+)*)",code):
                        code = re.sub("@(\\w+(\\.\\w+)*)","\\1.value",code)
                    self.slots.append(QObjectSignalHandler(target,signal.signal,code,self.context,self.ctx,this = obj,user_ctx=ctx))
                else:
                    log.error('для события нет объекта: объект(%s), событие(%s), выражение(%s)' % (signal.objectID,signal.signal,signal.data) )
                    # log.warning(f'no {signal.objectID} in {obj.objectName()}')
                    
            except Exception as e:
                log.error('ошибка при настройке события: объект(%s), событие(%s), выражение(%s): %s' % (signal.objectID,signal.signal,signal.data,e) )
                # log.error('error in signal initialization %s(%s)' % (objectID,e) )
                
    def window(self,t: 'type|str|QWidget',*, objectID:str = '',ctx: dict | None = None, baseinstance: Any | None=None, later:bool=False, parent:Optional['QWidget'] = None, **kwargs)->Optional['QWidget']:
        try:
            from qtpy import uic
            from qtpy.QtWidgets import QWidget
            self._ensure_configured()
            if isinstance(t,type):
                if len(kwargs)>0:
                    w = t( **kwargs )
                else:
                    w = t( )
            elif isinstance(t,str):
                log.debug('loading form from UI-file (%s)' % (t))
                w = uic.loadUi( t ,baseinstance=baseinstance)
                if w is None:
                    log.error('failed to load UI-file') 
                    return None
            elif isinstance(t,QWidget):
                w = t    

            for key,item in kwargs.items():
                w.setProperty(key,item)
                
            try:
                if not later:
                    self.animate(w,objectID=objectID,ctx=ctx)
                    self.signals(w,objectID=objectID,ctx=ctx)
                    self.flush( )
                else:
                    self.queued.append( (w,objectID,ctx) )
            except exc.SQLAlchemyError as e:
                log.error('error while initializing animations/signals: %s' % (e._message()))
            
            if parent is not None:
                flags = w.windowFlags()
                w.setParent(parent)
                w.setWindowFlags(flags)
            
            return w
        except Exception as e:
            log.error('error creating window: %s (%s)',t,e)
            
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
