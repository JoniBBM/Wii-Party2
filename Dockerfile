FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app
ENV FLASK_DEBUG=1
ENV PYTHONPATH=/app

CMD ["flask", "run", "--host=0.0.0.0"]
