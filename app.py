import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import psycopg2

app = Flask(__name__)

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

# ========================
# GERAR PIX
# ========================

@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    data = request.json
    email = data.get("email")
