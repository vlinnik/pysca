import typer

def message(ctx: typer.Context,  *args, styled:bool=True, **kwargs):
    if ctx.obj.get('query') is not None and styled:
        return
    if styled:
        typer.secho(*args,**kwargs,bold=True)
    else:
        typer.echo(*args,**kwargs)
