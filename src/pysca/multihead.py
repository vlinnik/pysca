from qtpy.QtWidgets import QMainWindow,QWidget,QApplication,QActionGroup,QAction,QToolBar,QVBoxLayout
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon,QScreen

class PageInfo():
    def __init__(self,page: QWidget, title:str=None, icon: QIcon=None,):
        self.screen:'Container' = None
        self.title = title if title is not None else page.windowTitle()
        self.icon = icon if icon is not None else page.windowIcon()
        self.page = page

class Container(QMainWindow):
    def __init__(self, manager:'Manager',parent = None):
        super().__init__(parent)    
        _navi = self.addToolBar('Навигация')
        _navi.setObjectName('navi')
        _navi.setFloatable( False )
        _navi.setMovable( False )
        _navi.setToolButtonStyle( Qt.ToolButtonStyle.ToolButtonTextUnderIcon  )
        
        self.setCentralWidget(QWidget())
        self.centralWidget().setObjectName("centralwidget")
        self.setProperty("style","container")
        self.centralWidget().setLayout(QVBoxLayout())
        self.centralWidget().layout().setContentsMargins(0,0,0,0)
        
        _navgroup = QActionGroup(self)
        _navgroup.setObjectName('navgroup')
        
        self._navi:QToolBar = _navi
        self._navgroup = _navgroup
        _navgroup.triggered.connect( self.triggered )
        self.manager = manager
        self._page = None
        
    def append(self,title: str, icon: QIcon):
        action = self._navi.addAction(icon,title)
        action.setCheckable(True)
        self._navgroup.addAction(action)
        
    def empty(self):
        return self._page==None 
    
    def activate(self,widget: QWidget,index:int = None):
        self.deactivate( self._page )
        self._page = widget
        if widget:
            self.centralWidget().layout().addWidget(widget)
            widget.setParent(self.centralWidget())
            widget.show( )
        if index is not None:
            self._navgroup.actions()[index].setChecked(True)
            
    def deactivate(self,widget: QWidget,index:int = None):
        if self._page is not None and widget==self._page:
            self._page.hide()
            self._page.setParent(None)
            self.centralWidget().layout().removeWidget(self._page)
            self._page = None
        if index is not None:
            self._navgroup.actions()[index].setChecked(False)
        
        
    def triggered(self,action:QAction):
        index = self._navgroup.actions().index(action)
        if action.isChecked():
            self.manager.activate( index, self )
        else:
            self.manager.deactivate(index, self)

class Manager():
    def __init__(self):
        self.screens:list[Container] = []
        self.pages:list[PageInfo] = []
        app:QApplication = QApplication.instance()
        self.primaryScreen:QMainWindow = None
        
        if app is not None:
            for s in app.screens():
                self.screenAdded( s )
                
            app.screenAdded.connect(self.screenAdded)
            app.screenRemoved.connect(self.screenRemoved)
            self.primaryScreen = self.screens[0]
        else:
            print('Warning: QApplication instance not found. Multihead manager will not work.')
            
    def screenAdded(self,screen: QScreen):
        container = Container( self )
        self.screens.append( container )
        container.setWindowTitle( f'[{screen.name()}]' )
        container.show()
        container.setGeometry(screen.geometry())
        if len(self.screens)==1: container.closeEvent = lambda _: QApplication.instance().quit()
        
        used = False
        for p in self.pages:
            container.append(p.title,p.icon)
            if p.screen is None and not used:
                container.activate(p.page,self.pages.index(p))
                p.screen = container
                used = True
    
    def screenRemoved(self,screen: QScreen):
        for p in self.pages:
            if p.screen is not None and p.screen.screen() == screen:
                container = p.screen
                self.deactivate(self.pages.index(p),container)
                p.screen = None
                container.deleteLater()
                
    
    def activate(self,index: int,container: Container ):
        old_screen = self.pages[index].screen
        self.deactivate(index,old_screen)
        for p in self.pages:
            if p.screen == container:
                container.deactivate(p.page)
                if old_screen is not None: 
                    old_screen.activate( p.page,self.pages.index(p) )
                p.screen = old_screen
        container.activate(self.pages[index].page,index)
        self.pages[index].screen = container
        

    def deactivate(self,index:int,container: Container):
        if container is not None:
            container.deactivate(self.pages[index].page,index)
        self.pages[index].screen = None
        
    def append(self,page: QWidget,title: str = None,icon: QIcon = None):
        title = title if title is not None else page.windowTitle()
        icon = icon if icon is not None else page.windowIcon()
        self.pages.append(PageInfo(page,title,icon))
        active = False
        for c in self.screens:
            c.append(title,icon)
            if c.empty() and not active:
                self.activate(len(self.pages)-1,c)
                active = True

manager = Manager( )
instance = manager.primaryScreen

def append(w: QWidget,title: str=None,icon: QIcon=None):
    manager.append(w,title,icon)

def tools( w: QWidget):
    _tb = instance.addToolBar(w.windowTitle())
    _tb.addWidget( w )
    _tb.setFloatable(False)
    _tb.setMovable(False)
