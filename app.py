import os
import yaml
from flask import Flask, jsonify, request, render_template, send_from_directory
from threading import Lock

app = Flask(__name__, static_folder="static")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config/config.yaml")
_lock = Lock()


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)