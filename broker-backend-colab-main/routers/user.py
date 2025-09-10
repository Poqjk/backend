from datetime import date
from fastapi import APIRouter, Query, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, EmailStr, Field
from models.operation import Operation
from models.user import User as UserModel
from config.database import AsyncSession, get_async_db
from sqlalchemy.future import select
from sqlalchemy import desc, func
from utils import get_hashed_password, write_token, validate_token_change_password,write_token_change_password
from models.user import User as UserModel
from models.payment import Payment as PaymentModel
from middlewares.verify_token_routes import VerifyTokenRoute 
from uuid import UUID
from sqlalchemy.orm import joinedload



router = APIRouter(route_class=VerifyTokenRoute)

class User(BaseModel):
    email:EmailStr | None = Field(default=None)
    password:str


class RegisterCredentials(User):
    firstname: str | None = Field(default=None)
    lastname: str | None = Field(default=None)
    birthday: date | None = Field(default=None)
    country: str | None = Field(default=None)
    role: str | None = Field(default="User")
    phone_number: str | None = Field(default=None)
    accept_terms: bool | None = Field(default=None)
    newsletter: bool | None = Field(default=None)
    

class UserData(BaseModel):
    email: EmailStr | None = Field(default=None)
    password: str
    balance_real: str | None = Field(default="0")
    balance_demo: str | None = Field(default="10000.00")
    account_mode: int | None = Field(default=0)
    role: str | None = Field(default="user")
    firstname: str | None = Field(default=None)
    lastname: str | None = Field(default=None)
    birthday: date | None = Field(default=None)
    country: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)



        
@router.post('/create')
async def register_user_admin(user: UserData,  db: AsyncSession = Depends(get_async_db)):
    
      
        try:
            #If pass user_id (navigator id demo) return the user registered
            user_id_uuid = ""
            stmt = select(UserModel).where(UserModel.email == user.email)
            result = await db.execute(stmt)
            user_data = result.scalars().all()

            if user_data:
                return JSONResponse({"message":"Ya este correo se encuentra registrado"},status_code=401)
            else: 
                new_user = user.model_dump()
                encrypted_password = get_hashed_password(user.password)
                new_user['password'] = encrypted_password
                new_user['role'] = user.role  
                new_user['balance_demo'] = "10000.00"
                new_user['balance_real'] = "0"
                new_user_register = UserModel(**new_user)
                db.add(new_user_register)
                db.commit()
                db.refresh(new_user_register)
                user_show = jsonable_encoder(new_user_register)
                user_show.pop('password')
                return JSONResponse({"message":"User Created", "User data": jsonable_encoder(user_show)}, status_code=200)
        except Exception as e:
            await db.rollback()
            return JSONResponse({"message":"error"}, status_code=402)



