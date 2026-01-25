from qtpy.QtWidgets import QMainWindow,QWidget,QStackedWidget,QApplication,QActionGroup
from qtpy.QtCore import Qt,QSettings
from typing import Optional

class Navbar(QMainWindow):  
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCentralWidget(QStackedWidget())
        self.centralWidget().setObjectName("centralwidget")
        settings = QSettings(QSettings.IniFormat, QSettings.UserScope,'com.etalon-kom.ru')
        self.restoreGeometry(settings.value('geometry',self.saveGeometry()))
        self.setToolButtonStyle( Qt.ToolButtonStyle.ToolButtonTextUnderIcon  )
        self._navi = self.addToolBar('Navi')
        self._navi.setFloatable( False )
        self._navi.setMovable( False )
        self._group = QActionGroup(self._navi)
        self._group.setExclusive(True)

    def closeEvent(self,_): 
        settings = QSettings(QSettings.IniFormat, QSettings.UserScope,'com.etalon-kom.ru')
        settings.setValue('geometry',self.saveGeometry())
        QApplication.quit()
    
    def append(self,w: QWidget):
        self.centralWidget().addWidget(w)
        _act = self._navi.addAction( w.windowIcon(), w.windowTitle( ) )
        _act.setActionGroup(self._group)
        _act.setCheckable(True)
        def on_activate( ):
            self.centralWidget().setCurrentWidget(w)
            self.centralWidget().setObjectName(w.objectName())
            self.centralWidget().setStyleSheet(w.styleSheet())
            
        _act.triggered.connect( on_activate )
        for _act in self._navi.actions():
            _act.setVisible(self.centralWidget().count()>1)
        if self.centralWidget().count()==1:
            _act.setChecked(True)
            on_activate()
                
    def tools(self,w: QWidget):
        _tb = self.addToolBar(w.windowTitle())
        _tb.addWidget( w )
        _tb.setFloatable(False)
        _tb.setMovable(False)
    
instance = Navbar( )

def append(w: Optional[QWidget]):
    instance.append(w)
            
def tools(w: Optional[QWidget]):
    instance.tools(w)
    
