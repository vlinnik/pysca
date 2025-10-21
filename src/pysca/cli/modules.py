import click
import importlib

@click.group(invoke_without_command=True,help='Настройка загрузки дополнительного модуля')
@click.option('--name',required=True,help='Имя модуля для загрузки')
@click.option('--args',multiple=True,help='Параметры инициализации модуля')
@click.pass_context
def module(ctx,name,args):
    params = { }
    for arg in args:
        key,val = arg.split("=",1)
        params[key] = val
    try:
        # Импортируем модуль по имени
        mod = importlib.import_module(name)
        # Проверяем, есть ли функция initialize
        if hasattr(mod, 'createInstance') and callable(getattr(mod, 'createInstance')):
            instance = mod.createInstance(**params)
            ctx.obj['modules'].append(instance)
            ctx.obj['globals'].update( { name: instance} )
        else:
            click.echo(f"Загружен пользовательский модуль {name}")
            ctx.obj['globals'].update({ name : mod })
    except ImportError:
        click.echo(f"Ошибка: Модуль {name} не найден")
    except Exception as e:
        click.echo(f"Ошибка при выполнении загрузки модуля {name}: {str(e)}")                