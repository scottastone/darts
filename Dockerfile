# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY templates/ /app/templates
COPY app.py .

# Make port 5054 available to the world outside this container
EXPOSE 5054

# Run the app using Gunicorn for a production-ready server
# This command tells Gunicorn to run the 'app' object from the 'app.py' file.
CMD ["gunicorn", "--bind", "0.0.0.0:5054", "app:app"]