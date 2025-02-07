FROM python:3.9-alpine
RUN mkdir -p /home/Magazine
WORKDIR /home/Magazine
RUN pip install --no-cache-dir Flask==2.3.2
RUN apk add --no-cache curl
RUN curl -0 https://github.com/Andre128/OtusMagazin/blob/cc0edbfb08e0c7be5e6797f86e30c8b04fd4f937/firstApp.py
EXPOSE 8000
CMD ["python", "healthCheck.py"]