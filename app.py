"""
NSGA-II + LSTM Portfolio Engine — Local App
Run: python app.py
Then open: http://localhost:5000
"""

import os
import json
import threading
import webbrowser
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")

# ── Serve the frontend ────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ── Proxy the Anthropic API call (key stays server-side) ─────
@app.route("/api/optimize", methods=["POST"])
def optimize():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set in .env file"}), 401

    body = request.get_json()
    if not body:
        return jsonify({"error": "No request body"}), 400

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json=body,
            timeout=120,
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out after 120s"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Auto-open browser after startup ──────────────────────────
def open_browser():
    webbrowser.open("http://localhost:5000")

if __name__ == "__main__":
    print("\n" + "="*52)
    print("  NSGA-II + LSTM Portfolio Engine")
    print("  Local App — http://localhost:5000")
    print("="*52 + "\n")

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠  WARNING: ANTHROPIC_API_KEY not found in .env")
        print("   Edit the .env file and add your key, then restart.\n")
    else:
        print("✓  API key loaded from .env")
        print("✓  Opening browser...\n")
        threading.Timer(1.2, open_browser).start()

    app.run(host="127.0.0.1", port=5000, debug=False)
