from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket,WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from routers import trades, user, payments, withdraws,assets, stats,affiliates
from fastapi import FastAPI, Request,Response, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
import asyncio
import requests
from utils import get_hashed_password, verify_password, write_token, calculate_age, write_refresh_token,validate_refresh_token
from fastapi.middleware.cors import CORSMiddleware
from config.database import AsyncSessionLocal, engine, Session, Base, AsyncSession, get_async_db
from models.operation import Operation
from models.user import User as UserModel
from models.asset import Asset as AssetModel
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from routers.user import User, RegisterCredentials
from typing import Dict, List
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import Optional
import os
from typing import Set
from models.affiliateLinks import AffiliateLinks, LinkProgram
from models.affiliateReferrals import AffiliateReferrals
from models.affiliateTransactions import AffiliateTransactions
from models.affiliateEarnings import AffiliateEarnings
from models.affiliates import Affiliates
from models.payment import Payment

from utils import calcular_nivel_afiliado, AFFILIATE_LEVELS
MODE = os.getenv("MODE")
if MODE.strip() == "DEV":
    direction = "http://localhost:8080/"
elif MODE.strip() == "PROD":
    direction = "/api/health"

CONNECTIONS = {}
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "https://broker-prbc-frontend.onrender.com",
    "https://broker-backend-colab-cr13.onrender.com",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:4173",
    "https://broker-admin-hazel.vercel.app"
]
scheduler = AsyncIOScheduler()

connected_users: Set[str] = set()
all_users: Set[str] = set()


  
        
        
        



#websocket manager
class ConnectionManager:
    # INITIALIZE THE LIST AND CONNECTION

    def __init__(self):
        """example:
        [{
        "channel_id":[Websocket]
        0370643958
        }]
        """
        self.active_connections: Dict[str, List[WebSocket]] = CONNECTIONS

    # CONNECT TO WEBSOCKET AND APPEND TO THE LIST
    async def connect(self, websocket: WebSocket, channel_id: str, user_id: str):
        await websocket.accept()
        connections = self.active_connections
        if connections.get(channel_id):
            connections[channel_id].append(websocket)
        else:
            connections[channel_id] = [websocket]

        connected_users.add(user_id)


    # PURGE WEBSOCKET LIST STORE
    async def disconnect(self, channel_id: str, websocket: WebSocket, user_id):
        if self.active_connections.get(channel_id):
            self.active_connections[channel_id].remove(websocket)
            connected_users.discard(user_id)

    def connection_count(self, channel_id: str):
        connection = self.active_connections
        if connection.get(channel_id):
            return len(connection[channel_id])

    # Send a retry message to a user WebSocket
    async def broadcast(
        self, channel_id: str, message, not_send: WebSocket
    ):
        connections = self.active_connections
        if connections.get(channel_id):
            ws_channel = connections[channel_id]

            for ws in ws_channel:
                ws: WebSocket = ws
                if ws != not_send:
                    await ws.send_json(
                        {
                            "message": message,
                        }
                    )
    async def get_connection(self, channel_id: str, token: str) -> Optional[WebSocket]:
        """Retrieve the WebSocket connection for a specific channel and token."""
        connections = self.active_connections.get(channel_id, [])
        for ws in connections:
            # Assuming you have a way to identify the user from the token
            # You may need to implement a way to associate tokens with WebSockets
            return ws
        return None
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_json(
            {
                "message": message,
                "sender": "you",
            }
        )


websocketManager = ConnectionManager()





def create_admin():
    try:
        db = Session()
        encrypted_password = get_hashed_password("K3YL2yj5vdKkTwo&3UCPX95t29%i@")
        admin_data = {
            "email":"superadmin@admin.com",
            "password":encrypted_password,
            "role":"admin",
            "firstname":"user",
            "lastname":"admin"    
        }
        if db.query(UserModel).count() == 0:    
            super_admin = UserModel(**admin_data)
            db.add(super_admin)
            db.commit()
        pass
    except Exception as e:
        db.rollback()
        pass

