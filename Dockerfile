FROM rust:1.83 as builder

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev build-essential libssl-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages maturin

WORKDIR /app

COPY . .

WORKDIR /app/jagua-rs/pybind

# Build the wheel using maturin
RUN maturin build --release

RUN ls -la /app/jagua-rs/target/wheels/

# Stage 2: Create the final runtime image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy and install Python dependencies from requirements.txt
COPY requirements.txt .
COPY test.json /python/test.json
COPY test.json .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built wheel from the builder stage and install it
COPY --from=builder /app/jagua-rs/target/wheels/ /wheels/
RUN pip install --no-cache-dir /wheels/*.whl

# Copy the rest of the repository (including your Python app)
COPY . .

# Set the entrypoint to run your Python main app
CMD ["python", "python/main.py"]
