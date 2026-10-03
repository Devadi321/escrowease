FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY static/ static/
COPY templates/ templates/
COPY schema.sql .

# Runtime config comes from environment (Render/HF Spaces dashboard):
#   PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, FLASK_SECRET_KEY
ENV PORT=5000
EXPOSE 5000

CMD ["python", "-m", "backend.app"]
