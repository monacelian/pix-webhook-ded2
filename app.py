import os
import psycopg2
from flask import Flask

app = Flask(__name__)

@app.route("/teste_db")
def teste_db():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return "BANCO CONECTADO ✅"
    except Exception as e:
        return str(e), 500
