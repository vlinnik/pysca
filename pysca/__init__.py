from AnyQt.QtWidgets import QApplication
from AnyQt.QtCore import QObject,QResource
import sys,os,glob,re
import logging
import argparse
from typing import Any
from __version__ import version_short as version
from .bindable import Expressions,Property

#работа с базой конфигурации проекта
from sqlalchemy import ForeignKey,String,BLOB,Boolean,create_engine,select,or_,exc
from sqlalchemy.orm import Session,DeclarativeBase,Mapped,mapped_column

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

class _Base(DeclarativeBase):
    pass

class _Variables(_Base):
    __tablename__ = "Variables"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(45))
    type: Mapped[int]
    source: Mapped[str] = mapped_column(String(45))
    address: Mapped[str] = mapped_column(String(128))
    logging: Mapped[bool] = mapped_column(Boolean)
    events: Mapped[bool] = mapped_column(Boolean)

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
log.info(f'initializing pysca {version}')
qApp = QApplication(sys.argv)

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
        self.devices = { }
        self.ctx = Expressions( )
        self.session = None
        self._ = { }
    
    def __findChild(self,o: QObject, path: list[str] ):
        if o is None:
            return None
        
        if o.objectName()!=path[0]:
            return None
        
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

    def start(self,ctx: dict ):
        self._ = ctx
        qApp.exec( )
        
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
        
        remote = 0 
        locals= 0

        for var in session.scalars(vars):
            source = var.source #self.__expand(var.source)
            if source in self.devices:
                dev,_ = self.devices[source]
                # self.var(Subscriber.subscribe(dev,var.address,var.name),var.name)
                remote+=1
            else:
                if var.type==2:
                    self.var(float,var.name)
                elif var.type==1:
                    self.var(bool,var.name)
                elif var.type==3:
                    self.var(str,var.name)
                elif var.type==4:
                    self.var(int,var.name)
                else:
                    raise ValueError('Variable %s type %d not supported' % (str(var.name),int(var.type)))
                locals+=1

        log.debug(f'local variables: {locals}, remote variables {remote}')
        
        rcc_dir = os.path.dirname(os.path.abspath(db))
        log.debug(f'searching resource files in {rcc_dir}')
        rcc_files = glob.glob('*.rcc',root_dir=rcc_dir)
        for rcc in rcc_files:
            log.debug(f'loading resources file {rcc_dir}/{rcc}')
            QResource.registerResource(f'{rcc_dir}/{rcc}')
        
    def animate(self,obj, ctx: dict = None,objectID:str = None ):
        from .qtac import QObjectPropertyBinding

        if not self.session:
            return
        
        if not objectID:
            objectID = obj.objectName() 
            
        if not ctx:
            ctx = { }
        
        if objectID not in ctx:
            ctx[objectID] = obj
            
        animations = select(_Animations).where( or_(_Animations.objectID.startswith(objectID+"."),_Animations.objectID==(objectID)) )
        
        for animation in self.session.scalars(animations):
            target = self.__findChild( obj, animation.objectID.split('.') )
            if target is None:
                log.error('анимируемый объект(%s) не найден' % (animation.objectID))
                continue
            code = animation.data
            try:
                code = re.sub("@(\\w+(\\.\\w+)*)","\\1",code)
                
                if code in self.ctx:
                    self.animations.append(QObjectPropertyBinding.create( target, animation.prop, self.ctx[code]))
                else:
                    expression = self.ctx.create(code)
                    animation = QObjectPropertyBinding.create( target, animation.prop, expression ,readOnly=True)
                    self.animations.append( animation )
                    animation.update(expression.value)
                    
            except Exception as e:
                log.error('ошибка при настройки анимации: объект(%s), свойство(%s), выражение(%s)' % (animation.objectID,animation.prop,animation.data) )
            
    def signals(self, obj, objectID: str = None):
        from .qtac import QObjectSignalHandler

        if not obj:
            return
        
        if not self.session:
            return
        
        if not objectID:
            objectID = obj.objectName() 
            
        signals = select(_Signals).where( or_(_Signals.objectID.startswith(objectID+"."),_Signals.objectID==(objectID)) )
        for signal in self.session.scalars(signals):
            try:
                target = self.__findChild( obj,signal.objectID.split('.') )
                if target:
                    self.slots.append(QObjectSignalHandler(target,signal.signal,signal.data,self.context,self.ctx))
                else:
                    log.warning(f'no {signal.objectID} in {obj.objectName()}')
                    
            except Exception as e:
                log.error('error in signal initialization %s(%s)' % (objectID,e) )
                
    def window(self,t:type | str,objectID:str = None,**kwargs)->'QWidget':
        try:
            from AnyQt import uic
            if isinstance(t,type):
                if len(kwargs)>0:
                    w = t( **kwargs )
                else:
                    w = t( )
            else:
                log.debug('loading form from UI-file (%s)' % (t))
                w = uic.loadUi( t )
                if w is None:
                    log.error('failed to load UI-file') 
                    return     
            try:
                self.animate(w,objectID=objectID)
                self.signals(w,objectID=objectID)
            except exc.SQLAlchemyError as e:
                log.error('error while initializing animations/signals: %s' % (e._message()))
            
            return w
        except Exception as e:
            log.error('error creating window: %s (%s)',t,e)
            
    def object(self,obj:'QObject',objectID:str = None):
        try:
            self.animate(obj,objectID=objectID)
            self.signals(obj,objectID=objectID)
        except exc.SQLAlchemyError as e:
            log.error('error while initializing animations/signals: %s' % (e._message()))        
        
    
pysca = _pysca( )

try:
    os.chdir(args.workdir)
    log.debug(f'working dir is {args.workdir}')
except FileNotFoundError as e:
    log.warning('cannot set workdir - not found') 

try:
    pysca.config( args.conf )
except exc.SQLAlchemyError as e:
    log.error(f'failed to open configuration')

__all__=['pysca']