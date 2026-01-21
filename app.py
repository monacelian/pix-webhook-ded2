from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# ------------------ APP ------------------
app = Flask(__name__)
CORS(app)

# ------------------ ENV ------------------
DATABASE_URL = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ------------------ MERCADO PAGO ------------------
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# ------------------ DATABASE ------------------
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    pix_id = Column(String, nullable=False)
    status = Column(String, default="pending")
    criado_em = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ------------------ ROTAS ------------------
@app.route("/gerar_pix")
def gerar_pix():
    email = request.args.get("email")

    if not email:
        return jsonify({"error": "Email não fornecido"}), 400

    payment_data = {
        "transaction_amount": 1.0,
        "description": "Pagamento Pix DedMais",
        "payment_method_id": "pix",
        "payer": {
            "email": email
        }
    }

    payment = mp.payment().create(payment_data)

    if payment["status"] != 201:
        return jsonify({"error": "Erro ao criar pagamento"}), 500

    result = payment["response"]

    pix_payload = result.get("point_of_interaction", {}) \
                        .get("transaction_data", {}) \
                        .get("qr_code")

    qr_base64 = result.get("point_of_interaction", {}) \
                      .get("transaction_data", {}) \
                      .get("qr_code_base64")

    if not pix_payload or not qr_base64:
        return jsonify({"error": "Não foi possível gerar Pix"}), 500

    # -------- SALVAR NO BANCO --------
    db = SessionLocal()
    pagamento = Pagamento(
        email=email,
        valor=result["transaction_amount"],
        pix_id=str(result["id"]),
        status="pending"
    )
    db.add(pagamento)
    db.commit()
    db.close()

    return jsonify({
        "pix_id": result["id"],
        "pix_payload": pix_payload,
        "qr_base64": qr_base64,
        "valor": result["transaction_amount"]
    })

# ------------------ START ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
