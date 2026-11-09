# Self-hosting

VitalFrame runs entirely locally. Two options.

## Option A — Python (any machine)

```bash
pip install -e ".[server]"
vitalframe sample --output config.yaml
# edit config.yaml to add your real sources
vitalframe ingest --config config.yaml     # populate the store
vitalframe serve --config config.yaml --port 8899
# open http://localhost:8899/
```

`serve` builds and serves the dashboard, rebuilding it on a timer. The dashboard
itself is a static file, so you can also `vitalframe build` and serve `dashboard.html`
with nginx, Caddy, or any static host behind your own auth/reverse proxy.

## Option B — Docker

```bash
docker compose up --build
# dashboard at http://localhost:8899/
```

`docker-compose.yml` mounts `./data` (the SQLite store + rendered dashboard) and runs
the server. Place your `config.yaml` (with real sources) in the project root or mount
it; the container reads `config.yaml` by default.

```yaml
# docker-compose.yml (excerpt)
services:
  vitalframe:
    build: .
    ports: ["8899:8899"]
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
```

## Security notes

- The server has **no authentication**. Bind to `127.0.0.1` (or put it behind a
  reverse proxy with auth) if exposing beyond your LAN.
- Keep `config.yaml` and the SQLite store out of any public share.
- The rendered dashboard embeds health data inline — treat the file as sensitive.
- Secrets in `config.yaml` should use `${ENV_VAR}` expansion, not literal values.
