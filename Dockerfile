# Usa una imagen base de Python
FROM python:3.11-slim

# Instalar Git, gcc, make y las dependencias necesarias para compilar psycopg2
RUN apt-get update && \
    apt-get install -y git libpq-dev gcc make && \
    apt-get clean

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requerimientos e instala dependencias
COPY requirements.txt /app/

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente de la aplicación
COPY . /app/



# Expone el puerto 8000 para FastAPI
EXPOSE 8000

# Comando para ejecutar FastAPI con Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]
