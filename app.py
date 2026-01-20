from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # libera comunicação CORS com a extensão

@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    # Aqui você coloca a lógica do Mercado Pago
    return jsonify({"link_pix": "PIX_DE_TESTE", "valor": 5.0})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Recebi webhook:", data)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