def save_all_asset():
    try:
        db = Session()
        list_assets = [
        #  {
        #     "active_id":"FX:EURUSD",
        #     "name":"EURUSD",
        #     "type":"forex",
        #     "status":True
        # },{
        #     "active_id":"FX:GBPUSD",
        #     "name":"GBPUSD",
        #     "type":"forex",
        #     "status":True
        # },{
        #     "active_id":"FX:USDJPY",
        #     "name":"USDJPY",
        #     "type":"forex",
        #     "status":True
        # },
        # {
        #     "active_id":"FX:USDCHF",
        #     "name":"USDCHF",
        #     "type":"forex",
        #     "status":True
        # },
        {
            "active_id":"BINANCE:BTCUSDT",
            "name":"BTCUSDT",
            "type":"crypto",
            "status":True
        },
        {
            "active_id":"BINANCE:ETHUSDT",
            "name":"ETHUSDT",
            "type":"crypto",
            "status":True
        },
        {
            "active_id":"BINANCE:SOLUSDT",
            "name":"SOLUSDT",
            "type":"crypto",
            "status":True
        },
        {
            "active_id":"BINANCE:XRPUSDT",
            "name":"XRPUSDT",
            "type":"crypto",
            "status":True
        },{
            "active_id":"BINANCE:ADAUSDT",
            "name":"ADAUSDT",
            "type":"crypto",
            "status":True
        }]
        #Add new asset if asset list in model is empty
        if db.query(AssetModel).count() == 0:
                for asset in list_assets:
                    new_asset = AssetModel(**asset)
                    db.add(new_asset)
                db.commit()
                print("Assets added")
    except Exception as e:
        print(f"Error: {e}")
            

        pass
    except Exception as e:
        print(e)
        pass

# Schedule the task to run every 30 minutes
I_want_money = None
async def connect_iq_option():
    global I_want_money
    print("Login...")
    #I_want_money = IQ_Option("rafajos9@gmail.com","123456")
    #I_want_money.connect()  # Connect IQ Option
    print("Start stream...")
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    #startup
   #await connect_iq_option()
   create_admin()
   save_all_asset()
   asyncio.create_task(send_assets(AsyncSessionLocal()))
   yield


app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    stats.router,
    prefix="/api/stats",
    tags=["stats"]
)

app.include_router(
   payments.router,
   prefix="/api/payments",
   tags=["payments"]
)

app.include_router(
   trades.router,
   prefix="/api/operation",
   tags=["operation"]
)

app.include_router(
   withdraws.router,
   prefix="/api/withdraw",
   tags=["operation"]
)

app.include_router(
   user.router,
   prefix="/api/user",
   tags=["users"]
)

app.include_router(
   assets.router,
   prefix="/api/assets",
   tags=["assets"]
)
app.include_router(
   affiliates.router,
   prefix="/api/affiliates",
   tags=["affiliates"]
)
#Web sockets

# Variables globales
clients: Dict[str, WebSocket] = {}  # Changed to a dictionary
client_info = {}  # Dictionary to store client-specific information




#Check if user trades active win or loose 
def calculate_percent(number,percent):
    return float(number) * percent

def calculate_income(number, percent):
    total_income = float(number) * percent
    additional_income = total_income - float(number)  # Calculate the additional income
    return additional_income  # Return both total and additional income

def get_commission_percentage(affiliate_level: int, commission_type: str) -> float:
    """
    Retorna el porcentaje de comisión basado en el nivel del afiliado y el tipo de transacción.
    
    - Para 'loss' (reparto de ingresos), por ejemplo, 10% por nivel hasta un máximo de 80%.
    - Para 'volume' (facturación total), por ejemplo, 1% por nivel hasta un máximo de 5%.
    
    Ajusta estos valores según tu modelo de negocio.
    """
    if commission_type == 'loss':
        return min(0.10 * affiliate_level, 0.80)
    elif commission_type == 'volume':
        return min(0.01 * affiliate_level, 0.05)
    return 0.0

