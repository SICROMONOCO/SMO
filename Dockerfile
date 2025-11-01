# Use an official Python runtime as a parent image
FROM mirror.gcr.io/python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Create a non-root user
RUN useradd -m -d /home/smo-user -s /bin/bash smo-user

# Copy the requirements file
COPY --chown=smo-user:smo-user requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=smo-user:smo-user . .

# Switch to the non-root user
USER smo-user

# Set the default command to run the agent
CMD ["python3", "agent.py"]
