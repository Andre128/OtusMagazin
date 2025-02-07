FROM python:3.9-alpine
RUN pip install --no-cache-dir Flask==2.3.2
ADD https://raw.githubusercontent.com/Andre128/OtusMagazin/refs/heads/main/healthCheck.py .
EXPOSE 8000
CMD ["python", "healthCheck.py"]
