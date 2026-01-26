from enum import IntFlag,auto
from qtpy.QtWidgets import QLabel,QWidget
from qtpy.QtCore import QUrl,QTimer,Property,Signal,Slot
from qtpy.QtGui import QMovie,QPixmap
from pysca.helpers import Q_FLAG,Q_ENUM
from typing import Optional,Generator,Iterator
import itertools
import sys

class PlaybackHint(IntFlag):
    Bounce = auto()
    Ceaseless = auto()
    Reversed = auto()
    Rewind = auto()

class pyAnimation(QLabel):
    PlaybackHint= PlaybackHint
    Q_FLAG(PlaybackHint)
    
    Ceaseless = PlaybackHint.Ceaseless    
    Rewind = PlaybackHint.Rewind
    Bounce = PlaybackHint.Bounce
    Reversed = PlaybackHint.Reversed
            
    def __init__(self, parent: Optional[QWidget]=None, *args, **kwargs):
        super().__init__(parent,*args, **kwargs)
        self._hint = 0
        self._running = False                           # анимация включена
        self._movie = None                              # файл анимации
        self._touched = False                           # состояние нажато/нет
        self._lazy = False                              # когда нет возможности прямо сейчас анимацию показать (не загружена еще)
        self._source = QUrl( )
        self._sequence:Optional[Iterator[int]] = None   # генератор возвращает номер кадра для отображения
        self.setSource(QUrl("qrc:///PYSCA/movie.gif"))

    @Slot(bool)
    def setRunning(self,running: bool):
        if not self._movie or (self._running==running and not self._lazy): 
            self._running = running
            self._lazy = True
            return
        
        self._lazy = False
            
        self._running = running
        self._sequence = self._timeline( )
        self._frameChanged( self._movie.currentFrameNumber() )
        
    @Property(bool,fset=setRunning)
    def running(self) -> bool:
        # if not self._movie: return False
        return self._running
        
    @Slot(PlaybackHint)
    def setPlaybackHints(self,hint: PlaybackHint):
        if self._hint!=hint:
            self._lazy=True
        self._hint = hint
        self._sequence = self._timeline( )

    @Property(PlaybackHint,fset=setPlaybackHints)
    def playbackHints(self)->PlaybackHint:
        return PlaybackHint(self._hint)
        
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
            
        # self._movie = QMovie( file )
        # self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
        # self._movie.frameChanged.connect( self._frameChanged )

        if _preview.size().height()>0 and _preview.size().width()>0:
            self.resize(_preview.size())
        # if self._movie.isValid():
        #     self.setMovie(self._movie)
        #     self._movie.jumpToNextFrame()
        # else:
        self.setPixmap(_preview)
            
        self._preload( file )

    @Property(QUrl,fset=setSource)            
    def source(self)->QUrl:
        return self._source

    def isTouched(self)->bool:
        return self._touched 
        
    def is_set(self,value: PlaybackHint )->bool:
        return (self._hint & value) == value 
        
    def mousePressEvent(self, event):
        if self._movie is None: return
        if (self._movie.currentImage().pixel(event.pos()) & 0xFF00000)>0:
            self._touched = True
            self.touched.emit( self._touched)
    
    def mouseReleaseEvent(self,event):
        self._touched = False 
        self.touched.emit( self._touched  )

    def _preloaded(self,frame:int = -1):
        if self._cache is None: return
        if self._cache and self._cache.frameCount()>0:
            self._cache.stop( )
            self._cache.finished.disconnect( )
            self._cache.frameChanged.disconnect( )
            if self._movie is not None: self._movie.deleteLater( )
            self._cache.jumpToFrame(0 if not self.is_set(PlaybackHint.Reversed) else self._cache.frameCount()-1)
            self._movie = self._cache
            self._movie.frameChanged.connect( self._frameChanged )
            self._movie.setPaused(True)
            self.setMovie(self._movie)
            if self._running: self.setRunning(self._running)
            self._cache = None
                
    def _preload(self,file:str):
        # if not self._movie:
        #     return
        self._cache = QMovie(file)
        self._cache.setCacheMode(QMovie.CacheMode.CacheAll)
        self._cache.start( )
        self._cache.finished.connect( self._preloaded )        
        self._cache.frameChanged.connect( self._preloaded )
            
    def _jumpToFrame(self,frame: int):
        if self._movie is None: return
        if self._movie.currentFrameNumber()!=frame:
            self._movie.jumpToFrame(frame)
        
    def _schedule(self, frame: int ):
        if self._movie is None: return
        QTimer.singleShot( max(10,self._movie.nextFrameDelay() ), lambda: self._jumpToFrame( frame ))
    
    def _frameChanged(self,frame: int):
        try:
            if self._sequence:
                self._schedule( next(self._sequence) )
        except StopIteration:
            self._sequence = None

    def _timeline(self)->Optional[Iterator[int]]:            
        if not self._movie:
            return
        
        frame = self._movie.currentFrameNumber()
        seq = list( range(0,self._movie.frameCount()) )
        
        if self.is_set(PlaybackHint.Reversed): seq.reverse()
        if self.is_set(PlaybackHint.Rewind): seq+=seq[:1]
        
        index = seq.index(frame) if frame in seq else 0

        if not self.running:
            if self.is_set(PlaybackHint.Bounce):
                seq = seq[:index+1]
                seq.reverse( )
            else:
                if self.is_set(PlaybackHint.Ceaseless):
                    seq=seq[index:]
                else:
                    seq=seq[-1:]
                
        skip= 1 if len(seq)>0 and seq[0]==frame else 0
        if self.running and self.is_set(PlaybackHint.Ceaseless):
            fwd = seq[skip:]
            if self.is_set(PlaybackHint.Bounce):
                back = list(reversed(seq[:-1]))
                seq = fwd + back
            else:
                seq = fwd
            tl = itertools.cycle(seq)
        else:
            tl = itertools.islice(seq,skip,len(seq))            
        
        return tl

    def changeHint(self, flag: PlaybackHint, on:bool):
        cur = int(self._hint)
        all_mask = sum(PlaybackHint)
        mask = int(flag)
        cur = (cur & ~mask) & all_mask
        if on: cur |= mask
        self.setPlaybackHints( PlaybackHint(cur) )

    def setBounce(self,on:bool):
        self.changeHint( PlaybackHint.Bounce, on )
    def setReversed(self,on:bool):
        self.changeHint( PlaybackHint.Reversed,on )
    def setCeaseless(self,on:bool):
        self.changeHint( PlaybackHint.Ceaseless,on )
    def setRewind(self,on:bool):
        self.changeHint( PlaybackHint.Rewind, on)
    
    @Property(bool,fset = setBounce)
    def bounce(self): return self.is_set(PlaybackHint.Bounce)
    @Property(bool,fset = setCeaseless)
    def ceaseless(self): return self.is_set(PlaybackHint.Ceaseless)
    @Property(bool,fset = setReversed)
    def reversed(self): return self.is_set(PlaybackHint.Reversed)
    @Property(bool,fset = setRewind)
    def rewind(self): return self.is_set(PlaybackHint.Rewind)
    
    touched = Signal(bool,arguments=['on'])
    touch   = Property(bool, isTouched, notify = touched)

Animation = pyAnimation 

if __name__=="__main__":
    from qtpy.QtWidgets import QMainWindow
    from qtpy.QtWidgets import QApplication
    app = QApplication(sys.argv)
    home = QMainWindow( )
    ani = Animation( home )
    ani.setPlaybackHints( PlaybackHint.Ceaseless ) 
    ani.setRunning (True)
    home.resize(ani.size())

    ani.touched.connect( ani.setRunning )

    home.show( )

    app.exec()