import json
import os
import re
import urllib.error
import urllib.request
import yaml
from flask import Flask, Response, jsonify, redirect, request, render_template, send_from_directory, stream_with_context
from threading import Lock

app = Flask(__name__, static_folder="static")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config/config.yaml")
_lock = Lock()

# Optional: a homelab monitor web page served through this app under /monitor/ (Monitor tab).
# The monitor keeps its own data, login and LLM; this only passes requests through.
# Unset = no Monitor tab.
MONITOR_URL = os.environ.get("MONITOR_URL", "").rstrip("/")
MONITOR_TIMEOUT = float(os.environ.get("MONITOR_TIMEOUT", 1800))  # chat answers can take minutes
FORWARD_REQUEST_HEADERS = ("Content-Type", "Cookie", "Accept")
FORWARD_RESPONSE_HEADERS = ("Set-Cookie", "Cache-Control")

# Optional: read-only Home Assistant states on the dashboard (the entities listed under
# `homeassistant:` in config.yaml). The token stays on the server; the browser only gets each
# listed entity's state, name and unit, never the token or the other attributes.
# Unset = no Home Assistant section.
HA_URL = os.environ.get("HA_URL", "").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
HA_TIMEOUT = float(os.environ.get("HA_TIMEOUT", 10))
ENTITY_ID = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


def read_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


def write_config(data):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.svg")
def favicon():
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.route("/api/config", methods=["GET"])
def get_config():
    with _lock:
        return jsonify(read_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    with _lock:
        write_config(data)
    return jsonify({"ok": True})


@app.route("/api/features")
def features():
    return jsonify({"monitor": bool(MONITOR_URL), "homeassistant": bool(HA_URL and HA_TOKEN)})


def ha_wanted(cfg):
    """The entities listed in config.yaml: [{"entity", "name", "icon"}], invalid ids dropped."""
    wanted = []
    for item in ((cfg.get("homeassistant") or {}).get("entities") or []):
        item = {"entity": item} if isinstance(item, str) else item
        if isinstance(item, dict) and ENTITY_ID.match(str(item.get("entity", ""))):
            wanted.append({"entity": item["entity"], "name": item.get("name") or "", "icon": item.get("icon") or ""})
    return wanted


def ha_states():
    """All states from Home Assistant, by entity id. Raises OSError/ValueError when it fails."""
    req = urllib.request.Request(f"{HA_URL}/api/states",
                                 headers={"Authorization": f"Bearer {HA_TOKEN}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=HA_TIMEOUT) as r:
        return {s["entity_id"]: s for s in json.load(r)}


def ha_error(e):
    if isinstance(e, urllib.error.HTTPError):
        why = "the token was rejected" if e.code in (401, 403) else f"it answered {e.code}"
    else:
        why = "it is not reachable"
    return jsonify({"error": f"Home Assistant: {why}"}), 502


@app.route("/api/ha")
def ha():
    if not (HA_URL and HA_TOKEN):
        return jsonify({"error": "No Home Assistant configured (HA_URL / HA_TOKEN are not set)"}), 404
    with _lock:
        wanted = ha_wanted(read_config())
    if not wanted:
        return jsonify({"entities": []})
    try:
        states = ha_states()
    except (OSError, ValueError) as e:
        return ha_error(e)
    out = []
    for w in wanted:
        s = states.get(w["entity"])
        attrs = (s or {}).get("attributes") or {}
        out.append({
            "entity": w["entity"], "icon": w["icon"],
            "name": w["name"] or attrs.get("friendly_name") or w["entity"],
            "state": s["state"] if s else None,  # None = no such entity in Home Assistant
            "unit": attrs.get("unit_of_measurement"),
            "device_class": attrs.get("device_class"),
            "last_changed": (s or {}).get("last_changed"),
        })
    return jsonify({"entities": out})


@app.route("/api/ha/entities")
def ha_entities():
    """Entity ids and names, for picking them in the editor."""
    if not (HA_URL and HA_TOKEN):
        return jsonify({"error": "No Home Assistant configured (HA_URL / HA_TOKEN are not set)"}), 404
    try:
        states = ha_states()
    except (OSError, ValueError) as e:
        return ha_error(e)
    return jsonify({"entities": sorted(
        ({"entity": i, "name": (s.get("attributes") or {}).get("friendly_name") or ""} for i, s in states.items()),
        key=lambda e: e["entity"])})


@app.route("/monitor")
def monitor_root():
    return redirect("/monitor/")  # the monitor page uses relative URLs


@app.route("/monitor/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/monitor/<path:path>", methods=["GET", "POST"])
def monitor_proxy(path):
    if not MONITOR_URL:
        return jsonify({"error": "No monitor configured (MONITOR_URL is not set)"}), 404
    url = f"{MONITOR_URL}/{path}"
    if request.query_string:
        url += "?" + request.query_string.decode()
    headers = {h: request.headers[h] for h in FORWARD_REQUEST_HEADERS if h in request.headers}
    upstream_request = urllib.request.Request(
        url, data=request.get_data() if request.method == "POST" else None, headers=headers, method=request.method)
    try:
        upstream = urllib.request.urlopen(upstream_request, timeout=MONITOR_TIMEOUT)
    except urllib.error.HTTPError as e:
        upstream = e  # 401, 404, ... are passed on as they are
    except OSError as e:
        return jsonify({"error": f"The homelab monitor ({MONITOR_URL}) is not reachable: {e}"}), 502

    def body():
        # read1 returns whatever has arrived, so streamed chat answers pass through live
        read = getattr(upstream, "read1", upstream.read)
        try:
            while chunk := read(8192):
                yield chunk
        finally:
            upstream.close()

    response = Response(stream_with_context(body()), status=getattr(upstream, "status", None) or upstream.code,
                        content_type=upstream.headers.get("Content-Type"))
    for name in FORWARD_RESPONSE_HEADERS:
        for value in upstream.headers.get_all(name) or []:
            response.headers.add(name, value)
    response.headers["X-Accel-Buffering"] = "no"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)