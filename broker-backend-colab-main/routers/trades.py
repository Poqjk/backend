from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy import update
from models.asset import Asset as AssetModel
from models.user import User as UserModel
from tradingview_ta import TA_Handler, Interval
import requests
import time
from decimal import Decimal
from models.operation import Operation as OperationModel
from config.database import AsyncSession, get_async_db
from datetime import datetime, timedelta, timezone
from middlewares.verify_token_routes import VerifyTokenRoute 
import uuid


router = APIRouter(route_class=VerifyTokenRoute)

class Operation(BaseModel):
    timer:int
    asset_id:str
    direction:str
    amount:str
    user_id: str

def is_valid_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

@router.post("/add/trade/{timeframe}")
async def set_trade(operation:Operation, timeframe: str, db: AsyncSession = Depends(get_async_db)):
    try:
        parse_user_id = None
        trade_information = operation.model_dump()
        print(trade_information)
        # Get the current date and time with UTC timezone
        now = datetime.now(timezone.utc)

        # Get the timezone offset in minutes
        offset = now.utcoffset()
        if offset is not None:
            timezone_offset = 0
        else:
            timezone_offset = 0

        # Create a new datetime object adjusted by the timezone offset
        adjusted_time = now + timedelta(minutes=-timezone_offset)

        print("Adjusted Time:", adjusted_time)
        # Convert adjusted_time to Unix timestamp in seconds
        unix_timestamp_seconds = int(adjusted_time.timestamp())
        # Convert to Unix timestamp in milliseconds
        unix_timestamp_milliseconds = unix_timestamp_seconds * 1000
        print("Unix time in milliseconds:", unix_timestamp_milliseconds)
        if int(operation.timer) == 0:
            return JSONResponse({"message":"error to generate trade"}, status_code=402)
        
        if trade_information['user_id'] and is_valid_float(trade_information['amount']):
            parse_user_id = uuid.UUID(trade_information['user_id'])
        else:
            return JSONResponse({"message":"error to generate trade"}, status_code=402)
        
        trade_information['operation_mode'] = 0 #demo
        trade_information['user_id'] = parse_user_id
        print(trade_information['asset_id'])
        trade_information['asset_id'] = uuid.UUID(trade_information['asset_id'])

        #Check if more 8 operations opens
        stmt_pendings = select(OperationModel).join(AssetModel).where(OperationModel.user_id == parse_user_id, OperationModel.is_verified == False)
        result_pendings =  await db.execute(stmt_pendings)
        trades_pendings = result_pendings.scalars().all()
        print("////////////////// CHECK PASS OPERATION ////////////////")
        if len(trades_pendings) >= 12:
            return JSONResponse({"message":"Limite de operaciones abiertas superado, revisa que tus operaciones finalicen"},status_code=400)


        ##Check amount
        stmt_user = select(UserModel).where(UserModel.user_id == parse_user_id)
        result_user =  await db.execute(stmt_user)
        user_data = result_user.scalars().all() 
        user_data_dump = user_data[0]
        balance_change = 0

        print("////////////////// CHECK PASS AMOUNT ////////////////")

        #Check the balance to the trade
        if user_data_dump.account_mode == 0:
            trade_information["operation_mode"] = 0
            balance_change = user_data_dump.balance_demo
        else:
            trade_information["operation_mode"] = 1
            balance_change = user_data_dump.balance_real
        
        if Decimal(balance_change) < Decimal(trade_information['amount']):
            return JSONResponse({"message":"Saldo insuficiente"},status_code=400)
        
        print("////////////////// CHECK PASS AMOUNT ////////////////")
        #Set data to register trade
        
        #If asset_id if type crypto obtain candle from binance
        asset_data_dump = None

        stmt = select(AssetModel).where(AssetModel.id == trade_information['asset_id'])
        result = await db.execute(stmt)
        asset_data = result.scalars().first()  # Retrieve the first matching result
        print(f"asset found {asset_data}")
        if not asset_data:
            return JSONResponse({"message": "Asset not found"}, status_code=404)
        asset_data_dump = jsonable_encoder(asset_data)

        
        asset_data_dump = jsonable_encoder(asset_data)
        data_candle = None
        
        #Check if asset if avalaible to trade
        if asset_data_dump['status'] == False or asset_data_dump['available_broker'] == False:
            return JSONResponse({"message":"error"}, status_code=402)
        
        print("////////////////// CHECK TYPE  ////////////////")
        if asset_data_dump['type'] == "crypto":
            #Range time estimated for binance
            trade_information['time_start'] = unix_timestamp_milliseconds
            trade_information['time_end'] = int(unix_timestamp_milliseconds) + (int(trade_information['timer']) * 1000)

            print("////////////////// TYPE CRYPTO  ////////////////")
            url = "https://api.binance.com/api/v3/klines"
            params = {
                    'symbol': asset_data_dump['name'],
                    'interval': timeframe,
                    'endTime': trade_information['time_start'],
                    'limit': 1  # Maximum number of data points to return
            }
                            
            response = requests.get(url, params=params)
            print("////////////////////GET RESPONSE//////////////////////")
            print(response.json())
            if response.status_code == 200:
                data_response_candle = response.json()  # Return the JSON response
                data_candle = {
                    "initial":data_response_candle[0][0],
                    "close":data_response_candle[0][4]
            }
            print("no req")  
        #Set trade if forex type
        if asset_data_dump['type'] == "forex":
            return JSONResponse({"message":"error"}, status_code=402)
            ##Check if asset is open
            response = requests.get(f"https://www.freeforexapi.com/api/live?pairs={asset_data_dump['name']}")
            data_json = response.json()
            if not data_json['rates']:
                return JSONResponse({"message":"El mercado seleccionado no esta disponible"}, status_code=402)
            data_tv = TA_Handler(
                symbol=asset_data_dump['name'],
                screener="forex",
                exchange="FX_IDC",
                interval=Interval.INTERVAL_1_MINUTE
                # proxies={'http': 'http://example.com:8080'} # Uncomment to enable proxy (replace the URL).
            )
            data_tc_dump = jsonable_encoder(data_tv.get_analysis())
            print(data_tc_dump)

            time = data_tc_dump['time']
            close_trade = data_tc_dump["indicators"]["close"]
             # Parse the ISO 8601 datetime string to a datetime object
            dt = datetime.fromisoformat(time)
            
            # Convert the datetime object to a Unix timestamp in milliseconds
            unix_timestamp_ms = int(dt.timestamp() * 1000)
            
            print("UNIX TIME TRADINGVIEW:  ",unix_timestamp_ms)
            print("UNIX TIME SERVER:   ",unix_timestamp_milliseconds)
            trade_information['time_start'] = unix_timestamp_ms
            trade_information['time_end'] = int(unix_timestamp_ms) + (int(trade_information['timer']) * 1000)
            data_candle={"close":close_trade}
            print(data_candle)
            

        trade_information['entry'] = data_candle["close"]

        final_balance = Decimal(balance_change) - Decimal(trade_information['amount'])
        balance_change = final_balance
        if user_data_dump.account_mode == 0:
            update_user = update(UserModel).where(UserModel.user_id == parse_user_id).values(balance_demo=f"{final_balance}")
        else:
            update_user = update(UserModel).where(UserModel.user_id == parse_user_id).values(balance_real=f"{final_balance}")
        new_trade = OperationModel(**trade_information)
        db.add(new_trade)
        await db.execute(update_user)
        await db.commit()
        # Refresh the instance to get the updated state from the database
        db.refresh(new_trade)


        # Refresh the user data to get the updated state
        await db.refresh(user_data_dump)
        #Return the user data updated 
        user_data_trade = jsonable_encoder(user_data_dump)
        data = {
            "account_mode":user_data_trade['account_mode'],
            "balance_demo":user_data_trade['balance_demo'],
            "balance_real":user_data_trade['balance_real']
        }
        print(new_trade)
        return JSONResponse({"message":"created", "trade":jsonable_encoder(new_trade), "user_data":jsonable_encoder(data)}, status_code=200)
    except Exception as e:
        await db.rollback()
        print(e)
        return JSONResponse({"message":f"error {e}"}, status_code=402)
    
    finally:
       if db:
        await db.close()


