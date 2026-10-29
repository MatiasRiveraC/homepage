# Homelab Homepage

A lightweight, self-hosted start page for your home server. It shows all your services as clickable cards in groups, and you can edit everything right in the browser. There's no database: all configuration lives in a single YAML file.

## Features

- **Dashboard**: services organized into named groups, each with an emoji icon, a name, a description, and a link.
- **In-browser editor**: add, remove, and reorder groups and services from the UI. Changes are saved straight to `config.yaml`.
- **Emoji picker**: a searchable picker for service icons.
- **18 themes**: Default, Terminal, Nord, Dracula, Solarized, Monokai, Tokyo, Rosé, Gruvbox, Catppuccin, Midnight, Forest, Amber, Ocean, Slate, Light, Retro, and Rust gloss. Your choice is remembered per browser.
  Retro is a classic beveled desktop: the page becomes a window on a teal desktop, with a taskbar, a menu and working minimize/restore buttons.
  Rust gloss is a dark glossy window: charcoal title bar with an orange underline, slate controls, orange only for what matters. The Monitor tab follows it.
- **Live clock & greeting**: a customizable title, greeting, and subtitle.
- **Optional Monitor tab**: shows a homelab monitor's web page inside homepage, in the same theme, with a live server-status strip on the dashboard (see [Monitor tab](#monitor-tab-optional)).
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
| `MONITOR_URL`        | *(unset)*             | Base URL of a homelab monitor web page; enables the Monitor tab |
| `MONITOR_TIMEOUT`    | `1800`                | Seconds to wait on the monitor (chat answers can be slow) |

### Monitor tab (optional)

With `MONITOR_URL` set (e.g. `http://<monitor-host>:8088`), homepage gets a **Monitor**
tab and a server-status strip at the top of the dashboard. Homepage passes every request
under `/monitor/` through to that URL, so the monitor keeps its own data, login and
logic; homepage only shows it and applies its current theme. The monitor page must use
relative URLs and support `?embed=1` (hides its own title bar). Chat answers are
streamed through, which is why Gunicorn runs with threads.

## Running as a TrueNAS custom app

TrueNAS (24.10+) can run homepage from its Apps page with **Install via YAML**. Custom
apps run an existing image, so build it on TrueNAS first, then install
`truenas-app.example.yaml` (copied to `truenas-app.yaml` with your paths). To update
later: build a new tag (`local/homepage:<n+1>`) and change the tag in Apps > homepage >
Edit. Note that `config.yaml` is mounted as a single file: if you replace it from outside
(e.g. over SMB), restart the app so the container sees the new file.

## API

| Method | Endpoint      | Description                               |
|--------|---------------|-------------------------------------------|
| GET    | `/api/config` | Returns the current config as JSON        |
| POST   | `/api/config` | Replaces the config with the posted JSON  |
| GET    | `/api/features` | `{"monitor": true}` when `MONITOR_URL` is set |
| GET/POST | `/monitor/…` | Passed through to `MONITOR_URL` |

## Project structure

```
app.py               Flask app: serves the UI and the config API
templates/index.html The whole frontend (dashboard, editor, themes)
favicon.svg          Site icon
static/retro-ui.css  Beveled desktop components (loaded only for the Retro theme)
static/retro-theme.css  How the homepage uses them in the Retro theme
static/rust-theme.css  The Rust gloss theme (loaded only while it is selected)
config.example.yaml  Example config (copy to config.yaml)
Dockerfile           Container image (Gunicorn with threads)
docker-compose.yml   Deployment with config.yaml bind-mounted
truenas-app.example.yaml  TrueNAS custom app (copy to truenas-app.yaml)
```

## Security notes

- There is **no authentication**. Anyone who can reach the page can edit the config through the UI or `POST /api/config`. Run it only on a trusted LAN or behind a reverse proxy that requires a login.
- Keep `config.yaml` out of version control. Use `config.example.yaml` as the template.
- The Monitor tab is protected by the monitor's own login, not by homepage. Homepage only
  forwards requests to the one `MONITOR_URL` you configure.
