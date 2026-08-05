#!/usr/bin/python3
import os
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget
from qtpy.QtDesigner import QPyDesignerCustomWidgetPlugin
from loguru import logger
from pysca import pysca_rcc; pysca_rcc()
from pysca.helpers import register_user_widgets

try:
    from pysca.animation import Animation,PlaybackHint
    class __AnimationPlugin(QPyDesignerCustomWidgetPlugin):

        def __init__(self, parent=None):
            super().__init__(parent)

            self.initialized = False

        def initialize(self, core):
            if self.initialized:
                return

            self.initialized = True

        def isInitialized(self):
            return self.initialized

        def createWidget(self, parent:QWidget):
            w = Animation(parent)
            return w

        def name(self):
            return "pyAnimation"

        def group(self):
            return "PYSCA"

        def icon(self):
            return QIcon()

        def toolTip(self):
            return "Анимационный GIF/WEBP/MNG"

        def whatsThis(self):
            return "Элемент для проигрывания QMovie"

        def isContainer(self):
            return True

        def includeFile(self):
            return "pysca.animation"
except Exception as e:
    logger.opt(depth=1).error(f'Инициализация расширения PYSCA.Animation не удалась: {e}')

try:
    from pysca.runtimetrend import RuntimeTrend
    class __RuntimeTrendPlugin(QPyDesignerCustomWidgetPlugin):

        def __init__(self, parent=None):
            super().__init__(parent)

            self.initialized = False

        def initialize(self, core):
            if self.initialized:
                return

            self.initialized = True

        def isInitialized(self):
            return self.initialized

        def createWidget(self, parent):
            return RuntimeTrend(parent)

        def name(self):
            return "pyRuntimeTrend"

        def group(self):
            return "PYSCA"

        def icon(self):
            return QIcon()

        def toolTip(self):
            return ""

        def whatsThis(self):
            return ""

        def isContainer(self):
            return False

        def includeFile(self):
            return "pysca.runtimetrend"
except Exception as e:
    logger.opt(depth=1).error(f'Инициализация расширения PYSCA.RuntimeTrend не удалась: {e}')

if 'PYSCAWIDGETSPATH' in os.environ: 
    register_user_widgets(os.environ['PYSCAWIDGETSPATH'],globals(),include='pyscawidgets') 
    pass
