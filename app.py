from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os
import psycopg2
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ----------------- CONFIG -----------------
DATABASE_URL = os.environ.get("DATABASE_URL")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ----------------- BANCO DE DADOS -----------------
def get_db():
    return psycopg2.connect(DATABASE_URL)

# ----------------- FUNÇÃO PARA PEGAR ÚLTIMO PAGAMENTO -----------------
def get_ultimo_pagamento_valido(uuid):
    """
    Retorna o último pagamento válido para o UUID, priorizando approved.
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT payment_id, status, valid_until
            FROM pagamentos
            WHERE uuid = %s
            ORDER BY
                CASE WHEN status = 'approved' THEN 1 ELSE 2 END,
                data_pagamento DESC
            LIMIT 1
        """, (uuid,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row  # (payment_id, status, valid_until) ou None
    except Exception as e:
        print("Erro ao consultar pagamento:", e)
        return None

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    uuid = request.args.get("uuid")
    if not email or not uuid:
        return jsonify({"error": "Email ou UUID não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment = mp.payment().create(payment_data)
    except Exception as e:
        return jsonify({"error": f"Erro ao criar pagamento no MP: {str(e)}"}), 500

    if payment["status"] != 201:
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]

    print("📌 Pix gerado:", result)

    pix_payload = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
    qr_base64 = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagamentos (payment_id, email, uuid, valor, status, valid_until, data_pagamento)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            str(result["id"]),
            email,
            uuid,
            result["transaction_amount"],
            "pending",
            datetime.utcnow() + timedelta(minutes=30),
            datetime.utcnow()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar no banco: {str(e)}"}), 500

    return jsonify({
        "payment_id": result["id"],
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

# ----------------- WEBHOOK -----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    payment_id = None

    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]
    elif request.args.get("id"):
        payment_id = request.args.get("id")

    if not payment_id:
        return "OK", 200

    r = mp.payment().get(payment_id)
    p = r["response"]

    if p["status"] != "approved":
        return "OK", 200

    # Atualiza pagamento aprovado e remove pendentes
    try:
        conn = get_db()
        cur = conn.cursor()

        # 1️⃣ Atualiza status do pagamento aprovado
        cur.execute("""
            UPDATE pagamentos
            SET status = %s, valid_until = %s
            WHERE payment_id = %s
        """, (
            "approved",
            datetime.utcnow() + timedelta(days=30),
            str(payment_id)
        ))

        # 2️⃣ Apaga todos os pagamentos pendentes do mesmo UUID
        # Primeiro precisamos buscar o UUID do pagamento aprovado
        cur.execute("""
            SELECT uuid FROM pagamentos WHERE payment_id = %s
        """, (payment_id,))
        row = cur.fetchone()
        if row:
            uuid = row[0]
            cur.execute("""
                DELETE FROM pagamentos
                WHERE uuid = %s AND status = 'pending'
            """, (uuid,))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Erro ao atualizar/apagar pagamentos no webhook:", e)
        pass

    return "OK", 200

# ----------------- CHECAR STATUS -----------------
@app.route("/checar_pagamento")
def checar_pagamento():
    uuid = request.args.get("uuid")
    if not uuid:
        return jsonify({"error": "UUID não fornecido"}), 400

    try:
        pagamento = get_ultimo_pagamento_valido(uuid)

        if not pagamento:
            return jsonify({"status": "none"})

        payment_id, status, valid_until = pagamento

        # Consulta o Mercado Pago apenas se status não for approved ou expirado
        if status == "approved" and valid_until > datetime.utcnow():
            return jsonify({"status": "active"})
        else:
            mp_status = mp.payment().get(payment_id)["response"]["status"]
            if mp_status == "approved":
                return jsonify({"status": "active"})
            elif mp_status == "pending":
                return jsonify({"status": "pending"})
            else:
                return jsonify({"status": "expired"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- START -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