@router.get("/trades/list/{user_id}")
async def list_trades(
    user_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        user_id_uuid = UUID(user_id)  # Validar el formato UUID

        # Consultar el total de trades verificados de manera asíncrona
        stmt_total_trades = (
            select(func.count())
            .select_from(Operation)
            .where(Operation.user_id == user_id_uuid, Operation.is_verified == True)
        )
        total_trades = (await db.execute(stmt_total_trades)).scalar()

        # Consultar trades verificados con paginación
        stmt_trades = (
            select(Operation)
            .options(joinedload(Operation.asset))  # Cargar relaciones de manera ansiosa
            .where(Operation.user_id == user_id_uuid, Operation.is_verified == True)
            .order_by(desc(Operation.created_at))
            .offset(offset)
            .limit(limit)
        )
        trades_list = (await db.execute(stmt_trades)).scalars().all()

        # Consultar el total de trades pendientes de manera asíncrona
        stmt_total_pending = (
            select(func.count())
            .select_from(Operation)
            .where(Operation.user_id == user_id_uuid, Operation.is_verified == False)
        )
        total_pending = (await db.execute(stmt_total_pending)).scalar()

        # Consultar trades pendientes
        stmt_pendings = (
            select(Operation)
            .options(joinedload(Operation.asset))
            .where(Operation.user_id == user_id_uuid, Operation.is_verified == False)
        )
        trades_pendings = (await db.execute(stmt_pendings)).scalars().all()

        # Preparar la respuesta
        trades_list_user = [
            {
                **jsonable_encoder(operation),
                "asset": jsonable_encoder(operation.asset),
            }
            for operation in trades_list
        ]

        trades_list_pending = [
            {
                **jsonable_encoder(operation),
                "asset": jsonable_encoder(operation.asset),
            }
            for operation in trades_pendings
        ]

        return JSONResponse(
            {
                "trades_list": trades_list_user,
                "total_trades": total_trades,
                "trades_pendings": trades_list_pending,
                "total_trades_pending": total_pending,
            },
            status_code=200,
        )

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error")

#Obtain list user data 
@router.get("/list")
async def users_list(offset: int = Query(0, ge=0), limit: int = Query(10, gt=0), db: AsyncSession = Depends(get_async_db)):
    
    userlist = []
    try:
        stmt = select(UserModel)
        validation = await db.execute(stmt)
        total_users = validation.scalars().all()
        stmt =(
            select(UserModel)
            .offset(offset)
            .limit(limit)
            .order_by(desc(UserModel.created_at))
                )  
            
        result =  await db.execute(stmt)
        usersl = result.scalars().all()
        
        for user in usersl:
            stmtd = select(PaymentModel).filter(PaymentModel.user_id == user.user_id, PaymentModel.status == "completed")
            resultd = await db.execute(stmtd)
            depositsl = resultd.scalars().all()
            if len(depositsl) != 0:
                deposits = True
            else: 
                deposits = False
            listed_user = jsonable_encoder(user)
            listed_user.pop('password')
            listed_user['deposits'] = deposits
            userlist.append(listed_user)
        return JSONResponse({"usuarios": jsonable_encoder(userlist), "total_users" : jsonable_encoder(len(total_users))},status_code=200)
    
    except Exception as e:
        return JSONResponse({"message":"Error"}, status_code=404)

@router.get("/data/admin")
async def user_data_admin(user_id : str = Query(), db: AsyncSession = Depends(get_async_db)):
   
       
        userlist = {}
        
        try:
            stmt =(select(UserModel).filter(UserModel.user_id == user_id)) 
            result = await db.execute(stmt)
            usersl = result.scalars().all()
           
            listed_user = jsonable_encoder(usersl[0])
            listed_user.pop('password')
            listed_user.pop('refreshToken')

            
            userlist = listed_user
            
            return JSONResponse({"usuario": jsonable_encoder(userlist)},status_code=200) 
        except Exception as e:
            return JSONResponse({"message":f"Error {e}"}, status_code=404)

#Update user data 
@router.put("/update/admin")
async def update_user_admin(
    user_id : str = Query(), 
  
    new_email : EmailStr = Body(), 
    new_password : str = Body(),  
    check : bool = Body(), 
    new_balance_real : str = Body(),
    new_role : str = Body(),
    firstname : str = Body(), 
    lastname : str = Body(), 
    birthday : date = Body(),
    country : str = Body(),
    phone_number: str = Body(), 
    newsletter : bool = Body(),
     db: AsyncSession = Depends(get_async_db)
    ):
  
        
        stmt = select(UserModel).filter(UserModel.email == new_email, user_id != UserModel.user_id)
        validation = await db.execute(stmt)
        usersl = validation.scalars().all()
        if len(usersl) == 0:
            stmt =(select(Operation).filter(Operation.user_id == user_id, Operation.operation_mode == 1, Operation.is_verified == False))
            result = await db.execute(stmt)
            operationsl = result.scalars().all()
            if len(operationsl) == 0:  
                try:
                    result = await db.query(UserModel).filter(UserModel.user_id == user_id)[0]
                    if result:
                        user_data = jsonable_encoder(result)
                        user_data.pop('password')
                        result.email = new_email
                        result.balance_real = new_balance_real
                        result.role = new_role
                        result.firstname = firstname
                        result.lastname = lastname
                        result.birthday = birthday
                        result.country = country
                        result.phone_number = phone_number
                        result.newsletter = newsletter
                        result.updated_at = func.now()
                        if check == True:
                            result.password = get_hashed_password(new_password)
                        await db.commit()
                        await db.refresh(result)
                        new_user_data = jsonable_encoder(result)
                        new_user_data.pop('password')
                        return JSONResponse({"message":"user data", "user_data_before":jsonable_encoder(user_data),"user_data_after":jsonable_encoder(new_user_data)},status_code=200)
                    else:
                        return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)
                except Exception as e:
                    print(e)
                    return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)
            else:
                return JSONResponse({"message":"Este usuario tiene operaciones activas"}, status_code=404)
        else:
            return JSONResponse({"message":"Este email pertenece a otro usuario"}, status_code=404)
        
#Update user data 
@router.put("/update/user")
async def update_user(user_id : str = Query(),  new_email : EmailStr = Body(), new_password : str = Body(), repeat_password : str = Body(), check : bool = Body(), firstname : str = Body(), lastname : str = Body(), phone_number: str = Body(), newsletter : bool = Body(),  db: AsyncSession = Depends(get_async_db)):
    
        if new_password == repeat_password:
           
            try:
                stmt = select(UserModel).filter(UserModel.email == new_email, user_id != UserModel.user_id)
                validation =  await db.execute(stmt)
                usersl = validation.scalars().all()
                result =  await db.query(UserModel).filter(user_id == UserModel.user_id)[0]
                if len(usersl) == 0:
                    if result:
                        user_data = jsonable_encoder(result)
                        user_data.pop('password')
                        result.email = new_email
                        result.updated_at = func.now()
                        if check == True:
                            result.password = get_hashed_password(new_password)
                        result.firstname = firstname
                        result.lastname = lastname
                        result.newsletter = newsletter
                        result.phone_number = phone_number
                        await db.commit()
                        await db.refresh(result)
                        new_user_data = jsonable_encoder(result)
                        new_user_data.pop('password')
                        return JSONResponse({"message":"user data", "user_data_before":jsonable_encoder(user_data),"user_data_after":jsonable_encoder(new_user_data), "token":write_token(jsonable_encoder(user_data))},status_code=200)
                    else:
                        return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)
                else:
                    return JSONResponse({"message":"Este email pertenece a otro usuario"}, status_code=404)
            except Exception as e:
                print(e)
                return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)
        else: 
            return JSONResponse({"message":"La nueva contraseña no coincide con la repetida"}, status_code=404)