def registrar_earning(db, affiliate_id, transaction, affiliate_level: int, K_factor: float = 1.0):
    """
    Calcula la comisión para una transacción y registra un registro en AffiliateEarnings,
    utilizando los parámetros definidos en AFFILIATE_LEVELS:
    
      - Para Revenue Share (income_split): 
            Comisión = |pérdida| * (base_income / 100)
      - Para Turnover Share (total_billing): 
            Comisión = volumen * (billing_factor / 100) * K_factor
    
    :param db: Sesión de base de datos.
    :param affiliate_id: ID del afiliado.
    :param transaction: Objeto de la transacción (AffiliateTransactions).
    :param affiliate_level: Nivel del afiliado.
    :param K_factor: Factor de ajuste para Turnover Share (por defecto 1.0).
    """
    print("data earning", transaction, affiliate_id, affiliate_level)
    print("Tipo de transaction.amount:", type(transaction.amount), "Valor:", transaction.amount)
    
    # Obtener los parámetros para el nivel actual
    params = AFFILIATE_LEVELS.get(affiliate_level)
    if params:
        base_income = params["base_income"]        # Porcentaje para Revenue Share (ej. 50, 55, etc.)
        billing_factor = params["billing_factor"]    # Porcentaje para Turnover Share (ej. 2.0, 2.5, etc.)
    else:
        # Valores por defecto en caso de no encontrar el nivel
        base_income = 50
        billing_factor = 2.0

    commission_value = 0.0

    if transaction.transaction_type == "loss":
        # Para Revenue Share, usamos el porcentaje base_income
        # Se espera que transaction.amount sea la magnitud de la pérdida
        porcentaje = base_income / 100  # Ejemplo: 50% => 0.50
        commission_value = abs(float(transaction.amount)) * porcentaje
        print(f"Revenue Share: Pérdida = {transaction.amount}, Porcentaje = {porcentaje}")
        
    elif transaction.transaction_type == "volume":
        # Para Turnover Share, usamos el billing_factor
        porcentaje = billing_factor / 100  # Ejemplo: 2.0% => 0.02
        commission_value = float(transaction.amount) * porcentaje * K_factor
        print(f"Turnover Share: Volumen = {transaction.amount}, Porcentaje = {porcentaje}, K = {K_factor}")
        
    else:
        print("Tipo de transacción no reconocido:", transaction.transaction_type)
    
    # Registrar el earning en la tabla AffiliateEarnings:
    earning_record = AffiliateEarnings(
        affiliate_id=affiliate_id,
        transaction_id=transaction.id,
        earnings=commission_value
    )
    db.add(earning_record)
    db.commit()
    print(f"Registrada ganancia: {commission_value} para transacción {transaction.id}")




async def registrar_transacciones_afiliado(trade_data, message_socket, affiliate_link_id, user_id_uuid):
    """
    Registra la transacción de afiliado (volumen o pérdida) según el modelo asignado al enlace.
    Se ejecuta en un thread aparte para no bloquear el event loop.
    """
    def _registro_transacciones():
        db = Session()  # sesión síncrona
        print("creando transacciones de afiliado...")
        try:
            # 1. Obtener el objeto del enlace y del afiliado
            affiliateLink_smt = db.execute(
                select(AffiliateLinks).where(AffiliateLinks.id == affiliate_link_id)
            )
            affiliateLink = affiliateLink_smt.scalars().first()
            if not affiliateLink:
                print("No se encontró el AffiliateLink con id:", affiliate_link_id)
                return

            affiliate_smt = db.execute(
                select(Affiliates).where(Affiliates.id == affiliateLink.affiliate_id)
            )
            affiliate = affiliate_smt.scalars().first()
            if not affiliate:
                print("No se encontró el afiliado con id:", affiliateLink.affiliate_id)
                return

            print(f"Afiliado id: {affiliate.id} | Programa: {affiliateLink.affiliate_program}")

            # 2. Registrar la transacción según el modelo del enlace
            if affiliateLink.affiliate_program == LinkProgram.total_billing:
                # Modelo total_billing: se registra solo la transacción de volumen.
                volume_tx = AffiliateTransactions(
                    affiliate_link_id=affiliate_link_id,
                    client_id=user_id_uuid,
                    amount=trade_data['amount'],  # Monto operado
                    transaction_type="volume"
                )
                db.add(volume_tx)
                db.flush()
                registrar_earning(db, affiliate.id, volume_tx, affiliate.affiliate_level)
            
            elif affiliateLink.affiliate_program == LinkProgram.income_split:
                # Modelo income_split: se registra solo la transacción de pérdida,
                # pero únicamente si el trade NO fue ganador.
                if not message_socket.get("winner", False):
                    # Calcular la pérdida en función de la dirección del trade:
                    if trade_data['direction'] == "up":
                        loss_amount = float(trade_data['entry']) - float(trade_data['close'])
                    else:
                        loss_amount = float(trade_data['close']) - float(trade_data['entry'])
                    

                    loss_tx = AffiliateTransactions(
                        affiliate_link_id=affiliate_link_id,
                        client_id=user_id_uuid,
                        amount=loss_amount,
                        transaction_type="loss"
                    )
                    db.add(loss_tx)
                    db.flush()
                    registrar_earning(db, affiliate.id, loss_tx, affiliate.affiliate_level)
                else:
                    print("Trade ganador, no se registra transacción 'loss' para income_split.")
            else:
                print("Modelo de enlace no reconocido:", affiliateLink.affiliate_program)

            # 3. Confirmar las transacciones
            db.commit()
        except Exception as e:
            print(f"Error en registrar_transacciones_afiliado: {e}")
            db.rollback()
        finally:
            db.close()

    # Ejecutar la función de registro en un thread aparte para no bloquear el loop principal.
    await asyncio.to_thread(_registro_transacciones)

