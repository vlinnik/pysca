from AnyQt.QtWidgets import QApplication,QWidget
from AnyQt.QtCore import QObject,QResource,QVariant,QTimer
from datetime import datetime
import time
import sys,os,glob,re,types
import logging
import argparse
import json
from typing import Any
try:
    from .__version__ import version
except ImportError:
    version = 'v0.0.0+unknown'
from .bindable import Expressions,Property
from .utils import LinearScale
from .device import PYPLC

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
        format = "%(name)s.%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

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

class _Variables(_Base):
    __tablename__ = "Variables"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(45))
    type: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(45))
    address: Mapped[str] = mapped_column(String(128))
    logging: Mapped[bool] = mapped_column(Boolean)
    events: Mapped[bool] = mapped_column(Boolean)
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
log.info(f'initializing pysca {version}, sqlalchemy {sqlalchemy_version}')
if not QApplication.instance():
    qApp = QApplication(sys.argv)
else:
    qApp = QApplication.instance()

parser = argparse.ArgumentParser(
                    prog='PYSCA Project',
                    description='Запуск проекта визуализации на Python+Qt',
                    epilog='Пример: python -m pysca')

parser.add_argument('--conf',action='store',default='default.scada',help='Конфигурационная база проекта (переменные, анимации, короткие события)')
parser.add_argument('-w','--workdir',action='store',default='./',help='Рабочий каталог проекта')

args,ignored = parser.parse_known_args()
    
