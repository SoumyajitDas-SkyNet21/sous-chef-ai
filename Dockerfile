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

# Use a smaller, secure base image for the final container
FROM python:3.11-slim

# Set environment variables for the runtime
ENV PORT=8080 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Copy only the installed packages and application code from the builder stage
# This significantly reduces the size of the final image
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder $APP_HOME $APP_HOME

# Streamlit/Cloud Run Entrypoint:
# Use gunicorn to run Streamlit on the standard Cloud Run port.
# Gunicorn is generally more stable than the simple 'streamlit run' command.
# This command tells Gunicorn to listen on the $PORT variable (which Cloud Run provides),
# and run the Streamlit app.
# IMPORTANT: Replace 'streamlit_app.py' with the actual name of your Python file!
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "streamlit_gunicorn:main", "--timeout", "120"]

# NOTE ON CMD:
# The command 'streamlit_gunicorn:main' is an abstraction. Since Streamlit doesn't
# natively support WSGI/ASGI (which Gunicorn expects), we must wrap the Streamlit command.
# A simpler, though less robust, command is: 
# CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
# For this advanced setup, the gunicorn wrapper works best.