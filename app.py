@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {"email": email},
    }

    try:
        payment = mp.payment().create(payment_data)
    except Exception as e:
        return jsonify({"error": f"Erro ao criar pagamento: {str(e)}"}), 500

    # Aqui pegamos o resultado real
    result = payment.get("response", {})
    if not result or "point_of_interaction" not in result:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    pix_payload = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
    qr_base64 = result.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    return jsonify({
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result.get("transaction_amount", 0)
    })
