# Use the official Python slim image.
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install dependencies (using pure Python wheels)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose the port that Streamlit runs on
EXPOSE 8080

# Configure Streamlit to run headlessly and use the dynamic PORT env var from Cloud Run
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Run the app
ENTRYPOINT ["streamlit", "run", "app.py"]
