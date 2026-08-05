from qtpy.QtCore import Qt,Property
from qtpy.QtGui import QColor,QBrush
from qtpy.QtWidgets import QApplication
#pip install PythonQwt or apt install python3-qwt
from typing import List
from datetime import datetime,timedelta
from qwt import QwtPlot,QwtPlotGrid,QwtPlotCurve,QwtPlotItem,QwtScaleDraw,QwtText

class TimeScaleDraw(QwtScaleDraw):
    def __init__(self):
        QwtScaleDraw.__init__(self)
        
    def label(self,value)->QwtText:
        dt = datetime.now()+timedelta(seconds=value)
        return QwtText(dt.strftime('%H:%M:%S'))

class pyRuntimeTrend(QwtPlot):
    def __init__(self, parent = None):
        QwtPlot.__init__(self)
        self.setParent(parent)
        self.setAxisScaleDraw( QwtPlot.xBottom, TimeScaleDraw( ) )

        grid = QwtPlotGrid( )
        grid.attach(self)
        grid.enableXMin(True )
        grid.setPen( QColor(Qt.gray),0.5,Qt.DotLine )
                
        self._pens=[]
        colors=[Qt.red,Qt.green,Qt.cyan,Qt.yellow,Qt.magenta,Qt.blue,Qt.gray]
        for color in colors:
            pen = QwtPlotCurve()
            pen.setRenderHint( QwtPlotItem.RenderAntialiased )
            pen.setPen( QColor(color),2,Qt.SolidLine )
            pen.attach(self)
            self._pens.append(pen)
            
        self._data = [None]*len(colors)  
        self._timerId = None
        self._samples = [ None ]*len(colors)
        self._depth = 60*20 #20 min
        self.setDepth(60*20)
        self.setContentsMargins(10,10,10,10)
        self.setCanvasBackground(QBrush(Qt.darkGray))

    def depth(self):
        return self._depth
    
    def setDepth(self,sec: int):
        self._depth = sec
        self.updateXScale( )
        self.setAxisScale(QwtPlot.xBottom,-sec,0)
        self.setupTimer( )
        
    def setValue(self,index: int,value: float):
        self._data[index] = value
        if not self._samples[index]: self._samples[index] = []
        
    def updateXScale(self):
        dt = self._depth/self.width()
        self._x = [ -dt*i for i in range(self.width()) ]
        self._x.reverse( )
    
    def setupTimer(self):
        if self._timerId: self.killTimer(self._timerId)       
        self._timerId = self.startTimer(  int(self._depth*1000/self.width()))
        
    def timerEvent(self, event):
        for i in range(len(self._data)):
            if self._data[i] is None: continue
            self._samples[i].append(self._data[i])
            if len(self._samples[i])>self.width(): self._samples[i] = self._samples[i][-self.width():]
            self._pens[i].setSamples( self._x[-len(self._samples[i]):], self._samples[i] )
        
        self.axisScaleDraw(QwtPlot.xBottom).invalidateCache()
        self.axisWidget(QwtPlot.xBottom).update()
        self.replot()
        
        return super().timerEvent(event)
    
    def resizeEvent(self, e):
        self.updateXScale( )
        self.setupTimer( )
        return super().resizeEvent(e)

    def pen_0(self):
        return self._data[0] or 0.0
    
    def setPen_0(self,value):
        self.setValue(0,value)

    def pen_1(self):
        return self._data[1] or 0.0
    
    def setPen_1(self,value):
        self.setValue(1,value)
    
    depth = Property(int,depth,setDepth)
    pen_0 = Property(float,pen_0,setPen_0)
    pen_1 = Property(float,pen_1,setPen_1)
    canvasBackground = Property(QBrush,QwtPlot.canvasBackground,QwtPlot.setCanvasBackground)

RuntimeTrend = pyRuntimeTrend
        
if __name__=='__main__':
    app = QApplication( [] )
    w =  RuntimeTrend( )
    w.show( )
    w.setValue(0,50)
    app.exec( )