#Update user block
@router.put("/update/user/block")
async def update_user_block( user_block: bool = Body(), token : str = Body(),user_id : str = Query(), db: AsyncSession = Depends(get_async_db)):
        try:
            result = await db.query(UserModel).filter(UserModel.user_id == user_id)[0]
            if result:
                result.block = user_block
                await db.commit()
                await db.refresh(result)
                new_user_data = jsonable_encoder(result)
                new_user_data.pop('password')
                return JSONResponse({"message":"cambio exitoso","user_data":jsonable_encoder(new_user_data)}, status_code=200)
            else:
                return JSONResponse({"message":"id no existe"}, status_code=404)
        except Exception as e:
            print(e)
            return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)

#Update user role
@router.put("/update/user/role")
async def update_user_role( user_role: str = Body(), token : str = Body(),user_id : str = Query(), db: AsyncSession = Depends(get_async_db)):
        try:
            result = await db.query(UserModel).filter(UserModel.user_id == user_id)[0]
            if result:
                result.role = user_role
                await db.commit()
                await db.refresh(result)
                new_user_data = jsonable_encoder(result)
                new_user_data.pop('password')
                return JSONResponse({"message":"cambio exitoso","user_data":jsonable_encoder(new_user_data)}, status_code=200)
            else:
                return JSONResponse({"message":"id no existe"}, status_code=404)
        except Exception as e:
            print(e)
            return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)

@router.put("/recovery/password")
async def user_recovery_password(user_id : str = Query(), new_password : str = Body(), new_password_repeat : str = Body(), db: AsyncSession = Depends(get_async_db)):
    
    
            if new_password == new_password_repeat:
                stmt = select(UserModel).filter(user_id == UserModel.user_id)
                validation = await db.execute(stmt)
                confirm = validation.scalars().all()
                result = await db.query(UserModel).filter(user_id == UserModel.user_id)[0]
                if len(confirm) != 0 :
                    user_data = jsonable_encoder(result)
                    result.password = get_hashed_password(new_password)
                    db.commit()
                    db.refresh(result)
                    new_user_data = jsonable_encoder(result)
                    new_user_data.pop('password')
                    return JSONResponse({"message":"Cambio de contraseña exitoso", "prueba": jsonable_encoder(user_data), "prueba despues": jsonable_encoder(new_user_data)}, status_code=200)
                else:
                    return JSONResponse({"message":"Usuario no encontrado"}, status_code=404)
            else:
                return JSONResponse({"message":"La contraseña nueva no corresponde con la contraseña nueva repetida"}, status_code=404)
   
    
@router.post("/id/token")
async def user_id_token(user_email : str = Body(), db: AsyncSession = Depends(get_async_db)):
    
    try:
        stmt = select(UserModel).filter(user_email == UserModel.email)
        validation = await db.execute(stmt)
        confirm = validation.scalars().all()
        if len(confirm) != 0:
            result = await db.query(UserModel).filter(user_email == UserModel.email)[0]
            user_data = jsonable_encoder(result)
            user_id = user_data['user_id']
            return JSONResponse({"ID": jsonable_encoder(user_id),"token": write_token_change_password(jsonable_encoder(user_data))},status_code=200)
        else:
            return JSONResponse({"message":"email incorrecto"}, status_code=404)
        
    except Exception as e:
        return JSONResponse({"message": "Error"}, status_code=404)
    
@router.post("/verify/update/password/token")
async def verify_token_password(auth : str = Body()):
    if validate_token_change_password(auth,output=True) == 1:
        return JSONResponse({"message": "El token no es valido"}, status_code=404)
    if validate_token_change_password(auth,output=True) == 2:
        return JSONResponse({"message": "El token ha expirado"}, status_code=404)
    if validate_token_change_password(auth,output=True) == 3:
        return JSONResponse({"message": "Usuario Suspendido"}, status_code=404)
    else:
        token_data = jsonable_encoder(validate_token_change_password(auth,output=True))
        token_data.pop('password')
        return JSONResponse({"message": "El token es valido","Token data":jsonable_encoder(token_data)}, status_code=404)
    

    
@router.post("/verify/age")
async def verify_age(birth : date = Body()):
    return JSONResponse({"Edad":jsonable_encoder(calculate_age(birth))})