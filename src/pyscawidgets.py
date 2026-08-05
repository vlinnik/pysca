#!/usr/bin/python3
import os
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget
from pysca import pysca_rcc,log; pysca_rcc()
from pysca.helpers import user_widgets

# Базовые компоненты PYSCA(анимированный виджет, тренд) + пользовательские виджеты (найденные  os.environ['PYSCAWIDGETSPATH'])

try:
    from pysca.animation import Animation,pyAnimation,PlaybackHint
except Exception as e:
    log.opt(depth=1).error(f'Загрузка PYSCA.Animation не удалась: {e}')

try:
    from pysca.runtimetrend import RuntimeTrend,pyRuntimeTrend
except Exception as e:
    log.opt(depth=1).error(f'Загрузка PYSCA.RuntimeTrend не удалась: {e}')

if 'PYSCAWIDGETSPATH' in os.environ: 
    user_widgets(os.environ['PYSCAWIDGETSPATH'],ctx=globals())
