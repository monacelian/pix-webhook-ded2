import os
import psycopg2
from flask import Flask

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

@app.route("/")
def index():
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    cur = conn.cursor()
    cur.execute("SELECT * FROM public.sua_tabela LIMIT 50")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    html = "<h1>Banco de Dados</h1><table border=1>"
    html += "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"

    for r in rows:
        html += "<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>"

    html += "</table>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
