import typer

app = typer.Typer(help="NightShift kernel CLI.")


@app.callback(invoke_without_command=True)
def root() -> None:
    pass
