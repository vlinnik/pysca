import os
from qtpy import API_NAME
from qtpy.QtCore import QResource
from qtpy.QtWidgets import QWidget
from loguru import logger
from types import ModuleType
from typing import Union,Optional,Tuple,List
from enum import IntEnum,IntFlag
from pathlib import Path
try:
    #пример использования для Qt Designer в конце файла 
    if API_NAME == 'PyQt5':
        from PyQt5.QtCore import Q_FLAG as Q_FLAG
        from PyQt5.QtCore import Q_ENUM as Q_ENUM
        from PyQt5.QtCore import pyqtSignal as Signal,pyqtSlot as Slot
    elif API_NAME == 'PyQt6':
        from PyQt6.QtCore import pyqtEnum as Q_ENUM
        from PyQt6.QtCore import pyqtEnum as Q_FLAG
        from PyQt6.QtCore import pyqtSignal as Signal,pyqtSlot as Slot
    elif API_NAME == 'PySide6':
        from PySide6.QtCore import QFlag as Q_FLAG 
        from PySide6.QtCore import QEnum as Q_ENUM
        from PySide6.QtCore import Signal,Slot
except:
    def __stub(_: Union[IntEnum,IntFlag,type]):
        logger.error(f'Проблема в инициализации Q_FLAG/Q_ENUM, {API_NAME}')
    Q_FLAG = __stub
    Q_ENUM = __stub    

def _autoload_modules_for(ui_dir: str)->List[ModuleType]:
    imported: List[ModuleType] = []
    if Path(ui_dir).joinpath('__init__.py').exists():
        logger.info( f'В каталоге с пользовательскими ui-виджетами есть __init__.py')
        import importlib
        try:
            mod = importlib.import_module( Path(ui_dir).name )
            imported.append(mod)
        except Exception as e:
            logger.warning(f'Что-то пошло не так: {e}')
            pass
    return imported
    

def register_user_widgets(ui_dir: str,ctx:dict,*,include:str|None = None):
    """В указанной  папке взять все ui-файлы и сделать из них custom_widget_plugin
    
    Если include указать, то необходимо чтобы в том файле были классы, которые совпадают
    с именем ui-файла (UserWidget.ui -> class UserWidget чувствителен к регистру). Имя класса
    в ui файлах также должно совпадать. Можно указать имя, откуда вызван register_user_widgets,
    т.к. в нем создаются эти классы через custom_widget.
    
    Args:
        ui_dir (str): где искать ui файлы
        ctx (dict): всегда = globals()
        include (str | None, optional): В генерируемом python-коде откуда имортировать реализацию. Defaults to None.
    """
    if not os.path.exists(ui_dir) or not os.path.isdir(ui_dir):
        logger.error( f'Каталог {os.path.abspath(ui_dir)} не найден' )
        return 

    imported: List[ModuleType] = []
    if "DIYED_PROJECT" in os.environ or "PYSCARUNTIME" in os.environ:   #загрузка пользовательской реализации нужна (в qt-designer например не нужна)
        imported = _autoload_modules_for(ui_dir=ui_dir)

    for filename in os.listdir(ui_dir):
        filepath = os.path.join(ui_dir, filename)
        if os.path.isfile(filepath):
            name, ext = os.path.splitext(filename)
            if ext in ['.ui']:  # уточни нужные расширения
                var_name = f"__{name}Plugin"
                try:
                    widget = custom_widget(filepath,imported=imported)
                    ctx[var_name] = custom_widget_plugin(widget, name=name,include=include or name.lower())
                    ctx[name] = widget
                except Exception as e:
                    logger.error(f'Ошибка при инициализации пользовательского элемента {name} - {e}')                    

def user_widgets(ui_dir: str,ctx:dict,*args,**kwargs):
    """В указанной  папке взять все ui-файлы и сделать из них custom_widget.
    параметр ctx должен быть =globals(), в нем добавляются имена классов, которые 
    создаются (user_widgets например в pyscawidgets.py, чтобы пользовательские виджеты как 
    будто часть pyscawidgets)
        
    Args:
        ui_dir (str): где искать ui файлы
        ctx (dict): всегда = globals()
    """
    if not os.path.exists(ui_dir) or not os.path.isdir(ui_dir):
        logger.error( f'Каталог {os.path.abspath(ui_dir)} не найден' )
        return 
    
    imported = _autoload_modules_for(ui_dir=ui_dir)
        
    for filename in os.listdir(ui_dir):
        filepath = os.path.join(ui_dir, filename)
        if os.path.isfile(filepath):
            name, ext = os.path.splitext(filename)
            if ext in ['.ui']:  # уточни нужные расширения
                try:
                    widget = custom_widget(filepath,imported=imported)
                    ctx[name] = widget
                except Exception as e:
                    logger.error(f'Ошибка при инициализации пользовательского элемента {name} - {e}')                    

