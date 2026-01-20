@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento de teste",
        "payment_method_id": "pix",
        "payer": {"email": email}
    }

    payment_response = mp.payment().create(payment_data)
    if payment_response["status"] != 201:
        return jsonify({"error": payment_response}), 500

    pix_info = payment_response["response"]["point_of_interaction"]["transaction_data"]
    return jsonify({
        "link_pix": pix_info.get("qr_code"),
        "valor": 1.0
    })
