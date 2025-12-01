# -------------------------------
# 1. Use Python 3.10 (stable)
# -------------------------------
FROM python:3.10-slim

# -------------------------------
# 2. Install OS dependencies
# -------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# 3. Set app directory
# -------------------------------
WORKDIR /app

# -------------------------------
# 4. Copy requirements
# -------------------------------
COPY requirements.txt /app/requirements.txt

# -------------------------------
# 5. Install Python packages
# -------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# 6. Copy application files
# -------------------------------
COPY . /app

# -------------------------------
# 7. Expose FastAPI port
# -------------------------------
EXPOSE 8000

# -------------------------------
# 8. Start FastAPI with Uvicorn
# -------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
