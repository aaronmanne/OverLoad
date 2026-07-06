#!/usr/bin/env python3
"""
overload – CLI entry point

Usage examples
--------------
  python overload.py serve                          # defaults: adversarial, 512 KB, port 5000
  python overload.py serve --strategy flood --size 1024 --port 8080
  python overload.py generate --strategy maze --size 256 --output payload.html
  python overload.py preview --strategy injection
"""

import click
import os
import sys


@click.group()
def cli():
    """OverLoad – LLM context window flood toolkit."""


@cli.command()
@click.option("--strategy", default="adversarial",
              type=click.Choice(["flood", "injection", "maze", "adversarial"]),
              show_default=True,
              help="Overload strategy.")
@click.option("--size", "size_kb", default=512, show_default=True,
              help="Approximate payload size in KB.")
@click.option("--port", default=5000, show_default=True,
              help="TCP port to listen on.")
@click.option("--host", default="0.0.0.0", show_default=True,
              help="Bind address.")
@click.option("--no-cache", is_flag=True, default=False,
              help="Regenerate payload on every request (slower but fresh each time).")
def serve(strategy, size_kb, port, host, no_cache):
    """Start the HTTP server and serve the payload page."""
    os.environ["OVERLOAD_STRATEGY"] = strategy
    os.environ["OVERLOAD_SIZE_KB"]  = str(size_kb)
    os.environ["PORT"]              = str(port)
    os.environ["HOST"]              = host
    os.environ["OVERLOAD_CACHE"]    = "0" if no_cache else "1"

    click.echo(f"[overload] strategy={strategy}  size={size_kb} KB  port={port}")
    click.echo(f"[overload] Payload URL -> http://localhost:{port}/payload")
    click.echo(f"[overload] Dashboard   -> http://localhost:{port}/")

    # Import here so env vars are set first
    from server import app
    app.run(host=host, port=port, debug=False)


@cli.command()
@click.option("--strategy", default="adversarial",
              type=click.Choice(["flood", "injection", "maze", "adversarial"]),
              show_default=True)
@click.option("--size", "size_kb", default=512, show_default=True,
              help="Approximate payload size in KB.")
@click.option("--output", default=None,
              help="Write HTML to this file instead of stdout.")
def generate(strategy, size_kb, output):
    """Generate the payload and write it to a file or stdout."""
    from payload_generator import generate_payload
    from server import _PAYLOAD_TEMPLATE
    from flask import Flask
    import time

    click.echo(f"[overload] Generating {size_kb} KB {strategy!r} payload …", err=True)
    body = generate_payload(strategy=strategy, size_kb=size_kb)

    _app = Flask(__name__)
    with _app.app_context():
        from flask import render_template_string
        html = render_template_string(
            _PAYLOAD_TEMPLATE,
            payload=body,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            size_kb=f"{len(body.encode('utf-8'))/1024:.1f}",
            strategy=strategy,
        )

    actual_kb = len(html.encode("utf-8")) / 1024
    click.echo(f"[overload] Done – actual size {actual_kb:.1f} KB", err=True)

    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(html)
        click.echo(f"[overload] Written to {output}", err=True)
    else:
        sys.stdout.write(html)


@cli.command()
@click.option("--strategy", default="adversarial",
              type=click.Choice(["flood", "injection", "maze", "adversarial"]),
              show_default=True)
@click.option("--lines", default=60, show_default=True,
              help="Number of lines to preview.")
def preview(strategy, lines):
    """Print the first N lines of a generated payload to stdout."""
    from payload_generator import generate_payload
    click.echo(f"[overload] Generating preview (strategy={strategy!r}) …", err=True)
    body = generate_payload(strategy=strategy, size_kb=16)
    all_lines = body.splitlines()
    for line in all_lines[:lines]:
        click.echo(line)
    if len(all_lines) > lines:
        click.echo(f"\n… ({len(all_lines) - lines} more lines)")


if __name__ == "__main__":
    cli()
