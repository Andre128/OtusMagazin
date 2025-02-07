FROM python:3.9-alpine
RUN mkdir -p /home/Magazine
WORKDIR /home/Magazine
RUN pip install --no-cache-dir Flask==2.3.2
RUN apk add --no-cache curl
RUN curl https://github.com/Andre128/OtusMagazin/blob/main/healthCheck.py
EXPOSE 8000
CMD ["python", "healthCheck.py"]
