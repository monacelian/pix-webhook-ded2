from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

@app.route("/")
def home():
    return "Servidor Flask OK"

@app.route("/teste_db")
def teste_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO pagamentos (email, valor, status)
                VALUES ('teste@exemplo.com', 1.0, 'teste')
            """))
            conn.commit()

        return jsonify({"status": "registro inserido com sucesso"})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
