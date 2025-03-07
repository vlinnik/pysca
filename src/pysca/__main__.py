
def main():
    from . import app
    from AnyQt.QtCore import QResource
    import argparse
    parser = argparse.ArgumentParser(
                        prog='PYSCA Project',
                        description='Запуск проекта визуализации на Python+Qt',
                        epilog='Пример: python -m pysca')

    parser.add_argument('forms',help='Загружаемые окна',nargs='+')
    parser.add_argument('-w','--workdir',action='store', help='Рабочий каталог проекта')
    parser.add_argument('--conf',action='store', help='Конфигурационная база проекта (переменные, анимации, короткие события)')
    parser.add_argument('--resources',action='store',default='', help='Файл ресурсов')
    parser.add_argument('--start',action='store', help='Какое окно главное')
    parser.add_argument('--init',action='store',default='', help='Выполнить')
    
    args,ignored = parser.parse_known_args()
    
    import os.path
    if os.path.isfile(args.resources):
        QResource.registerResource(args.resources)
    
    _g = globals()
    startup = None
    for file in args.forms:
        w = app.window(file)
        if w:
            _g[w.objectName()] = w
            if startup is None:startup = w
            if args.start==w.objectName():
                startup = w
                
    if args.init:
        with open(args.init) as f:
            exec(f.read(),globals())
            
    if startup: 
        startup.show( )        
        app.start( ctx = globals() )

if __name__=='__main__': 
    main()
