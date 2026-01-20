# app.py
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2
import mercadopago
import qrcode
import io
from flask_cors import CORS

# ========================
# CONFIGURAÇÕES
# ========================
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = Flask(__name__)
CORS(app)  # permitir chamadas da extensão

# ========================
# BANCO DE DADOS
# ========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id SERIAL PRIMARY KEY,
            payment_id BIGINT UNIQUE,
            email TEXT,
            status TEXT,
            valor NUMERIC,
            data_pagamento TIMESTAMP,
            data_expiracao TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ========================
# ENDPOINTS
# ========================

# Validar se email tem pagamento ativo
@app.route("/validar", methods=["GET"])
def validar():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email é obrigatório"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT status, data_expiracao
        FROM pagamentos
        WHERE email=%s
        ORDER BY id DESC
        LIMIT 1
    """, (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and row[0] == "approved" and row[1] > datetime.now():
        return jsonify({"ativo": True, "expira_em": row[1]})
    else:
        return jsonify({"ativo": False})

# Criar pagamento Pix
@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")
    valor = float(data.get("valor", 1.0))
    titulo = data.get("titulo", "Pagamento Pix DedMais")

    if not email:
        return jsonify({"error": "Email é obrigatório"}), 400

    # Criar preferência no Mercado Pago
    preference_data = {
        "items": [{"title": titulo, "quantity": 1, "unit_price": valor}],
        "payer": {"email": email},
        "payment_methods": {"excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}, {"id": "credit_card"}]},
        "back_urls": {"success": WEBHOOK_URL, "failure": WEBHOOK_URL, "pending": WEBHOOK_URL},
        "auto_return": "approved"
    }

    pref = sdk.preference().create(preference_data)
    link = pref["response"].get("init_point")
    pix_id = pref["response"]["id"]

    # Salvar no banco como pendente
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagamentos (payment_id, email, status, valor, data_pagamento, data_expiracao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (pix_id, email, "pending", valor, datetime.now(), datetime.now() + timedelta(days=30)))
    conn.commit()
    cur.close()
    conn.close()

    # Gerar QR Code em memória
    qr = qrcode.QRCode()
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    return jsonify({"pix_id": pix_id, "link_pix": link, "valor": valor})

# Receber notificações do Mercado Pago
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("=== Notificação recebida do Mercado Pago ===")
    print(data)

    payment_id = None
    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif "resource" in data:
        payment_id = data["resource"].split("/")[-1]

    if payment_id:
        try:
            resp = sdk.payment().get(payment_id)
            payment = resp["response"]
            status = payment.get("status")

            # Atualizar banco
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE pagamentos
                SET status=%s
                WHERE payment_id=%s
            """, (status, payment_id))
            conn.commit()
            cur.close()
            conn.close()

            print(f"Pagamento {payment_id} atualizado para status: {status}")
        except Exception as e:
            print("Erro ao consultar API:", e)
    else:
        print("Payment ID não encontrado na notificação.")

    return "OK", 200

# ========================
# Roda no Railway via gunicorn
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
