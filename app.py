from flask import Flask, jsonify
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

@app.route("/")
def home():
    return "Servidor OK"

@app.route("/teste_db")
def teste_db():
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO pagamentos (payment_id, email, status, valor)
            VALUES (%s, %s, %s, %s)
        """, (
            "TESTE123",
            "teste@exemplo.com",
            "pending",
            1.00
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "ok", "msg": "Registro inserido"})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
