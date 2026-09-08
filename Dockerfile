FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY finance_bot/ ./finance_bot/
WORKDIR /app/finance_bot
CMD ["python", "bot.py"]
