from jwt import encode, decode, exceptions
from fastapi import HTTPException
import os
from passlib.context import CryptContext
from datetime import datetime, timedelta, date,timezone
from fastapi.encoders import jsonable_encoder
from models.payment import Payment
from sqlalchemy import update, select
from models.affiliates import Affiliates

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
ALGORITHM = os.getenv("ALGORITHM")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # should be kept secret
REFRESH_JWT_KEY=os.getenv("REFRESH_JWT_KEY")
JWT_SECRET_KEY_CHANGE_PASSWORD = os.getenv("JWT_SECRET_KEY_CHANGE_PASSWORD") # kept secret

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def expire_date(days: int) -> datetime:
    """Generate an expiration date for the given number of days."""
    return datetime.now(timezone.utc) + timedelta(days=days)

def write_token(data: dict) -> str:
    """Generate an access token with a 15-minute expiration."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)  # 15 minutes
    token = encode(payload={**data, "exp": exp}, key=JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token

def write_refresh_token(data: dict) -> str:
    """Generate a refresh token with a 7-day expiration."""
    exp = expire_date(7)  # 7 days
    
    token = encode(payload={**data, "exp": exp}, key=REFRESH_JWT_KEY, algorithm=ALGORITHM)
    return token

def validate_refresh_token(token, output=False):
    try:
        decoded_token = decode(token, key=REFRESH_JWT_KEY, algorithms=[ALGORITHM])
        if output:
            return decoded_token
        return True
    except exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")


def validate_token(token: str, output: bool = False):
    try:
        decoded_token = decode(token, key=JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if output:
            return decoded_token
        return None
    except exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")

def expire_minutes(mins:int):
    date = datetime.now()
    new_date = date + timedelta(hours=4, minutes = mins)
    return new_date

def write_token_change_password(data:dict):
    token = encode(payload={**data, "exp":expire_minutes(15)},key=JWT_SECRET_KEY_CHANGE_PASSWORD, algorithm=ALGORITHM)
    return token

def validate_token_change_password(token: str, output=False):
    try:
        user_data = decode(token,key=JWT_SECRET_KEY_CHANGE_PASSWORD, algorithms=ALGORITHM)
        user = jsonable_encoder(user_data)
        user_block = user['block']
        if output == True and user_block != True:
            return decode(token,key=JWT_SECRET_KEY_CHANGE_PASSWORD, algorithms=ALGORITHM)
        else:
            return 3
    except exceptions.DecodeError:
        return 1
    except exceptions.ExpiredSignatureError:
        return 2

def verify_token_data(token: str, output=False):
    try:
        user_data = decode(token,key=JWT_SECRET_KEY, algorithms=ALGORITHM)
        user = jsonable_encoder(user_data)
        user_block = user['block']
        if output == True and user_block != True:
            return decode(token,key=JWT_SECRET_KEY, algorithms=ALGORITHM)
        else:
            return 3
    except exceptions.DecodeError:
        return 1
    except exceptions.ExpiredSignatureError:
        return 2
    
def validate_user(token : str):
    try:
        decode(token,key=JWT_SECRET_KEY, algorithms=ALGORITHM)
        user = jsonable_encoder(verify_token_data(token,output=True))
        user_role = user['role']
        user_block = user['block']
        if user_role == "admin" and  user_block != True:
            return user_role
        else:
            return True
    except exceptions.DecodeError:
        return True
    except exceptions.ExpiredSignatureError:
        return True

def calculate_age(birth : date):
    today = date.today()
    age = today.year - birth.year
    age -= ((today.month , today.day) < (birth.month, birth.day))
    return age

def validate_user_admin(user_id: str, token : str):
    if verify_token_data(token,output=True) == 1 or verify_token_data(token,output=True) == 2:
        return False
    else: 
        user_data = jsonable_encoder(verify_token_data(token,output=True))
        if (user_data['user_id'] == user_id or user_data['role'] == "admin") and user_data['block'] != True:
            return True
        else:
            return False
        
def validate_own_user(user_id: str, token : str):
    if verify_token_data(token,output=True) == 1 or verify_token_data(token,output=True) == 2:
        return False
    else: 
        user_data = jsonable_encoder(verify_token_data(token,output=True))
        if user_data['user_id'] == user_id and user_data['block'] != True:
            return True
        else:
            return False
        
        
AFFILIATE_LEVELS = {
    1: {"min_deposits": 0,   "max_deposits": 14,  "base_income": 50, "billing_factor": 2.0},
    2: {"min_deposits": 15,  "max_deposits": 29,  "base_income": 55, "billing_factor": 2.5},
    3: {"min_deposits": 30,  "max_deposits": 44,  "base_income": 60, "billing_factor": 3.0},
    4: {"min_deposits": 45,  "max_deposits": 59,  "base_income": 65, "billing_factor": 3.5},
    5: {"min_deposits": 60,  "max_deposits": 74,  "base_income": 70, "billing_factor": 4.0},
    6: {"min_deposits": 75,  "max_deposits": 89,  "base_income": 75, "billing_factor": 4.5},
    7: {"min_deposits": 90,  "max_deposits": 104, "base_income": 80, "billing_factor": 5.0},
    8: {"min_deposits": 105, "max_deposits": 119, "base_income": 85, "billing_factor": 5.5},
    9: {"min_deposits": 120, "max_deposits": 134, "base_income": 90, "billing_factor": 6.0},
    10: {"min_deposits": 135, "max_deposits": None, "base_income": 95, "billing_factor": 6.5},
}


def calcular_nivel_afiliado(deposits_count: int) -> int:
    for nivel, params in sorted(AFFILIATE_LEVELS.items()):
        # Si max_deposits es None, significa que no hay límite superior para ese nivel
        if params["max_deposits"] is None:
            return nivel
        if params["min_deposits"] <= deposits_count <= params["max_deposits"]:
            return nivel
    # Si no se cumple ninguno, se puede retornar el nivel 1 por defecto
    return 1


async def actualizar_nivel_afiliado(db, affiliate_id: str):
    # Define el período que te interese (por ejemplo, depósitos acumulados del mes actual)
  
    
    # Consulta todos los depósitos para el afiliado desde inicio_periodo
    stmt_deposits = select(Payment).where(
        Payment.affiliate_id == affiliate_id,
      
    )
    result = await db.execute(stmt_deposits)
    deposits = result.scalars().all()
    deposits_count = len(deposits)
    
    # Calcular el nuevo nivel usando el diccionario
    nuevo_nivel = calcular_nivel_afiliado(deposits_count)
    
    # Actualizar el nivel en la tabla Affiliates
    stmt_update = update(Affiliates).where(Affiliates.id == affiliate_id).values(affiliate_level=nuevo_nivel)
    await db.execute(stmt_update)
    db.commit()
    print(f"Afiliado {affiliate_id} actualizado a nivel {nuevo_nivel} con {deposits_count} depósitos.")