def resolve_class_info(ui_path:str)->Tuple[Optional[str],Optional[str],List[str]]:  #получить базовый класс и имя из ui-файла по тегам <class>&<widget>
    import xml.etree.ElementTree as ET
    tree = ET.parse(ui_path)
    root = tree.getroot()
    class_tag = root.find('class')
    widget_tag = root.find('widget')
    resources_tag = root.find('resources')
    class_name = class_tag.text if class_tag is not None else None
    base_class_name = widget_tag.attrib.get('class',None) if widget_tag is not None else None
    resources: List[str] = []
    if resources_tag:
        for qrc in resources_tag.findall('include'):
            file = qrc.attrib.get('location',None)
            if file: resources.append(str(Path(ui_path).parent.joinpath(file).resolve()))
    return class_name,base_class_name,resources

def resolve_base_type(class_name: Optional[str]=None, base_class_name: Optional[str]=None,imported: List[ModuleType] = [])->Optional[type]:  #получить базовый класс и имя из ui-файла по тегам <class>&<widget>
    import qtpy.QtWidgets as QtWidgets
    cls = None
    if class_name is not None:
        hints: List[ModuleType] = imported
        try:
            from pysca.config import config
            hints += config().imported
        except:
            pass
        for mod in hints:
            if hasattr(mod,class_name):
                cls = getattr(mod,class_name)
                break
    if cls is None and base_class_name:
        if hasattr(QtWidgets,base_class_name):
            cls = getattr(QtWidgets,base_class_name)
    return cls

def custom_widget( ui_file: str, *, base: Optional[type] = None, imported: List[ModuleType]= [] ): 
    """Использование на окне пользовательских виджетов, получаемых из ui-файлов. Применяется в связке с custom_widget_plugin
    
    Пример: на форме есть однотипные элементы состоящие из кнопки on & off. Можно создать ON_OFF.ui.
    Для доступности в QtDesigner необходимо создать файл оканчивающийся на plugin.py, например widgetsplugin.py , 
    в котором должна быть строка
    
    ON_OFF_PLUGIN = custom_widget_plugin('ON_OFF.ui',include='widgets',name='ON_OFF')
    
    И файл widgets.py (как в параметре include), в котором должна быть строка
    
    ON_OFF = custom_widget('ON_OFF.ui') #имя переменной должно совпадать с параметром name
    
    Если необходимо добавить свойства, обработчики событий то наследуем класс
    class ON_OFF(custom_widget('ON_OFF.ui')):
        ...
    и потом 
    ON_OFF_PLUGIN = custom_widget_plugin(ON_OFF,include='widgets',name='ON_OFF')
    
    Args:
        ui_file (str): ui-файл, из которого создается пользовательский виджет
        base (type QWidget-derived): от чего наследуется создаваемый класс, default QWidget
    """
    from qtpy import uic
    # from .uic import uic

    class_name,base_class_name,resources = resolve_class_info(ui_file)
    if base is None:
        base = resolve_base_type(class_name,base_class_name,imported=imported)
        # _,base = uic.loadUiType(ui_file)
    
    if base is None:
        base = QWidget
        
    for qrc in resources:
        path = Path(qrc).with_suffix('.rcc')
        if not path.exists():
            logger.warning(f'Файл ресурсов {path.name} не найден')
            continue
        QResource.registerResource(str(path))
        
        
    class UserWidget(base):
        def __init__(self,parent: Optional[QWidget] = None,*args,**kwargs):
            from pysca import app
            super().__init__(parent,*args,**kwargs)
            uic.loadUi(ui_file,self)
            self.setParent(parent)
            app.window(self,objectID=self.objectName(),ctx=self._ctx(),later=True)  
            setup = getattr(self, "setupUi", None) 
            try:
                if callable(setup): setup(**kwargs)
            except Exception as e:
                logger.error(f'Ошибка вызова {self}.setupUi : {e}')
        
        def __str__(self):
            return f'{class_name}({base_class_name})'
                        
        def _ctx(self):
            for key in self.dynamicPropertyNames():
                yield bytearray(key).decode(),self.property(key)

    return UserWidget