#check operation websocket
async def check_operation_socket(user_id:str,operation_id:str, all:bool):
    try:
         db = Session()
         #first search the operation
         message_socket = {}
         operation_uuid = None
         user_id_uuid = uuid.UUID(user_id)
         if operation_id:
            operation_uuid = uuid.UUID(operation_id)
         stmt_user = select(UserModel).where(UserModel.user_id == user_id_uuid)
         result_user =  db.execute(stmt_user)
         user_data = result_user.scalars().all()
         stmt = None
         # Give all or select operations
         if all:
            stmt = select(Operation).where(Operation.is_verified == False, Operation.user_id == user_id_uuid) 
         else:
            stmt = select(Operation).where(Operation.is_verified == False, Operation.operation_id == operation_uuid, Operation.user_id == user_id_uuid)
         result =  db.execute(stmt)
         trades_list = result.scalars().all()
         user_data_dump = jsonable_encoder(user_data[0])
         #Set the balance to change
         balance_change_demo = user_data_dump['balance_demo']
         balance_change_real = user_data_dump['balance_real']
         print(trades_list)
         for trade in trades_list:
            update_balance = None
            update_stmt = None
            asset_profit_evalue = 1
            #Verify asset in trade
            if trade.asset.in_custom:
               asset_profit_evalue = trade.asset.custom_profit
            else:
               asset_profit_evalue = trade.asset.profit

            profit_income = calculate_percent(trade.amount,float(asset_profit_evalue)) #profit 1 ~ 1.9
            added_income = calculate_income(trade.amount,float(asset_profit_evalue))
            print(trade.operation_mode)
            #Check operation in request binance api
            result_trade_close = 0
            data_candle = None
            data_response_candle = None 

            # if trade asset is type crypto, check operation in binance
            if trade.asset.type == "crypto":
                url = "https://api.binance.com/api/v3/klines"
                params = {
                        'symbol': trade.asset.name,
                        'interval': '1s',
                        'endTime': trade.time_end,
                        'limit': 1  # Maximum number of data points to return
                    }
                        
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data_response_candle = response.json()  # Return the JSON response
                    data_candle = {
                        "initial":data_response_candle[0][0],
                        "close":data_response_candle[0][4],
                        "to":data_response_candle[0][6]
                        }
                
                message_socket['operation_id'] = operation_id

            #if trade asset is type forex, check operation with api forex

            if trade.asset.type == "forex":
                continue
                # Get the current date and time with UTC timezone
                now = datetime.now(timezone.utc)
                # Create a new datetime object adjusted by the timezone offset
                adjusted_time = now + timedelta(minutes=-0)
                unix_timestamp_seconds = int(adjusted_time.timestamp())
                # Convert to Unix timestamp in milliseconds
                unix_timestamp_milliseconds = unix_timestamp_seconds * 1000
                print("TRADE PENDING", jsonable_encoder(trade))
                if unix_timestamp_milliseconds < trade.time_end:
                    continue
                #Change this, need remove iqoption
                #data_candle = I_want_money.get_candles(trade.asset.name.upper(),1,1,int(trade.time_end / 1000))
                print(data_candle)
                if not data_candle[0]:
                    continue

                data_candle={"close":data_candle[0]["close"], "to":unix_timestamp_milliseconds}

            
            timestamp_end = datetime.fromtimestamp(trade.time_end / 1000) 
            message_socket['closed_at'] = timestamp_end.isoformat()
            print(data_response_candle)
            if trade.asset.type == "crypto" and data_candle['initial'] < trade.time_end:
                continue
           

            elif float(data_candle["close"]) > float(trade.entry) and trade.direction == "up": 
                update_stmt = update(Operation).where(Operation.operation_id == trade.operation_id).values(winner=True, is_verified=True, income=f"{profit_income:.2f}", close=f"{float(data_candle['close'])}", closed_at=timestamp_end )
                message_socket['winner'] = True
                message_socket['close'] = float(data_candle["close"])
                message_socket['income'] = f"{profit_income:.2f}"
                message_socket['trade'] = jsonable_encoder(trade)
                
                # Update trade mode demo

                if trade.operation_mode == 0:
                    final_balance = (float(balance_change_demo) + float(trade.amount)) + (float(added_income))
                    balance_change_demo = final_balance
                    message_socket['final_balance'] = final_balance
                    user_data_dump['balance_demo'] = final_balance
                    update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_demo=f"{final_balance}")
                
                #update trade mode real
                if trade.operation_mode == 1:
                    final_balance = (float(balance_change_real) + float(trade.amount)) + (float(added_income))
                    balance_change_real = final_balance
                    message_socket['final_balance'] = final_balance
                    user_data_dump['balance_real'] = final_balance
                    update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_real=f"{final_balance}")
                
            elif float(data_candle["close"]) < float(trade.entry) and trade.direction == "down": #Check if direction down and win
                update_stmt = update(Operation).where(Operation.operation_id == trade.operation_id).values(winner=True, is_verified=True, income=f"{profit_income:.2f}", close=f"{float(data_candle['close'])}", closed_at=timestamp_end )
                    # Update account mode demo
                message_socket['winner'] = True
                message_socket['close'] = float(data_candle["close"])
                message_socket['income'] = f"{profit_income:.2f}"
                message_socket['trade'] = jsonable_encoder(trade)

                if trade.operation_mode == 0:
                    final_balance = (float(balance_change_demo) + float(trade.amount)) + (float(added_income))
                    balance_change_demo = final_balance
                    message_socket['final_balance'] = final_balance
                    user_data_dump['balance_demo'] = final_balance
                    update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_demo=f"{final_balance}")

                if trade.operation_mode == 1:
                    final_balance = (float(balance_change_real) + float(trade.amount)) + (float(added_income))
                    balance_change_real = final_balance
                    message_socket['final_balance'] = final_balance
                    user_data_dump['balance_real'] = final_balance
                    update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_real=f"{final_balance}")
                
            else:
                if data_candle:
                    update_stmt = update(Operation).where(Operation.operation_id == trade.operation_id).values(winner=False, is_verified=True, close=f"{float(data_candle['close'])}", closed_at=timestamp_end )
                    message_socket['winner'] = False
                    message_socket['close'] = float(data_candle["close"])
                    message_socket['income'] = "0"
                    message_socket['trade'] = jsonable_encoder(trade)
                    # Update account mode demo
                    if trade.operation_mode == 0:
                        final_balance = float(balance_change_demo) 
                        balance_change_demo = final_balance
                        message_socket['final_balance'] = final_balance
                        user_data_dump['balance_demo'] = final_balance
                        update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_demo=f"{final_balance}")

                    if trade.operation_mode == 1:
                        final_balance = float(balance_change_real) 
                        balance_change_real = final_balance
                        message_socket['final_balance'] = final_balance
                        user_data_dump['balance_real'] = final_balance
                        update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_real=f"{final_balance}")

            db.execute(update_stmt)
            db.execute(update_balance)
            print(f"Trade mode: {trade.operation_mode} - Affiliated code: {user_data_dump.get('affiliated_code')}")

