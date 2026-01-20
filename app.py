import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2
from flask_cors import CORS

# ========================
# CRIAR APP FLASK
# ========================
app = Flask(__name__)
CORS(app)  # permite que a extensão converse com o backend

# ========================
# CONFIGURAÇÕES
# ========================
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

MP_HEADERS = {
    "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

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

# Inicializa o banco ao subir o app
init_db()

# ========================
# ENDPOINT VALIDAR
# ========================
@app.route("/validar")
def validar():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, data_expiracao FROM pagamentos WHERE email = %s ORDER BY id DESC LIMIT 1", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        # Não existe pagamento registrado
        return jsonify({"ativo": False})

    status, data_expiracao = row
    if status.lower() == "approved" and data_expiracao > datetime.utcnow():
        return jsonify({"ativo": True, "expira_em": data_expiracao.isoformat()})
    else:
        return jsonify({"ativo": False})

# ========================
# ENDPOINT GERAR PIX
# ========================
@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")
    valor = data.get("valor", 1.0)  # padrão: 1 real

    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Aqui você chamaria a API do Mercado Pago para criar o pagamento
    # Exemplo fictício (substituir pelo seu fluxo real)
    pagamento = {
        "payment_id": 123456,  # gerar ou pegar do MP
        "email": email,
        "status": "pending",
        "valor": valor,
        "data_pagamento": datetime.utcnow(),
        "data_expiracao": datetime.utcnow() + timedelta(days=30)
    }

    # Salvar no banco
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagamentos (payment_id, email, status, valor, data_pagamento, data_expiracao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        pagamento["payment_id"],
        pagamento["email"],
        pagamento["status"],
        pagamento["valor"],
        pagamento["data_pagamento"],
        pagamento["data_expiracao"]
    ))
    conn.commit()
    cur.close()
    conn.close()

    # Retornar dados do Pix
    return jsonify({
        "pix": f"PIX_DO_EXEMPLO_{pagamento['payment_id']}",
        "valor": pagamento["valor"],
        "expira_em": pagamento["data_expiracao"].isoformat()
    })

# ========================
# RODAR APP
# ========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