class _pysca():
    def __init__(self):
        self.animations = []
        self.slots = []
        self.devices = { }          #устройства IO
        self.ctx = Expressions( )   #выражения и переменные
        self.session = None         #работа с базой 
        self._ = { }
        self.queued = []            #запланировано к анимированию. tuples параметров animate + objectID
        now = datetime.now()
        self.SECOND = self.var(int(now.second),'SECOND')
        self.MINUTE = self.var(int(now.minute),'MINUTE')
        self.HOUR = self.var(int(now.hour),'HOUR')
        self.MSEC = self.var(int(now.microsecond/1_000),'MSEC')
        self.NOW = self.var(time.time(),'NOW')
    
    def __findChild(self,o: QObject, path: list[str] ):
        if o is None:
            return None
        
        # if o.objectName()!=path[0]:
        #     return None
        
        if len(path)>1:
            child = o.findChild(QObject, path[1] )
            return self.__findChild(child,path[1:])
        return o
        

    def var(self,init_val: Any | type =None,name: str=None)->Property:
        if isinstance(init_val, Property ):
            self.ctx[name] = init_val
            return init_val
        else:
            ret = Property(init_val)
            if name is not None:
                self.ctx[name] = ret
            return ret
        
    def expr(self,code:str )->Expressions.Expression:
        return self.ctx.create(code)
    
    def exec(self,code: str, ctx:dict=None ):
        try:
            exec( code, ctx if ctx else self._ , self.ctx )
        except Exception as e:
            log.error('error in exec-code: %s (%s)',code,e)
    
    def eval(self,code: str, ctx:dict=None )->Any:
        # try:
        return eval( code, ctx if ctx else self._ , self.ctx )
        # except Exception as e:
        #     log.error('error in eval-code: %s (%s)',code, e)
            
        # return None
        
    def context(self)->dict:
        return self._
    
    def tick(self):
        now = datetime.now( )
        self.NOW(time.time())
        self.SECOND(now.second)
        self.MINUTE(now.minute)
        self.HOUR(now.hour)

    def start(self,ctx: dict ):
        self._ = ctx
        
        for name,dev in self.devices.items():
            log.debug(f'инициализация источника {name}')
            for p in self.ctx.values():
                if p.source == name:
                    dev.subscribe(p)
        
        clock = QTimer()
        clock.timeout.connect( self.tick )
        clock.start(100)
        qApp.exec( )
        clock.stop( )
        
    def config(self,db:str): 
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
                p = self.var(float,var.name)
                p.filter = LinearScale()
            elif var.type==Property.TYPE_BOOL:
                p = self.var(bool,var.name)
            elif var.type==Property.TYPE_STR:
                p = self.var(str,var.name)
            elif var.type==Property.TYPE_INT:
                p = self.var(int,var.name)
            elif var.type==Property.TYPE_LONG:
                p = self.var(int,var.name)
            else:
                raise ValueError('Variable %s type %d not supported' % (str(var.name),int(var.type)))
            
            p.name = var.name
            p.source = var.source
            p.address = var.address
            p.type = var.type
            try:
                p.properties = json.loads( var.properties )
            except:
                p.properties = { }
            p.config(p.properties)
        
        rcc_dir = os.path.dirname(os.path.abspath(db))
        log.debug(f'searching resource files in {rcc_dir}')
        rcc_files = glob.glob('*.rcc',root_dir=rcc_dir)
        for rcc in rcc_files:
            mod_name = os.path.splitext(rcc)[0]+'_rc'
            log.debug(f'loading resources file {rcc_dir}/{rcc}/{mod_name}')
            sys.modules[mod_name] = types.ModuleType(mod_name)
            QResource.registerResource(f'{rcc_dir}/{rcc}')

    def ctxOf(self,target, ctx: dict =None):
        for key in target.dynamicPropertyNames():
            yield bytearray(key).decode(),target.property(key)
        if ctx is not None:
            for key in ctx:
                yield key,ctx[key]
        
    def bindings( self, target: QObject,ctx: dict = None, **kwargs):
        from .qtac import QObjectPropertyBinding,QObjectDynamicPropertyHelper
        from .flexeffect import FlexEffect
        
        helper = None

        for prop in kwargs:
            if target.isWidgetType() and not target.property(b'_effect'):
                target.setProperty(b'_effect',QVariant(FlexEffect(target)))
                            
            code = kwargs[prop]
            
            rd_only = False
            wr_only = False
            expression = None
            if isinstance(code,Property):
                expression = code
            elif isinstance(code,str):
                expression = self.ctx.create(code,locals=ctx)
            elif callable(code):
                try:
                    init_val = code( )
                except TypeError as e:
                    init_val = None
                    wr_only = True
                expression = Property(init_val, read=None if wr_only else code, write=code if not rd_only else None)
            else:
                log.warning('неизвестный тип анимации %s для свойства %s' % (type(code),prop))
                continue
                
            if rd_only:
                if not prop.startswith('__effect_'):
                    ani = QObjectPropertyBinding.create( target, prop, expression ,readOnly=True)
                else:
                    effect = target.property(b'_effect')
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
            
    def animate(self,obj, ctx: dict = None,objectID:str = None):
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
            
        helpers = dict[str,QObjectDynamicPropertyHelper]( )
        animations = select(_Animations).where( or_(_Animations.objectID.startswith(objectID+"."),_Animations.objectID==(objectID)) )
        
        for animation in self.session.scalars(animations):
            target = self.__findChild( obj, animation.objectID.split('.') )
            if target is None:
                log.error('анимируемый объект(%s) не найден' % (animation.objectID))
                continue
            
            if target.isWidgetType() and not target.property(b'_effect'):
                target.setProperty(b'_effect',QVariant(FlexEffect(target)))
                            
            code = animation.data
            try:
                resolved = eval(f'f\'{code}\'',None,dict(self.ctxOf(target,ctx)))
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
                    expression = self.ctx.create(code,locals=ctx)
                    if not animation.prop.startswith('__effect_'):
                        ani = QObjectPropertyBinding.create( target, animation.prop, expression ,readOnly=True)
                    else:
                        effect = target.property(b'_effect')
                        ani = QObjectPropertyBinding.create( effect, str(animation.prop)[9:], expression ,readOnly=True)
                        
                    self.animations.append( ani )
                    ani.update(expression.value)
                    
                    
            except Exception as e:
                log.error('ошибка при настройки анимации: объект(%s), свойство(%s), выражение(%s): %s' % (animation.objectID,animation.prop,animation.data,e) )
            
    def signals(self, obj, objectID: str = None,ctx:dict = None):
        from .qtac import QObjectSignalHandler

        if not obj:
            return
        
        if not self.session:
            return
        
        if not objectID:
            objectID = obj.objectName() 
        
        if ctx is None:
            ctx = { }
                    
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
                    self.slots.append(QObjectSignalHandler(target,signal.signal,code,self.context,self.ctx))
                else:
                    log.error('для события нет объекта: объект(%s), событие(%s), выражение(%s)' % (signal.objectID,signal.signal,signal.data) )
                    # log.warning(f'no {signal.objectID} in {obj.objectName()}')
                    
            except Exception as e:
                log.error('ошибка при настройке события: объект(%s), событие(%s), выражение(%s): %s' % (signal.objectID,signal.signal,signal.data,e) )
                # log.error('error in signal initialization %s(%s)' % (objectID,e) )
                
    def window(self,t:type | str | QWidget,objectID:str = None,ctx: dict = None, baseinstance: Any | None=None, later:bool=False, **kwargs)->'QWidget':
        try:
            from AnyQt import uic
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
                    return 
            elif isinstance(t,QWidget):
                w = t    
            try:
                if not later:
                    self.animate(w,objectID=objectID,ctx=ctx)
                    self.signals(w,objectID=objectID)
                    for q,objectID,ctx in self.queued:
                        try:
                            ctx = dict(ctx)
                            self.animate(q,objectID=objectID,ctx=ctx)
                            self.signals(q,objectID=objectID,ctx=ctx)
                        except Exception as e:
                            log.warning(f'внимание: проблема в отложенном анимировании объекта object({objectID})')
                    self.queued.clear()                        
                else:
                    self.queued.append( (w,objectID,ctx) )
            except exc.SQLAlchemyError as e:
                log.error('error while initializing animations/signals: %s' % (e._message()))
            
            return w
        except Exception as e:
            log.error('error creating window: %s (%s)',t,e)
            
    def object(self,obj:'QObject',objectID:str = None,ctx:dict = None):
        if ctx is None:
            ctx = { }
        try:
            ctx=dict(ctx)
            self.animate(obj,objectID=objectID,ctx=ctx)
            self.signals(obj,objectID=objectID,ctx=ctx)
        except exc.SQLAlchemyError as e:
            log.error('error while initializing animations/signals: %s' % (e._message()))        
        
    
app = _pysca( )

try:
    os.chdir(args.workdir)
    log.debug(f'working dir is {args.workdir}')
except FileNotFoundError as e:
    log.warning('cannot set workdir - not found') 

try:
    app.config( args.conf )
except exc.SQLAlchemyError as e:
    log.error(f'failed to open configuration')

__all__=['app','PYPLC']