def custom_widget_plugin(widget: Union[str,type], name:str,is_container:bool = False, group: str='PYSCA', include: str='widgetsplugin', whatsThis:str='', toolTip: str=''):
    """Создать класс, который позволяет использовать пользовательский виджет в QtDesigner + PyQt5. 
    
    Последовательность действий для использования пользовательских виджетов в QtDesigner + PyQt5
    - создать файл с окончанием на plugin.py, например widgetsplugin.py
    - в нем создаем экземпляр при помощи INSTANCE_PLUGIN = custom_widget_plugin( ... )
    - запускаем QtDesigner: PYQTDESIGNERPATH=<где лежит созданный widgetsplugin.py> qtdesigner

    Args:
        widget (str|type): ui-файл, описывает пользовательский виджет или класс, который создается
        name (str): имя пользовательского виджета
        is_container (bool, optional): пользовательский виджет контейнер.
        group (str, optional): группа, в которой будет отображен пользовательский виджет в интерфейсе QtDesigner. Defaults to 'PYSCA'.
        include (str, optional): что необходимо включить для использования (при генерации с помощью uic). Defaults to 'widgets'.
        whatsThis (str, optional): значение для описания виджета в интерфейсе QtDesigner. Defaults to ''.
        toolTip (str, optional): подсказка для описания виджета в интерфейсе QtDesigner. Defaults to ''.

    Returns:
        НОВЫЙ_КЛАСС: созданный класс-потомок QPyDesignerCustomWidgetPlugin
    """
    from qtpy.QtDesigner import QPyDesignerCustomWidgetPlugin
    from qtpy.QtGui import QIcon
    from qtpy.QtWidgets import QWidget
    
    class __CUSTOM_WIDGET_PLUGIN(QPyDesignerCustomWidgetPlugin):
        def __init__(self, parent = None):
            super().__init__(parent)
            self.initialized = False
            if isinstance(widget,str):
                self.widget = type(name,(custom_widget(widget),),{})
            else:
                self.widget = type(name,(widget,),{})

        def initialize(self, core):
            if self.initialized:
                return

            self.initialized = True

        def isInitialized(self):
            return self.initialized

        def createWidget(self, parent:QWidget = None):
            return self.widget(parent)

        def name(self):
            return name

        def group(self):
            return group

        def includeFile(self):
            return include

        def icon(self):
            return QIcon()

        def toolTip(self):
            return toolTip

        def whatsThis(self):
            return whatsThis
        
        def isContainer(self):
            return is_container
    
    return __CUSTOM_WIDGET_PLUGIN

def user_window( ui_file: str, base: Optional[type] = None ): 
    """Использование пользовательских окон, получаемых из ui-файлов. 
    
    Пример: Однотипные элементы (конвейеры) имеют одинаковое окно для настроек/управления. Можно создать conveyor_dialog.ui.
    
    Наследуем класс (в файле conveyor_dialog.py etc)
    class CONVEYOR_DIALOG(user_window('conveyor_dialog.ui',QDialog)):
        ...
    и потом в событии click() указываем (не забыть в глобальном контексте from conveyor_dialog import CONVEYOR_DIALOG)
    CONVEYOR_DIALOG().exec( )
    Именованные параметры, которые kwargs будут установлены как динамические свойства, например
    CONVEYOR_DIALOG(prefix='CONVEYOR_2').exec( ) диалог будет иметь динамическое свойство prefix, и в анимациях можно
    указывать шаблонное выражение '{prefix}_ON' 
        
    Args:
        ui_file (str): ui-файл, из которого создается пользовательский виджет
        base (type QWidget-derived): от чего наследуется создаваемый класс, default QWidget, должно быть как в ui
    """
    from qtpy import uic
    # from .uic import uic
    class_name,base_class_name,resources = resolve_class_info(ui_file)
    if base is None:
        base = resolve_base_type(class_name,base_class_name)
    
    class __UserWindow(base):
        def __init__(self,parent: Optional[QWidget] = None,*args,**kwargs):
            from pysca import app
            super().__init__(parent,*args)
            uic.loadUi(ui_file,self)
            for key,item in kwargs.items():
                self.setProperty(key,item)
            try:
                setup = getattr(self,'setupUi',None)
                if setup and callable(setup):setup(**kwargs)
            except Exception as e:
                logger.error(f'Что то пошло не так в вызове setupUi для {base}: {e}')
            flags = self.windowFlags()
            self.setParent(parent)
            self.setWindowFlags(flags)
            app.window(self,objectID=self.objectName(),**kwargs)
            
        def _ctx(self):
            for key in self.dynamicPropertyNames():
                yield bytearray(key).decode(),self.property(key)

    return __UserWindow

"""
Пример custom qt-designer widget со свойством Enum/Flag

class PlaybackHints(IntFlag): #Int Enum для Enum-ов
    Ceaseless = auto()
    Rewind = auto()
    StartOnShow = auto()
    Bounce = auto()
    Reversed = auto()

class Demo(QLabel):
    PlaybackHints = PlaybackHints   # для PyQt6 без этого в designer числом показывает значение 
    Q_FLAG(PlaybackHints)   # Q_ENUM для enum
    playbackHintsChanged = Signal(PlaybackHints)
    
    #надо для uic, он использует значения Demo.<значение>  
    Ceaseless = PlaybackHints.Ceaseless 
    Rewind = PlaybackHints.Rewind
    StartOnShow = PlaybackHints.StartOnShow
    Bounce = PlaybackHints.Bounce
    Reversed = PlaybackHints.Reversed
                    
    def __init__(self, parent: QWidget=None, *args, **kwargs):
        super().__init__(parent)
        self._hint = Demo.Ceaseless #uic так же делает
    
    @Slot(PlaybackHints,name='setPlaybackHints')    #так можно несколько вариантов с разными типами параметров сделать
    def setPlaybackHints(self,hint):
        try:
            self._hint = (hint)
            self.playbackHintsChanged.emit(PlaybackHints(hint))
            self.setText(f'{PlaybackHints(hint).name}')
        except Exception as e:
            print(e,file=sys.stderr)
            pass

    @Property(PlaybackHints,fset=setPlaybackHints,designable=True)
    def playbackHints(self):
        return PlaybackHints(self._hint)    #для PyQt6 обязательно cast
"""