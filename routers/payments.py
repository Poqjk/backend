import os
from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy import update
from models.user import User as UserModel
import requests
from models.operation import Operation as OperationModel
from models.payment import Payment as PaymentModel
from config.database import Session, AsyncSession, get_async_db
from middlewares.verify_token_routes import VerifyTokenRoute 
import uuid
from httpx import AsyncClient
from main import actualizar_nivel_afiliado
from models.affiliateLinks import AffiliateLinks
from utils import actualizar_nivel_afiliado

router = APIRouter(route_class=VerifyTokenRoute)

API_KEY_NOWPAYMENTS = os.getenv("API_KEY_NOWPAYMENTS") # Only from testing
class Payment(BaseModel):
    price_amount: str
    pay_currency:str
    order_id:str
    order_description:str
    user_id: str
    country:str
    pay_currency_format:str


class PaymentStatus(BaseModel):
    status:str
    
    
@router.get('/{user_id}/check/all')
async def check_payments_crypto_list(user_id: str, db: AsyncSession = Depends(get_async_db)):
        db = Session()
        try:
            headers = {
                'x-api-key': API_KEY_NOWPAYMENTS,
            }
            user_uuid = uuid.UUID(user_id)

            # Find the user
            result = await db.execute(select(UserModel).where(UserModel.user_id == user_uuid))
          
            customer_user = result.scalars().first()  # Get the first result
            customer_user_dump = jsonable_encoder(customer_user)
            balance_real_actual = float(customer_user_dump['balance_real'])

            # List transactions
            transactions_result = await db.execute(
                select(PaymentModel).where(
                    PaymentModel.user_id == user_uuid,
                    PaymentModel.status.in_(["waiting", "confirming", "sending"])
                )
            )
            transactions_user = transactions_result.scalars().all()

            if len(transactions_user) <= 0:
                return JSONResponse({"message":"Pagos actualizados"}, status_code=200)

            for transaction in transactions_user:
                transaction_dump = jsonable_encoder(transaction)

                # Make a synchronous HTTP request
                response = requests.get(f'https://api.nowpayments.io/v1/payment/{transaction_dump["payment_id"]}', headers=headers)
                data = response.json()  # No need to await

                # Update payment status
                updated_status = await db.execute(update(PaymentModel).where(PaymentModel.payment_id == transaction_dump['payment_id']).values(status=data['payment_status'])) 

                if data['payment_status'] == "confirmed":
                    balance_real_actual += float(data['price_amount'])

            # Update user balance
            update_balance = await db.execute( update(UserModel).where(UserModel.user_id == user_uuid).values(balance_real=f"{balance_real_actual}"))
            
            await db.commit()
            return JSONResponse({"message":"Pagos actualizados"}, status_code=200)

        except Exception as error:
            print(error)
            db.rollback()
            return JSONResponse({"message":"Error al actualizar los pagos"}, status_code=404)
    
@router.post('/crypto/create/')
async def create_payment(payment: Payment, db: AsyncSession = Depends(get_async_db)):
    # Verificar si el usuario tiene operaciones activas
    stmt = select(OperationModel).filter(
        OperationModel.user_id == payment.user_id,
        OperationModel.operation_mode == 1,
        OperationModel.is_verified == False
    )
    result = await db.execute(stmt)
    operationsl = result.scalars().all()

    if len(operationsl) > 0:
        return JSONResponse({"message": "Este usuario tiene operaciones activas"}, status_code=404)

    try:
        # Configurar headers y datos para la solicitud a NOWPayments
        headers = {
            'x-api-key': API_KEY_NOWPAYMENTS,
        }
        data_payment = {
            'price_amount': payment.price_amount,
            'price_currency': "usd",
            'pay_currency': payment.pay_currency,
            'ipn_callback_url': "https://nowpayments.io",
            'is_fee_paid_by_user': False,
            'is_fixed_rate': False,
            'order_id': payment.order_id,
            'order_description': payment.order_description,
        }

        # Realizar la solicitud de forma asíncrona
        async with AsyncClient() as client:
            response = await client.post('https://api.nowpayments.io/v1/payment', json=data_payment, headers=headers)

        response.raise_for_status()  # Levantar error si la solicitud falló
        data = response.json()

        # Preparar los datos para guardar en la base de datos
        user_id_uuid = uuid.UUID(payment.user_id)

        # Verificar si el usuario tiene un código de afiliado (es decir, si es referido)
        stmt_user = select(UserModel).where(UserModel.user_id == user_id_uuid)
        result_user = await db.execute(stmt_user)
        user_obj = result_user.scalars().first()
        stmt_affiliate = select(AffiliateLinks).where(AffiliateLinks.link_code == user_obj.affiliate_id)
        result_affiliate = await db.execute(stmt_affiliate)
        affiliate_link = result_affiliate.scalars().first()
        affiliate_id_value = None
        
        if user_obj and getattr(user_obj, "affiliated_code", None):
            
            affiliate_id_value = affiliate_link.affiliate_id
        if affiliate_id_value:  
            actualizar_nivel_afiliado(db,affiliate_link.affiliate_id)

        data_save = {
            'user_id': user_id_uuid,
            'amount': str(data.get('price_amount')),
            'payment_id': data.get('payment_id'),
            'currency': payment.pay_currency,  # Asumimos que este campo es correcto
            'type': "crypto",
            'status': data.get('payment_status'),
            'country': payment.country,
            'affiliate_id': affiliate_id_value  # Si el usuario tiene un código de afiliado, se agrega; sino, queda None.
        }
        new_payment = PaymentModel(**data_save)

        # Guardar en la base de datos
        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)

        return JSONResponse({"message": "Transacción creada", "payment": jsonable_encoder(data)}, status_code=200)

    except Exception as error:
        print(f"Error al crear depósito: {error}")
        await db.rollback()
        return JSONResponse({"message": "No se pudo completar la transacción"}, status_code=402)


