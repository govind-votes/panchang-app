FROM python:3.10-slim

WORKDIR /app

# Install dependencies required for building Swiss Ephemeris
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Download Swiss Ephemeris C library
RUN wget https://www.astro.com/ftp/swisseph/swetest_src_2.10.03.zip -O swe.zip && \
    unzip swe.zip -d swe_src && \
    rm swe.zip

# Build and install Swiss Ephemeris C library
RUN cd swe_src && \
    make -f makefile.linux && \
    cp libswe.so /usr/lib/

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