# Verificar que el trade sea en modo real y el usuario tenga código de afiliado
            if trade.operation_mode == 1 and user_data_dump.get('affiliated_code'):
                try:
                    # Buscar el enlace de afiliado usando select
                    stmt_affiliate = select(AffiliateLinks).where(
                        AffiliateLinks.link_code == user_data_dump['affiliated_code']
                    )
                    result_affiliate = db.execute(stmt_affiliate)
                    affiliate_link = result_affiliate.scalars().first()
                    print("Affiliate link encontrado:", affiliate_link.id)
                    if affiliate_link:
                        # Preparar los datos del trade para el registro de transacciones
                        trade_data = {
                            'amount': trade.amount,
                            'direction': trade.direction,
                            'entry': trade.entry,
                            'close': data_candle["close"]
                        }
                        # Ejecutar la función de registro en segundo plano
                        asyncio.create_task(
                            registrar_transacciones_afiliado(trade_data, message_socket, affiliate_link.id, user_id_uuid)
                        )

                except Exception as e:
                    print(f"Error al registrar transacciones de afiliado: {e}")
                    db.rollback()

            # Commit final de las actualizaciones del trade y balance
            db.commit()

            if all:
                return True
            
            message_socket['user_data'] = {
                "account_mode": user_data_dump['account_mode'],
                "balance_demo": user_data_dump['balance_demo'],
                "balance_real": user_data_dump['balance_real']
            } 

            print(message_socket)
            return message_socket
    except Exception as e:
        print(e)
        db.rollback()
        if all:
            return False
        return False


