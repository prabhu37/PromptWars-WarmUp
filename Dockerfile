# Use the official Python slim image.
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose the port that Streamlit runs on (rendered expects 8501, Cloud Run automatically maps PORT)
EXPOSE 8080

# Configure Streamlit to run headlessly and use the dynamic PORT env var from Cloud Run
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Run the app
ENTRYPOINT ["streamlit", "run", "app.py"]
