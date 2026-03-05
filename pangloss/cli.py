"""Command-line interface for Pangloss."""

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Pangloss: Language graph analysis and transformation."""
    pass


@cli.command()
def version():
    """Show version information."""
    click.echo("Pangloss 0.1.0")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
def analyze(input_file):
    """Analyze a language dataset."""
    click.echo(f"Analyzing {input_file}...")


if __name__ == "__main__":
    cli()
