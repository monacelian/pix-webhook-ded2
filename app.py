import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import uuid

app = Flask(__name__)
CORS(app)

# ========================
# BANCO DE DADOS
# ========================
DATABASE_URL = "postgresql://postgres:wxMkqvcRPlDGJiwSeDPluMioymuhpiuU@containers-us-west-123.railway.app:5432/railway"

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Cria tabela se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pix_notifications (
            id SERIAL PRIMARY KEY,
            payment_id VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL,
            amount NUMERIC(10,2),
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Inicializar tabela
init_db()

# ========================
# GERAR PIX (grava email tentando pagar)
# ========================
@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email obrigatório"}), 400

    # Gerar ID único para pagamento
    payment_id = str(uuid.uuid4())[:8]  # exemplo de 8 caracteres
    amount = 5  # valor fixo de 5 reais
    status = "pending"  # status inicial
    created_at = datetime.datetime.utcnow()
    expires_at = created_at + datetime.timedelta(days=30)

    # Gravar no banco
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
        return jsonify({"error": str(e)}), 500

    # Retornar dados para a extensão
    return jsonify({
        "message": "Tentativa de pagamento registrada",
        "payment_id": payment_id,
        "email": email,
        "status": status,
        "amount": amount,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
