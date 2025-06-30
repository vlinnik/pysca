from AnyQt.QtWidgets import QWidget, QGraphicsBlurEffect,QGraphicsEffect,QGraphicsOpacityEffect,QGraphicsColorizeEffect,QGraphicsDropShadowEffect
from AnyQt.QtGui import QPalette
from AnyQt.QtCore import Qt,QObject,QPropertyAnimation,Property #,Signal,Slot

from enum import Flag,Enum,auto
try:
    from AnyQt.QtCore import Q_FLAGS as pyqtEnum
except:
    from AnyQt.QtCore import  pyqtEnum

class _AffineEffect(QGraphicsEffect):
    def __init__(self, angle:float=None, parent = ...):
        super().__init__(parent)
        self._angle = angle
        self._scale = ()
        self._move = ()
        
    def rotate(self,angle: float):
        if self._angle == angle:
            return
        self._angle = angle
        self.update( )
    
    def move(self,sx:float=None,sy:float=None):
        if not sx and not sy:
            self._move = ()
        else:            
            self._move = ( sx if sx else 0, sy if sy else 0 )
        self.update( )
    
    def moveX(self,offset:float):
        self.move( sx=offset )
        
    def moveY(self,offset:float):
        self.move( sy=offset)
        
    def scale(self,x: float=None,y:float=None ):
        if not x and not y:
            self._scale=()
        self._scale = (x if x else 1,y if y else 1)
    
    def draw(self, painter):
        pixmap,offset = self.sourcePixmap (Qt.CoordinateSystem.LogicalCoordinates)

        painter.setRenderHint(painter.RenderHint.Antialiasing,True)
        painter.setRenderHint(painter.RenderHint.SmoothPixmapTransform,True)
        transform = painter.worldTransform()
        
        if self._angle is not None or self._scale:
            transform.translate( pixmap.width()/2,pixmap.height()/2)
            
        #rotate, origin center 
        if self._angle is not None:
            transform.rotate(self._angle)
        #scale
        if self._scale: 
            transform.scale(self._scale[0],self._scale[1])
        #move        
        if self._move: 
            transform.translate(self._move[0],self._move[1])
            
        if self._angle is not None or self._scale:
            transform.translate( -pixmap.width()/2, -pixmap.height()/2 )
        
        painter.setWorldTransform(transform,False)
        painter.drawPixmap(offset,pixmap)

class EffectType(Enum):
    Nothing = 0
    Blur = 1
    Opacity = 2
    Glow = 3
    Colorize = 4
    Rotate = 5
    MoveX = 6
    MoveY = 7
    MirrorX = 8
    MirrorY = 9