@app.post("/api/register")
async def register_user(
    afficode: Optional[str] = Query(None, alias="ref"),  # Aquí se indica que "ref" en la URL se asigna a "afficode"
    userData: RegisterCredentials = Body(),
    db: AsyncSession = Depends(get_async_db)
):
    # Validar aceptación de términos
    if not userData.accept_terms:
        raise HTTPException(status_code=400, detail="Debe aceptar los términos y condiciones")
    
    # Validar edad
    if calculate_age(userData.birthday) < 18:
        raise HTTPException(status_code=400, detail="Debe ser mayor de edad")
    
    try:
        # Verificar si el usuario ya existe
        stmt = select(UserModel).where(UserModel.email == userData.email)
        result = await db.execute(stmt)
        user_data = result.scalars().first()
        
        if user_data:
            raise HTTPException(status_code=409, detail="Este correo ya está registrado")
        
        # Inicializamos la variable para el código afiliado
        affiliated_code = None
        affiliate_id = None  # Inicializamos la variable para el ID del afiliado
        
        # Si se recibió un código de referido, se verifica que exista
        if afficode:
            affiliateLinkExistQuery = await db.execute(
                select(AffiliateLinks).where(AffiliateLinks.link_code == afficode)
            )
            affiliateLinkExist = affiliateLinkExistQuery.scalars().first()
            if affiliateLinkExist:
                affiliated_code = afficode
                affiliate_id = affiliateLinkExist.affiliate_id  # Obtener el ID del afiliado

        # Preparar los datos del nuevo usuario
        new_user = {
            "email": userData.email,
            "password": get_hashed_password(userData.password),
            "firstname": userData.firstname,
            "lastname": userData.lastname,
            "birthday": userData.birthday,
            "country": userData.country,
            "phone_number": userData.phone_number,
            "accept_terms": userData.accept_terms,
            "role": userData.role
        }
        
        # Si se verificó que el código afiliado existe, se añade al usuario
        if affiliated_code:
            new_user["affiliated_code"] = affiliated_code

        # Agregar el usuario a la base de datos
        new_user_register = UserModel(**new_user)
        db.add(new_user_register)
        await db.commit()
        await db.refresh(new_user_register)

        # Si hay un afiliado válido, registrar la referencia
        if affiliate_id:
            new_referral = AffiliateReferrals(
                affiliate_id=affiliate_id,
                referred_user_id=new_user_register.user_id,  # ID del usuario recién registrado
                referred_at=datetime.utcnow()
            )
            db.add(new_referral)
            await db.commit()

        return JSONResponse({"message": "User Created"}, status_code=201)
    
    except Exception as e:
        await db.rollback()  # Rollback en caso de error
        print(f"Error: {e}")  # Log para depuración
        raise HTTPException(status_code=500, detail=f"Hubo un error al registrarte {e}")



