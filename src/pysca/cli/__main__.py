import click
from . import cli
        
def entry():
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    _ = QApplication([])
    try:
        cli()
    except Exception as e:
        from qtpy.QtWidgets import QMessageBox
        QMessageBox.critical(None,'Что-то пошло не так',f'{e}')
        click.echo(e,err=True)
        import traceback; traceback.print_exc();
    
if __name__ == '__main__':
    entry()