from typing import Callable
from AnyQt.QtWidgets import QWidget
from AnyQt.QtCore import QObject

def custom_widget( ui_file: str, base: type = QWidget ): 
    """Использование на окне пользовательских виджетов, получаемых из ui-файлов. Применяется в связке с custom_widget_plugin
    
    Пример: на форме есть однотипные элементы состоящие из кнопки on & off. Можно создать ON_OFF.ui.
    Для доступности в QtDesigner необходимо создать файл оканчивающийся на plugin.py, например widgetsplugin.py, 
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
    from AnyQt import uic
    
    class __CustomWidget(base):
        def __init__(self,parent: QWidget = None,*args,**kwargs):
            from pysca import app
            super().__init__(parent,*args,**kwargs)
            uic.loadUi(ui_file,self)
            self.setParent(parent)
            app.window(self,self.objectName(),self._ctx(),later=True)        
        def _ctx(self):
            for key in self.dynamicPropertyNames():
                yield bytearray(key).decode(),self.property(key)

    return __CustomWidget

def custom_widget_plugin(widget: str | type, name:str,is_container:bool = False, group: str='PYSCA', include: str='widgetsplugin', whatsThis:str='', toolTip: str=''):
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
    from AnyQt.QtDesigner import QPyDesignerCustomWidgetPlugin
    from AnyQt.QtGui import QIcon
    from AnyQt.QtWidgets import QWidget
    from AnyQt import uic
    
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
