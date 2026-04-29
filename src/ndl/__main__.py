"""Allow `python -m ndl` invocation equivalent to the `ndl` script."""

from ndl.cli.main import app

if __name__ == "__main__":
    app()
