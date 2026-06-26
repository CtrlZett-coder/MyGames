FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pieces.py solver.py render.py bot.py .
CMD ["python", "bot.py"]
