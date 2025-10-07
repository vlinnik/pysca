from qtpy.QtWidgets import QMainWindow,QWidget,QStackedWidget,QApplication
from qtpy.QtCore import Qt,QSettings

instance = QMainWindow( )
instance.setCentralWidget(QStackedWidget())

settings = QSettings(QSettings.IniFormat, QSettings.UserScope,'com.etalon-kom.ru')
instance.restoreGeometry(settings.value('geometry',instance.saveGeometry()))

_navi = instance.addToolBar('Navi')
_navi.setFloatable( False )
_navi.setMovable( False )

instance.setToolButtonStyle( Qt.ToolButtonStyle.ToolButtonTextUnderIcon  )

def append(w: QWidget):
    instance.centralWidget().addWidget(w)
    _act = _navi.addAction( w.windowIcon(), w.windowTitle( ) )
    _act.triggered.connect( lambda: instance.centralWidget().setCurrentWidget(w) )
    for _act in _navi.actions():
        _act.setVisible(instance.centralWidget().count()>1)
            
def tools(w: QWidget):
    _tb = instance.addToolBar(w.windowTitle())
    _tb.addWidget( w )
    _tb.setFloatable(False)
    _tb.setMovable(False)

def _closeEvent(_): 
    settings.setValue('geometry',instance.saveGeometry())
    QApplication.quit()
    
instance.closeEvent=_closeEvent