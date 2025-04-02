# Dockerfile
FROM python:3.11.4-slim-buster

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# set the working directory
WORKDIR /app

# install system dependencies
RUN apt-get update && \
    apt-get install -y gcc libpq-dev

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copy entrypoint.sh
# COPY /entrypoint.sh /app/
#RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
# RUN chmod +x /usr/src/app/entrypoint.sh



# Copy project files
COPY . .

# run entrypoint.sh
# ENTRYPOINT ["/usr/src/app/entrypoint.sh"]

# Collect static files (adjust if needed)
RUN python manage.py collectstatic --noinput

# Expose the port your app runs on (Gunicorn default)
EXPOSE 8000

# Start Gunicorn with your WSGI module (adjust as necessary)
CMD ["gunicorn", "mokkapi.wsgi:application", "--bind", "0.0.0.0:8000"]