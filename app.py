@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    payment_id = data["data"]["id"]

    # Atualizar status no banco
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pagamentos SET status = %s WHERE payment_id = %s", ("approved", payment_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})
