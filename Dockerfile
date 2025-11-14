# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 5054

# Run app.py when the container launches using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5054", "--workers", "4", "app:app"]