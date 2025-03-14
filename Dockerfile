# Use a lightweight Python image
FROM python:3.9-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy the dependency file first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose the port that Streamlit will use
EXPOSE 8501

# Run the Streamlit app (frontend.py starts the backend as a subprocess)
CMD ["streamlit", "run", "frontend.py", "--server.port", "8501", "--server.enableCORS", "false"]