class FlexEffect(QObject):
    EffectType = EffectType
    pyqtEnum(EffectType)
    
    def __init__(self,target:QWidget = None):
        super(QObject,self).__init__( parent = target )
        self.target = target
        self._effect = EffectType.Nothing
        self._power:float = 1
        self._strength:float = 0
        self._strength_:float = 0
        self._animated: bool = True
        self._active: bool = True
        self._deactivating: bool = False
        self._animation = QPropertyAnimation(self)
        self._animation.setTargetObject(self)
        self._animation.setPropertyName(b'power')
        self._animation.setDuration(200)
        self._push = 0
    
    def push(self, effect: QGraphicsEffect ):
        self._push += 1 
        self.target.setGraphicsEffect(effect)

    def pop(self):
        if not self._push:
            return
        self._push -= 1
        if not self._push: 
            effect = self._effect
            self._effect = EffectType.Nothing
            self.target.setGraphicsEffect(None)
            self.set_effect(effect)
    
    def get_duration(self)->int:
        return self._animation.duration( )
    
    def set_duration(self,x:int):
        self._animation.setDuration(x)
        if x<=0: self._animated = False
        else: self._animated = True
            
    def get_active(self)->bool:
        return self._active
    
    def set_active(self,x: bool):
        if x==self._active:
            return
        self._active = x
        self._strength_ = 0
        geffect:QGraphicsEffect = self.target.graphicsEffect()
        
        if not geffect or self._push: return
        
        if self._animated:
            self._deactivating = not x
            self._power = 0 if x else 1
            self._apply( )
            self._animation.stop( )
            self._animation.setStartValue( 0 if x else 1 )
            self._animation.setEndValue( 1 if x else 0 )
            self._animation.start( )
            return
        
        geffect.setEnabled(x)
                

    def get_effect(self)->EffectType:
        return self._effect

    def set_effect(self,effect: EffectType):
        if not isinstance(effect,EffectType):
            effect = EffectType(effect)
        if self._effect==effect:
            return
        self._effect = effect
        if self._push:
            return
        if effect==EffectType.Nothing:
            self.target.setGraphicsEffect(None)
        elif effect==EffectType.Opacity:
            self.target.setGraphicsEffect(QGraphicsOpacityEffect(self))
        elif effect==EffectType.Blur:
            self.target.setGraphicsEffect(QGraphicsBlurEffect(self))
        elif effect==EffectType.Colorize:
            self.target.setGraphicsEffect(QGraphicsColorizeEffect(self))
        elif effect==EffectType.Glow:
            self.target.setGraphicsEffect(QGraphicsDropShadowEffect(self))
        elif effect==EffectType.Rotate or effect==EffectType.MoveX or effect==EffectType.MoveY or effect==EffectType.MirrorX or effect==EffectType.MirrorY:
            self.target.setGraphicsEffect(_AffineEffect(parent=self))
            
        self._apply( )
    
    def get_strength(self)->float:
        return self._strength

    def set_strength(self,x: float ):
        self._strength_ = self._strength
        self._strength = x
        if self._push:
            return
        if self._animated:
            self._animation.stop()
            self._animation.setStartValue(0)
            self._animation.setEndValue(1)
            self._animation.start()
        else:
            self._apply( )
    
    def get_power(self)->float:
        return self._power
    
    def set_power(self,x:float):
        self._power = x
        if x==0 and self._deactivating:
            self._deactivating = False
        self._apply( )
        print(f'{x}')
        
    def _apply(self):
        strength = (self._strength - self._strength_)*self._power + self._strength_
        geffect:QGraphicsEffect = self.target.graphicsEffect()
        if not geffect or self._push:
            return
        
        if self._effect==EffectType.Blur:
            blur:QGraphicsBlurEffect = geffect
            blur.setBlurRadius(strength)
        if self._effect==EffectType.Opacity:
            opacity:QGraphicsOpacityEffect = geffect
            opacity.setOpacity( 1.0 - self._power )
        if self._effect==EffectType.Colorize:
            colorize:QGraphicsColorizeEffect = geffect
            p:QPalette = self.target.palette()
            group:QPalette.ColorGroup = QPalette.Normal
            if not self.target.isActiveWindow(): group = QPalette.Inactive
            if not self.target.isEnabled(): group = QPalette.Disabled
            colorize.setStrength( self._power)
            colorize.setColor(p.color(group, QPalette.ColorRole.Shadow))
        if self._effect==EffectType.Glow:
            shadow:QGraphicsDropShadowEffect = geffect
            p:QPalette = self.target.palette()
            group:QPalette.ColorGroup = QPalette.Normal
            if not self.target.isActiveWindow(): group = QPalette.Inactive
            if not self.target.isEnabled(): group = QPalette.Disabled
            shadow.setBlurRadius(strength)
            shadow.setOffset(0,0)
            shadow.setColor( p.color(group,QPalette.ColorRole.Highlight))
        if self._effect==EffectType.Rotate and isinstance(geffect,_AffineEffect):
            rotate:_AffineEffect = geffect
            rotate.rotate(strength)
        if self._effect==EffectType.MoveX:
            moveX:_AffineEffect = geffect
            moveX.moveX(strength)
        if self._effect==EffectType.MoveY:
            moveY:_AffineEffect = geffect
            moveY.moveY(strength)
        if self._effect==EffectType.MirrorX:
            scale:_AffineEffect = geffect
            scale.scale( x=-1 )
        if self._effect==EffectType.MirrorY:
            scale:_AffineEffect = geffect
            scale.scale( y=-1 )
                        
        geffect.setEnabled(self._active or self._deactivating)
            
    power = Property(float, get_power, set_power )
    strength = Property(float,get_strength,set_strength)
    effect = Property(int,get_effect,set_effect)
    active = Property(bool,get_active,set_active )
    duration = Property(int,get_duration,set_duration)
        
if __name__=='__main__':
    from AnyQt.QtWidgets import QApplication,QCheckBox
    app = QApplication([])
    win = QWidget( )
    target = QCheckBox('activate',parent=win)
    flex = FlexEffect( target )
    flex.set_duration(0)
    flex.set_effect(EffectType.Opacity)
    flex.set_strength(1)
    target.setChecked(flex.get_active( ))
    target.toggled.connect(flex.set_active)
    win.show( )
    app.exec( )