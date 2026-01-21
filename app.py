from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Servidor Flask OK"

@app.route("/teste_db")
def teste_db():
    return jsonify({"status": "rota ok"})

# NÃO use app.run no Railway