@app.get("/api/count")
async def usersCount(db: AsyncSession = Depends(get_async_db)):
    try:
        # Execute the query to fetch all user IDs from the database
        query = await db.execute(select(UserModel.user_id))
        result = query.scalars().all()
    except Exception as e:
        print(f"Error getting all the users: {e}")
        return {"error": "Unable to fetch users"}

    # Convert the result (list of user IDs) into a set for set operations
    all_users = set(result)
    
    # Calculate online and offline users
    online_users = len(connected_users)
    offline_users = len(all_users - connected_users)  # Calculate users not currently online

    return {"online": online_users, "offline": offline_users}



@app.post("/api/login")
async def login_user(user: User, response: Response,  db: AsyncSession = Depends(get_async_db)):
    try:
        # Query the user from the database
        result = await db.execute(select(UserModel).where(UserModel.email == user.email))
        user_record = result.scalars().first()  # Get the first user object

        if user_record:
            # Encode and remove sensitive information
            user_data = jsonable_encoder(user_record)
            user_data_show = user_data.copy()
            user_data_show.pop('password', None)  # Remove sensitive information
            
            # Check if the user is blocked
            if not user_data["block"]:
                # Verify the password
                if verify_password(user.password, user_data['password']):
                    # Generate the token
                    minimal_data = {
                    "user_id": user_data["user_id"],
                    "firstname": user_data["firstname"],
                    "lastname": user_data["lastname"],
                    "email": user_data["email"],
                    "rol": user_data["role"],
                    "is_affiliate": user_data["is_affiliate"]
                }

                # Generate tokens
                    AccessToken = write_token(minimal_data)
                    RefreshToken = write_refresh_token(minimal_data)

                    
                    await db.execute(
                            update(UserModel)
                            .where(UserModel.email == user.email)
                            .values(refreshToken=RefreshToken)
                        )
                    await db.commit()
                    # Set the secure cookie
                    response = JSONResponse(
                        content={
                            "message": "logged",
                            "user_data": minimal_data,
                            "access_token": AccessToken
                        },
                        status_code=200,
                    )
                    response.set_cookie(
                        key="refresh_token", 
                        value=RefreshToken,
                        httponly=True,  # Prevent JavaScript access
                        secure=True,   # Use HTTPS only
                        samesite="None",  # Control cross-site behavior
                        max_age=3600,  # Expiration time in seconds
                    )
                    return response
                else:
                    raise HTTPException(status_code=404, detail="Contraseña o email incorrecto")
            else:
                raise HTTPException(status_code=404, detail="Usuario suspendido")
        else:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        print("error",e)
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
@app.get("/api/refresh")
async def update_refresh_token(req: Request, db: AsyncSession = Depends(get_async_db)):
    try:
        # Get the refresh token from cookies
        refresh_token = req.cookies.get("refresh_token")
        if not refresh_token:
            return JSONResponse(
                {"message": "No se encontró un refresh token en las cookies"},
                status_code=400,
            )

        # Query the user based on the refresh token
        try:
            result = await db.execute(select(UserModel).where(UserModel.refreshToken == refresh_token))
            found_user = result.scalar()
            user_data = jsonable_encoder(found_user)
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos {e}")

        if not user_data:
            return JSONResponse(
                {"message": "No se ha encontrado un usuario asociado al refresh token"},
                status_code=404,
            )

        # Validate the refresh token
       # Validar el refresh token
        try:
            verify_token = validate_refresh_token(refresh_token)
        except HTTPException as http_exc:
            return JSONResponse({"message": http_exc.detail}, status_code=http_exc.status_code)


        # Prepare the payload for the new access token
        payload = {
            "user_id": user_data["user_id"],
                    "firstname": user_data["firstname"],
                    "lastname": user_data["lastname"],
                    "email": user_data["email"],
                    "rol": user_data["role"]
        }

        # Generate a new access token
        try:
            new_access_token = write_token(payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al generar el token de acceso {e}")

        return JSONResponse(
            {"access_token": new_access_token}, status_code=200
        )

    except HTTPException as http_exc:
        return JSONResponse({"message": http_exc.detail}, status_code=http_exc.status_code)

    except Exception as e:
        # Catch any unexpected error
        return JSONResponse(
            {"message": f"Error inesperado: {str(e)}"}, status_code=500
        )
        
@app.post("/api/verify/token")
async def verify_token(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        return JSONResponse({"message": "No token provided"}, status_code=401)
    
    return validate_refresh_token(token,output=True)
        
@app.get("/api/logout")
async def logout(req: Request, response: Response, db: AsyncSession = Depends(get_async_db)):
    try:
        # Obtener la cookie refresh_token desde la solicitud
        cookie = req.cookies.get("refresh_token")
        if not cookie:
            return JSONResponse(
                status_code=204
            )
        
        # Buscar al usuario con el refreshToken
        result = await db.execute(select(UserModel).where(UserModel.refreshToken == cookie))
        found_user = result.scalar()
        user_data = jsonable_encoder(found_user)
        
        if not user_data:
            response = JSONResponse(
                {"message": "Logged out successfully"},
                status_code=204
            )
            # Eliminar la cookie del cliente
            response.delete_cookie("refresh_token", httponly=True, secure=True)
            return response
        
        # Actualizar el refreshToken del usuario a None
        await db.execute(update(UserModel).where(UserModel.user_id == user_data["user_id"]).values(refreshToken=None))
        await db.commit()
        
        # Crear una respuesta y eliminar la cookie
        response = JSONResponse(
            {"message": "Logged out successfully"},
            status_code=204
        )
        response.delete_cookie("refresh_token", httponly=True, secure=True)
        return response
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )

             
        

@app.get("/api/trades/check/{user_id}")
async def check_trades(user_id: str):
   try:
    await check_operation_socket(user_id,None,True)
    return JSONResponse({"message":"trades updated"},status_code=200)
   except Exception as e:
    return JSONResponse({"message":"error"},status_code=402)



# Dictionary to store connected clients by user_id
connected_clients: Dict[str, List[WebSocket]] = {}

async def all_assets_broker(db):

    try:
        stmt = select(AssetModel).where(AssetModel.status == True)
        result = await db.execute(stmt)
        asset_db = result.scalars().all()
        print(f"assets ws f{asset_db}")

        return jsonable_encoder(jsonable_encoder(asset_db))
    except Exception as e:
        print(e)
        return jsonable_encoder([])

active_task = None
assets = None
async def send_assets(db):
    global assets
    while True:
        assets = await all_assets_broker(db)
        await asyncio.sleep(100)  # Adjust the frequency as needed
        
@app.websocket("/ws/assets/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    global active_task
    global assets
    await websocketManager.connect(websocket, "assets", user_id)
    try:
            # Keep the connection open and handle incoming messages if needed
            while True:
                if assets:
                    await websocket.send_json({"assets": assets})
                    await asyncio.sleep(105)

    except WebSocketDisconnect:
        await websocketManager.disconnect("assets", websocket, user_id)
    except Exception as e:
        print(f"Error occurred: {e}")

#Este endpoint es solo para hacer pruebas del chart directas desde el front sin necesidad de servirlo aca en el back,
#de forma contaria apareceran problemas de cors en el front
@app.get("/binance/klines")
async def get_klines(symbol: str, interval: str, limit: int = 1000): 
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    return response.json()


##To listen request operation finish
@app.websocket("/ws/operation")
async def websocket_operation(websocket: WebSocket):
    # Extract query parameters from the WebSocket request

    # Accept the WebSocket connection
    await websocketManager.connect(websocket, "operations","")

    try:
        while True:
            # Listen for incoming messages
            data = await websocket.receive_json()
            # Process the received message 
            if data:
                response = await check_operation_socket(data['user_id'], data['operation_id'], False)
                await websocketManager.send_personal_message(response, websocket)
    except WebSocketDisconnect:
        await websocketManager.disconnect("operations", websocket, data['operation_id'])

#Server static files html


# Sets the templates directory to the `build` folder from `npm run build`
# this is where you'll find the index.html file.
templates = Jinja2Templates(directory="./static")

# Mounts the `static` folder within the `build` folder to,nnn,mx the `/static` route.
app.mount('/assets', StaticFiles(directory="./static/assets"), 'assets')

# sets up a health check route. This is used later to show how you can hit
# the API and the React App url's
@app.get('/api/health')
async def health():
    return { 'status': 'healthy' }


# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/app/{catchall:path}")
async def react_app(req: Request, catchall: str):
    return templates.TemplateResponse('index.html', { 'request': req })

@app.get("/")
async def redirect_app():
    return RedirectResponse(direction)
    

