from qtpy.QtWidgets import QMainWindow,QWidget,QStackedWidget,QApplication,QActionGroup
from qtpy.QtCore import Qt,QSettings

instance = QMainWindow( )
instance.setCentralWidget(QStackedWidget())
instance.centralWidget().setObjectName("centralwidget")

settings = QSettings(QSettings.IniFormat, QSettings.UserScope,'com.etalon-kom.ru')
instance.restoreGeometry(settings.value('geometry',instance.saveGeometry()))

_navi = instance.addToolBar('Navi')
_navi.setFloatable( False )
_navi.setMovable( False )
_group = QActionGroup(_navi)
_group.setExclusive(True)

instance.setToolButtonStyle( Qt.ToolButtonStyle.ToolButtonTextUnderIcon  )

def append(w: QWidget):
    instance.centralWidget().addWidget(w)
    _act = _navi.addAction( w.windowIcon(), w.windowTitle( ) )
    _act.setActionGroup(_group)
    _act.setCheckable(True)
    def on_activate( ):
        instance.centralWidget().setCurrentWidget(w)
        instance.centralWidget().setObjectName(w.objectName())
        instance.centralWidget().setStyleSheet(w.styleSheet())
        
    _act.triggered.connect( on_activate )
    for _act in _navi.actions():
        _act.setVisible(instance.centralWidget().count()>1)
    if instance.centralWidget().count()==1:
        _act.setChecked(True)
        on_activate()
            
def tools(w: QWidget):
    _tb = instance.addToolBar(w.windowTitle())
    _tb.addWidget( w )
    _tb.setFloatable(False)
    _tb.setMovable(False)

def _closeEvent(_): 
    settings.setValue('geometry',instance.saveGeometry())
    QApplication.quit()
    
instance.closeEvent=_closeEvent