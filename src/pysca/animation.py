from AnyQt.QtWidgets import QLabel,QWidget
try:
    from AnyQt.QtCore import Q_FLAGS as pyqtEnum
except:
    from AnyQt.QtCore import  pyqtEnum
from AnyQt.QtCore import QUrl,QTimer,Property,Signal,Slot
from AnyQt.QtGui import QMovie,QPixmap
from enum import Flag,auto
from AnyQt.QtWidgets import QMainWindow
from AnyQt.QtWidgets import QApplication
import sys

class PlaybackHint(Flag):
    Ceaseless = auto()
    Rewind = auto()
    StartOnShow = auto()
    Bounce = auto()
    Reversed = auto()

class Animation(QLabel):
    PlaybackHint = PlaybackHint
    pyqtEnum(PlaybackHint)
    
    Ceaseless = PlaybackHint.Ceaseless    
    StartOnShow = PlaybackHint.StartOnShow
    Rewind = PlaybackHint.Rewind
    Bounce = PlaybackHint.Bounce
    Reversed = PlaybackHint.Reversed
            
    def __init__(self, parent: QWidget=None, *args, **kwargs):
        self._hint = None
        self._running = False
        self._movie = None
        self._touched = False
        self._source = QUrl( )
        super(Animation, self).__init__(parent,*args, **kwargs)

    @Slot(QUrl)
    def setSource(self, url: QUrl ):
        self._source = url
        if url.scheme()=='qrc':
            file = ':'+url.path()
        else:
            file = url.toLocalFile( )
        _preview = QPixmap()
        _preview.load( file )
        if self._movie:
            self._movie.frameChanged.disconnect()
            
        self._movie = QMovie( file )
        self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self._movie.frameChanged.connect( self._frameChanged )
        
        self.resize(_preview.size())
        if self._movie.isValid():
            self.setMovie(self._movie)
            self._movie.jumpToNextFrame()
        else:
            self.setPixmap(_preview)
            
        self._preload( )
            
    def getSource(self)->QUrl:
        return self._source
    
    def getPlaybackHints(self)->PlaybackHint:
        if self._hint: return self._hint.value    
        return 0

    def _preloaded(self,frame:int = -1):
        if self._cache and self._cache.frameCount()>0:
            self._cache.stop( )
            self._cache.disconnect( )
            self._movie.deleteLater( )
            self._movie = self._cache
            self._movie.frameChanged.connect( self._frameChanged )
            self.setMovie(self._movie)
            self.setRunning(self.isRunning())
            self._cache = None
                
    def _preload(self):
        if not self._movie or (self._hint and PlaybackHint.Reversed not in self._hint):
            return
        self._cache = QMovie(self._movie.fileName( ))
        self._cache.setCacheMode(QMovie.CacheMode.CacheAll)
        self._cache.start( )
        self._cache.finished.connect( self._preloaded )        
        self._cache.frameChanged.connect( self._preloaded )
    
    def setPlaybackHints(self,hint: PlaybackHint | int):
        self._hint = PlaybackHint(hint)
        if self._hint and PlaybackHint.Reversed in self._hint and self._movie and self._movie.frameCount()==0:
            self._preload( )
    
    @Slot(bool)
    def setRunning(self,running: bool):
        if not self._movie: return
        
        self._running = running
        
        if running and (not self._hint or PlaybackHint.Reversed not in self._hint):
            self._movie.start()
        else:
            self._movie.stop( )
            if self._hint and PlaybackHint.Reversed in self._hint and running and self._movie.frameCount()>0:
                if self._movie.currentFrameNumber()>0:
                    self._frameChanged( self._movie.currentFrameNumber()-1)
                else:
                    self._frameChanged( self._movie.frameCount()-1 )
            else:
                self._frameChanged(self._movie.currentFrameNumber())
            # if PlaybackHint.Bounce in PlaybackHint(self._hint) and self._movie.currentFrameNumber()>0:
            #     self._movie.jumpToFrame( self._movie.currentFrameNumber()-1 )
        
    def isRunning(self) -> bool:
        if not self._movie: return False
        return self._running

    def _frameChanged(self,frame: int):
        if self._hint and PlaybackHint.Bounce in self._hint and frame>0 and not self.isRunning():
            QTimer.singleShot(self._movie.nextFrameDelay(), lambda: self._movie.jumpToFrame( frame-1 ))
        if self._hint and PlaybackHint.Ceaseless in PlaybackHint(self._hint) and not self.isRunning() and frame!=0:
            if frame<self._movie.frameCount( ):
                QTimer.singleShot(self._movie.nextFrameDelay(), lambda: self._movie.jumpToFrame( frame+1 ))
            else:
                QTimer.singleShot(self._movie.nextFrameDelay(), lambda: self._movie.jumpToFrame( 0 ))
        if self._hint and PlaybackHint.Reversed in self._hint and self.isRunning():
            if frame>0:
                QTimer.singleShot(self._movie.nextFrameDelay(), lambda: self._movie.jumpToFrame( frame-1 ))
            elif self._movie.loopCount()<0:
                QTimer.singleShot(self._movie.nextFrameDelay(), lambda: self._movie.jumpToFrame( self._movie.frameCount()-1 ))

    def isTouched(self)->bool:
        return self._touched 
        
    def mousePressEvent(self, event):
        if (self._movie.currentImage().pixel(event.pos()) & 0xFF00000)>0:
            self._touched = True
            self.touched.emit( self._touched)
    
    def mouseReleaseEvent(self,event):
        self._touched = False 
        self.touched.emit( self._touched  )
            
    touched = Signal(bool,arguments=['on'])
    touch   = Property(bool, isTouched, notify = touched)
    source  = Property(QUrl,getSource,setSource)
    running = Property(bool,isRunning,setRunning)
    playbackHints = Property(PlaybackHint,getPlaybackHints,setPlaybackHints)

if __name__=="__main__":
    import SCADA_qrc
    app = QApplication(sys.argv)
    home = QMainWindow( )
    ani = Animation( home )
    ani.setSource( QUrl("qrc:/SCADA/dcement.mng"))
    ani.setPlaybackHints( PlaybackHint.Reversed)
    home.resize(ani.size())

    ani.touched.connect( ani.setRunning )

    home.show( )

    app.exec()