import os
import psycopg2
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ========================
# BANCO
# ========================

def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=5
    )

# ========================
# ROTAS
# ========================

@app.route("/")
def home():
    return "Servidor ONLINE - Teste Banco 🚀"

@app.route("/teste_db")
def teste_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        # cria tabela SOMENTE quando chamar a rota
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pagamentos (
                id SERIAL PRIMARY KEY,
                email TEXT,
                valor NUMERIC,
                status TEXT,
                data_pagamento TIMESTAMP
            )
        """)

        cur.execute("""
            INSERT INTO pagamentos (email, valor, status, data_pagamento)
            VALUES (%s, %s, %s, %s)
        """, (
            "teste@exemplo.com",
            1.23,
            "teste",
            datetime.utcnow()
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "registro gravado com sucesso"})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ========================
# START
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
