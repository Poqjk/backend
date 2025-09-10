# broker-backend-colab

## How start server

First make sure that postgresql service is running, and the database is created

### For WSL2

To run the project make sure install:

`sudo apt-get install build-essential libpq-dev python3-dev`

### Create database postgresql

In psql run this command:

`postgres=# CREATE DATABASE <name>;`

### Start server

1. To start the project create an environment (preferably)
`python -m venv env`

+ Start this (on linux)
`source env/bin/activate`

+ (on windows)
`env\Scripts\activate`

2. Install all the requirements
`pip install -r requirements.txt`

3. Execute the project
`fastapi dev main.py --reload`

+ or use
`uvicorn --port 8000 --host 127.0.0.1 main:app --reload`


### Enviroment variables to used

| Key | Value  |
| ------- | --- |
| DATABASE_URL | url path from postgresql |
| DATABASE_URL_ASYNC | url async from postgresql |
| API_KEY_NOWPAYMENTS | Key for the nowpayments API |
| JWT_SECRET_KEY | Secret key for token generation using JWT |
| JWT_SECRET_KEY_CHANGE_PASSWORD | Secret key for the generation of tokens for password change using JWT |
| ALGORITHM | Algorithm format for password encryption |
| MODE | Mode from the server (DEV:development - PROD:production) |


You can import the database from the sqlfile.sql

### Note
To connect the frontend from the server, just put the files in the /dist folder of the frontend when building and move them to the /static folder on the server. 

The server live from the project: https://broker-backend-colab.onrender.com/app

### To do
- [ ] Realization of websocket from assets forex and binary
- [ ] Realization of websocket to OTC market
- [ ] Make controllers to set the OTC market from assets binary and forex
- [ ] Add payment methods from cards and check crypto payments
