# La imagen de docker base - capa 1
FROM python:3.9.1

# Instalacion de los prerequisitos
RUN apt-get install wget
RUN pip install pandas sqlalchemy psycopg2 requests  

WORKDIR /app

COPY ingest_data.py ingest_data.py 

ENTRYPOINT [ "python", "ingest_data.py" ]  
