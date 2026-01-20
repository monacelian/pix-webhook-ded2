import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import uuid

# ========================
# CONFIGURAÇÃO DO FLASK
# ========================
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
    # Criar tabela se não existir
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
# ENDPOINT PARA GERAR PIX
# ========================
@app.route("/gerar_pix", methods=["GET", "POST"])
def gerar_pix():
    # Suporta GET ou POST
    if request.method == "POST":
        data = request.json
        email = data.get("email")
    else:
        email = request.args.get("email")

    if not email:
        return jsonify({"error": "Email obrigatório"}), 400

    # Criar ID único para o pagamento
    payment_id = str(uuid.uuid4())[:8]  # 8 caracteres
    amount = 5  # valor fixo do PIX
    status = "pending"  # registra tentativa
    created_at = datetime.datetime.utcnow()
    expires_at = created_at + datetime.timedelta(days=30)

    # Inserir no banco de dados
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

    # Retornar para a extensão
    return jsonify({
        "message": "Tentativa de pagamento registrada",
        "payment_id": payment_id,
        "email": email,
        "status": status,
        "amount": amount,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat()
    })

# ========================
# ENDPOINT PARA LISTAR TODOS OS PAGAMENTOS (teste)
# ========================
@app.route("/listar_pix", methods=["GET"])
def listar_pix():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT payment_id, email, status, amount, created_at, expires_at FROM pix_notifications")
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
                "expires_at": r[5].isoformat()
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# RODAR SERVIDOR
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
