# Homelab Homepage

A lightweight, self-hosted start page for your home server. It shows all your services as clickable cards in groups, and you can edit everything right in the browser. There's no database: all configuration lives in a single YAML file.

## Features

- **Dashboard**: services organized into named groups, each with an emoji icon, a name, a description, and a link.
- **In-browser editor**: add, remove, and reorder groups and services from the UI. Changes are saved straight to `config.yaml`.
- **Emoji picker**: a searchable picker for service icons.
- **16 themes**: Default, Terminal, Nord, Dracula, Solarized, Monokai, Tokyo, Rosé, Gruvbox, Catppuccin, Midnight, Forest, Amber, Ocean, Slate, and Light. Your choice is remembered per browser.
- **Live clock & greeting**: a customizable title, greeting, and subtitle.
- **Tiny footprint**: Flask + Gunicorn and a single HTML template.

## Requirements

- Docker + Docker Compose (recommended), **or** Python 3.12+

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-user>/homepage.git
cd homepage
```

### 2. Create your config

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your own services, or leave the examples and edit them later from the web UI.
`config.yaml` is listed in `.gitignore`, so your hostnames and IPs never get committed.

> **Important:** create `config.yaml` **before** starting the container. If the file is missing, Docker creates an empty *directory* with that name instead and the app won't start.

### 3. Deploy with Docker Compose

```bash
docker compose up -d --build
```

Then open `http://<your-server>:3000`.

To use a different host port, change `"3000:5000"` in `docker-compose.yml`.

### Alternative: run without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p static && cp favicon.svg static/
CONFIG_PATH=./config.yaml gunicorn --bind 0.0.0.0:5000 app:app
```

Then open `http://localhost:5000`.

## Configuration

`config.yaml` has two sections:

```yaml
groups:
- name: Media                     # group heading
  services:
  - name: Jellyfin                # card title
    description: Media server     # small text under the title
    icon: 🎬                       # any emoji
    url: http://192.168.0.10:8096/
site:
  title: Homelab                  # page/header title
  greeting: Welcome back
  subtitle: my server
```

| Environment variable | Default               | Description                     |
|----------------------|-----------------------|---------------------------------|
| `CONFIG_PATH`        | `/config/config.yaml` | Path to the YAML config file    |

## API

| Method | Endpoint      | Description                               |
|--------|---------------|-------------------------------------------|
| GET    | `/api/config` | Returns the current config as JSON        |
| POST   | `/api/config` | Replaces the config with the posted JSON  |

## Project structure

```
app.py               Flask app: serves the UI and the config API
templates/index.html The whole frontend (dashboard, editor, themes)
favicon.svg          Site icon
config.example.yaml  Example config (copy to config.yaml)
Dockerfile           Container image (Gunicorn)
docker-compose.yml   Deployment with config.yaml bind-mounted
```

## Security notes

- There is **no authentication**. Anyone who can reach the page can edit the config through the UI or `POST /api/config`. Run it only on a trusted LAN or behind a reverse proxy that requires a login.
- Keep `config.yaml` out of version control. Use `config.example.yaml` as the template.