@router.get('/crypto/updated/{payment_id}')
async def update_payment(payment_id:str,  db: AsyncSession = Depends(get_async_db)):

        try:
            headers = {
                'x-api-key': API_KEY_NOWPAYMENTS,
            }

            response = requests.get(f'https://api.nowpayments.io/v1/payment/{payment_id}', headers=headers)

            data = response.json()

            transaction_user = await db.query(PaymentModel).filter(PaymentModel.payment_id == payment_id).first()
            if not transaction_user:
                return JSONResponse({"message":"No se encontro la transaccion"}, status_code=404)
            #Save data in the bill 
            update_status = update(PaymentModel).where(PaymentModel.payment_id == payment_id).values(status=data['payment_status'])
            await db.execute(update_status)

            #Set balance in the user
            
            customer_user = await db.execute(select(UserModel).where(UserModel.user_id == transaction_user.user_id))
            customer_user_instance = customer_user.scalars().first()
            user_dump = jsonable_encoder(customer_user_instance)
            if not customer_user_instance:
                return JSONResponse({"message":"No se encontro la transaccion"}, status_code=404)
            if data['payment_status'] == "confirmed":
                update_balance = update(UserModel).where(UserModel.user_id == transaction_user.user_id).value(balance_real=f"{float(user_dump['balance_real']) + float(data['price_amount'])}")

            await db.execute(update_balance)
            await db.commit()
            await db.refresh(customer_user_instance)
            user_dump = jsonable_encoder(customer_user_instance)

            return JSONResponse({"message":"Transaccion actualizada", "payment":jsonable_encoder(data), "balance_real":user_dump['balance_real'],"balance_demo":user_dump['balance_demo']}, status_code=200)
        except Exception as error:
            print(error)
            db.rollback()
            return JSONResponse({"message":"No se pudo completar la transaccion"}, status_code=402)


@router.get('/{payment_id}/reject/')
async def reject_transaction(payment_id: str, db: AsyncSession = Depends(get_async_db)):
    try:
        # Search the transaction by the id
        stmt_payment = select(PaymentModel).where(PaymentModel.payment_id == payment_id)
        result_payment = await db.execute(stmt_payment)
        data_payment = result_payment.scalars().all()

        # Check if the transaction exists
        if not data_payment:  # Handles the case when the list is empty
            return JSONResponse({"message": "Transacción no encontrada"}, status_code=404)

        # Get the first instance
        instance_payment = data_payment[0]

        # Updated model
        db.refresh(instance_payment)
        return JSONResponse({"message": "Transacción actualizada", "payment": jsonable_encoder(instance_payment)}, status_code=200)
    except Exception as error:
        print(error)
        await db.rollback()  # Rollback needs to be awaited in async
        return JSONResponse({"message": "No se pudo completar la transacción"}, status_code=500)


@router.get('/{user_id}/list/')
async def list_payment(user_id: str, offset: int = Query(0, ge=0), limit: int = Query(10, gt=0),  db: AsyncSession = Depends(get_async_db)):
       
        try:  
            # Query for payments with pagination
            user_id_uuid = uuid.UUID(user_id)
            stmt = select(PaymentModel).where(PaymentModel.user_id == user_id_uuid)
            validation = await db.execute(stmt)
            total_payments = validation.scalars().all()
            stmt_payment = (
                select(PaymentModel)
                .where(PaymentModel.user_id == user_id_uuid)
                .order_by(PaymentModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await db.execute(stmt_payment)
            payment_list = result.scalars().all()
            return JSONResponse({"payments":jsonable_encoder(payment_list), "total_payments": jsonable_encoder(len(total_payments))}, status_code=200)
        except Exception as error:
            print(error)
            db.rollback()
            return JSONResponse({"message":"No se pudo completar la transaccion"}, status_code=402)
  