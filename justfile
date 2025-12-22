set dotenv-load := true

[private]
default:
    @just --list

# Install dependencies
[group('development')]
install *args:
    uv lock --upgrade
    uv sync {{ args }}

# Run the development server at :8001
[group('development')]
[working-directory("src")]
run:
    uv run python -c "from aiohttp import web; from c3queue import main; web.run_app(main(), port=8001)"

# Run the production server with gunicorn
[group('production')]
[working-directory("src")]
server:
    uv run gunicorn --bind unix:/run/gunicorn/c3queue --worker-class aiohttp.GunicornWebWorker c3queue:main
