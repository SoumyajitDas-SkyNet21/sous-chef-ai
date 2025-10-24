# Stage 1: Builder Stage - Installs dependencies and prepares the app

# Use a specific, slim Python version for stability and small size
FROM python:3.11-slim as builder

# Set environment variables
# Streamlit will use the PORT set by Cloud Run. Gunicorn listens on 8080 by default 
# when using the Streamlit command in the CMD below.
ENV PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Create and set the working directory
WORKDIR $APP_HOME

# Install dependencies first for better caching
# This ensures a faster build if only application code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# IMPORTANT: Replace 'streamlit_app.py' with the actual name of your Python file.
# If your file is named 'app.py', change the line below and the CMD.
COPY . .

# ---

# Stage 2: Final Runtime Stage - Minimal image for deployment
FROM python:3.11-slim

# Set environment variables for the runtime
# Cloud Run automatically sets the actual port, but we use 8080 as a default fallback
ENV PORT=8080 \
    APP_HOME=/app 

WORKDIR $APP_HOME

# Copy only the installed packages and application code from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder $APP_HOME $APP_HOME

# 🚀 THE CRITICAL FIX: Explicitly set the host and port for Streamlit
# The $PORT variable will be set by Cloud Run (usually 8080)
# We must listen on 0.0.0.0 (all interfaces)
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]

# NOTE: We hardcode 8080 here because Streamlit sometimes ignores the $PORT environment
# variable for its internal server, but the Cloud Run networking layer maps it correctly.