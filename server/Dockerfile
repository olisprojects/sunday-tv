FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY seed.py ./seed.py

# Persist the SQLite DB outside the image.
ENV SUNDAYTV_DB=/data/sundaytv.db
VOLUME ["/data"]

EXPOSE 8770

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8770"]