@router.get("/{user_id}/balance")
async def register_user(user_id:str,db: AsyncSession = Depends(get_async_db)):
    
    print(user_id)
    try:
        user_id_uuid = uuid.UUID(user_id)  
        stmt = select(UserModel).where(UserModel.user_id == user_id_uuid)
        result = await db.execute(stmt)
        user_data = result.scalars().all()
        # Check if user_data is empty
        if not user_data:
            return JSONResponse({"message":"Usuario no encontrado"},status_code=404)
        user_dump = jsonable_encoder(user_data[0])
        user_dump['password'] = ''
        userBalance = {
            "balance_real": user_dump["balance_real"],
            "balance_demo": user_dump["balance_demo"],
            "account_mode": user_dump["account_mode"]
        }
        return JSONResponse({"user_data":userBalance}, status_code=200)
    except Exception as e:
        db.rollback()
        print(e)
        return JSONResponse({"message":"error"}, status_code=402)
        
    finally:
        await db.close()


@router.get("/{user_id}/change/mode/{mode}")
async def change_balance(user_id:str, mode:int, db: AsyncSession = Depends(get_async_db)):
  
    if mode < 0 and mode > 1:
        return JSONResponse({"message":"El modo de la cuenta no es valido"}, status_code=402)

    try:
        user_id_uuid = uuid.UUID(user_id)  
        stmt = select(UserModel).where(UserModel.user_id == user_id_uuid)
        result = await db.execute(stmt)
        user_data = result.scalars().all()

        # Check if user_data is empty
        if not user_data:
            return JSONResponse({"message": "Usuario no encontrado"}, status_code=404)

        # Update the user's balance
        if int(mode) == 0:
            update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(account_mode=1)
        else:
            update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(account_mode=0)
        await db.execute(update_balance)
        await db.commit()

        # Refresh the first user instance in the list
        user_instance = user_data[0]
        db.refresh(user_instance)
        user_dump = jsonable_encoder(user_instance)
        data = {
            'account_mode':user_dump['account_mode'],
            'balance_demo':user_dump['balance_demo'],
            'balance_real':user_dump['balance_real']

        }

        return JSONResponse({
            "balance_user": data
        }, status_code=200)

    except Exception as error:
        await db.rollback()
        print(error)

@router.get("/{user_id}/balance/demo/refill")
async def refill_balance_demo(user_id: str, db: AsyncSession = Depends(get_async_db)):
   
    try:
        user_id_uuid = uuid.UUID(user_id)  
        stmt = select(UserModel).where(UserModel.user_id == user_id_uuid)
        result = await db.execute(stmt)
        user_data = result.scalars().all()

        # Check if user_data is empty
        if not user_data:
            return JSONResponse({"message": "Usuario no encontrado"}, status_code=404)

        # Update the user's balance
        update_balance = update(UserModel).where(UserModel.user_id == user_id_uuid).values(balance_demo="10000.00")
        await db.execute(update_balance)
        await db.commit()

        # Refresh the first user instance in the list
        user_instance = user_data[0]
        await db.refresh(user_instance)
        user_dump = jsonable_encoder(user_instance)
        data = {
            'account_mode':user_dump['account_mode'],
            'balance_demo':user_dump['balance_demo'],
            'balance_real':user_dump['balance_real']

        }

        return JSONResponse({
            "message": "Balance demo updated",
            "balance_demo": "10000.00",
            "balance_user": data
        }, status_code=200)

    except Exception as e:
        db.rollback()
        print(e)
        return JSONResponse({"message": "error"}, status_code=402)