import logging

def console(name: str,level = logging.DEBUG)->logging.Logger:
    """создать логгер на консоль с цветовым выделением
    
    можно вместо этого:
    .. highlight:: python
    .. code-block:: python
        
    logging.basicConfig( format = '%(name)s.%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.DEBUG )    

    Args:
        name (str): имя логгера
        level (_type_, optional): уровень логгера. logging.DEBUG.

    Returns:
        logging.Logger: использовать для вывода отладочных сообщениий
    """
    class ColoredFormatter(logging.Formatter):
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "%(name)s.%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: yellow + format + reset,
            logging.WARNING: red + format + reset,
            logging.ERROR: bold_red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    stream = logging.StreamHandler()
    stream.setFormatter(ColoredFormatter())
    stream.setLevel(level)
    ret = logging.getLogger(name)
    ret.setLevel(level)
    ret.addHandler(stream)
    return ret
