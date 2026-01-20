import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import uuid

# ========================
# CONFIGURAÇÃO DO FLASK
# ========================
app = Flask(__name__)
CORS(app)  # libera comunicação CORS com a extensão

# ========================
# BANCO DE DADOS
# ========================
DATABASE_URL = "postgresql://postgres:wxMkqvcRPlDGJiwSeDPluMioymuhpiuU@containers-us-west-123.railway.app:5432/railway"

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pix_notifications (
                id SERIAL PRIMARY KEY,
                payment_id VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255),
                status VARCHAR(20) NOT NULL,
                amount NUMERIC(10,2),
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                webhook_received BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Banco inicializado")
    except Exception as e:
        print("⚠️ Erro ao inicializar banco:", e)

# Inicializa o banco, mas não trava o servidor se falhar
init_db()

# ========================
# ROTA DE TESTE
# ========================
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "Servidor online"})

# ========================
# GERAR PIX (registro da tentativa)
# ========================
@app.route("/gerar_pix", methods=["GET"])
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Criar ID único para pagamento
    payment_id = str(uuid.uuid4())[:8]
    amount = 5.0
    status = "pending"
    created_at = datetime.datetime.utcnow()
    expires_at = created_at + datetime.timedelta(days=30)

    # Responder para extensão imediatamente
    response = {
        "message": "Tentativa de pagamento registrada",
        "payment_id": payment_id,
        "email": email,
        "status": status,
        "amount": amount,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat()
    }

    # Gravação no banco em try/except para não travar
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pix_notifications
            (payment_id, email, status, amount, created_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (payment_id, email, status, amount, created_at, expires_at))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("⚠️ Erro ao gravar tentativa de pagamento no banco:", e)

    return jsonify(response)

# ========================
# WEBHOOK DO MERCADO PAGO
# ========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "Nenhum dado recebido"}), 400

    print("📢 Webhook recebido:", data)

    payment_id = str(data.get("data", {}).get("id", ""))
    status_mp = data.get("action", "unknown")  # ex: 'payment.updated'

    # Atualiza banco em try/except para não travar
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pix_notifications
            SET status = %s, webhook_received = TRUE
            WHERE payment_id = %s
        """, (status_mp, payment_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("⚠️ Erro ao atualizar webhook no banco:", e)

    # Sempre retorna 200 rápido para o Mercado Pago
    return "", 200

# ========================
# LISTAR PIX (teste)
# ========================
@app.route("/listar_pix", methods=["GET"])
def listar_pix():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT payment_id, email, status, amount, created_at, expires_at, webhook_received
            FROM pix_notifications
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "payment_id": r[0],
                "email": r[1],
                "status": r[2],
                "amount": float(r[3]),
                "created_at": r[4].isoformat(),
                "expires_at": r[5].isoformat(),
                "webhook_received": r[6]
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# RODAR SERVIDOR
# ========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # porta dinâmica Railway
    app.run(host="0.0.0.0", port=port, debug=True)
