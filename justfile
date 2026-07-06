set dotenv-load := true
set shell := ["bash", "-euo", "pipefail", "-c"]

# Check for required tools
_ := require("uv")

[private]
default:
    @just --list

# Install and update dependencies
[group('development')]
install *args:
    uv lock --upgrade
    uv sync {{ args }}

# Run the development server on port 8001
[group('development')]
[working-directory("src")]
run:
    uv run python -c "from aiohttp import web; from c3queue import main; web.run_app(main(), port=8001)"

# Run the production server with gunicorn on unix socket
[group('production')]
[working-directory("src")]
server:
    uv run gunicorn --bind unix:/run/gunicorn/c3queue --worker-class aiohttp.GunicornWebWorker c3queue:main
