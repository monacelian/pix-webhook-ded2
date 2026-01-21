from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago

app = Flask(__name__)
CORS(app)  # permite comunicação com a extensão

# ----------------- CONFIGURAÇÃO -----------------
# Substitua pelo seu Access Token de PRODUÇÃO
mp = mercadopago.SDK("APP_USR-4983735969013417-011912-06b5dab8d512172248682b9398cd847b-32984780")

# ----------------- GERAR PIX -----------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,  # valor em reais
        "description": "Pagamento via DedMais Pix",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment_response = mp.payment().create(payment_data)
        payment = payment_response["response"]

        # Pega o link do QR Code do Pix
        qr_link_url = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")

        if not qr_link_url:
            return jsonify({"error": "Não foi possível gerar Pix"}), 500

        return jsonify({
            "link_pix": qr_link_url,
            "valor": payment.get("transaction_amount", 1.0)
        })
    except Exception as e:
        print("Erro ao gerar Pix:", e)
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

# ----------------- WEBHOOK -----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Recebi webhook:", data)

    # Aqui você pode adicionar lógica para marcar pagamento como concluído
    # ou enviar mensagem para extensão via websocket / polling

    return "OK", 200

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
