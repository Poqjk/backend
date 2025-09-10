from fastapi import APIRouter, Query, Depends,HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy.future import select
from models.user import User as UserModel
from models.withdraw import Withdraw as WithdrawModel
from config.database import AsyncSession, get_async_db
from middlewares.verify_token_routes import VerifyTokenRoute 
import uuid
from sqlalchemy.orm import selectinload
 

router = APIRouter(route_class=VerifyTokenRoute)

class Withdraw(BaseModel):
    user_id:str
    admin_id:str | None = Field(default="")
    amount:str   
    reason:str   | None = Field(default="")
    type:str
    network:str
    address:str 
    

@router.post("/create")
async def create_withdraw(withdraw: Withdraw, db: AsyncSession = Depends(get_async_db)):
    try:
        # Buscar el usuario en la base de datos
        stmt = select(UserModel).where(UserModel.user_id == withdraw.user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return JSONResponse({"message": "Usuario no encontrado"}, status_code=404)

        # Verificar si el saldo es suficiente
        if float(user.balance_real) < float(withdraw.amount):
            return JSONResponse({"message": "Saldo insuficiente"}, status_code=404)

        # Preparar los datos para guardar el retiro
        withdraw_dump = withdraw.model_dump()
        withdraw_dump['admin_id'] = None
        withdraw_dump['user_id'] = uuid.UUID(withdraw_dump['user_id'])  # Convertir a UUID

        # Crear y guardar el modelo de retiro
        withdraw_save = WithdrawModel(**withdraw_dump)
        db.add(withdraw_save)
        await db.commit()

        return JSONResponse({"message": "Solicitud de retiro creada"}, status_code=200)

    except Exception as error:
        print(f"Error al crear el retiro: {error}")
        await db.rollback()
        return JSONResponse({"message": "Error al crear solicitud de retiro"}, status_code=500)

    
class UpdateWithdrawRequest(BaseModel):
    withdraw_id: str
    status: str | None = Field(default="")
    admin_id: str
    reason:str | None = Field(default="")

@router.post("/update")
async def update_withdraw(
    request: UpdateWithdrawRequest,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Verificar si el admin existe y tiene rol de administrador
        admin_query = select(UserModel).where(UserModel.user_id == request.admin_id)
        admin_result = await db.execute(admin_query)
        admin = admin_result.scalars().first()

        if not admin or admin.role != "admin":
            return JSONResponse({"message": "Este id no pertenece a un usuario admin"}, status_code=404)

        # Verificar si el retiro existe
        withdraw_query = select(WithdrawModel).where(WithdrawModel.id == request.withdraw_id)
        withdraw_result = await db.execute(withdraw_query)
        withdraw = withdraw_result.scalars().first()

        if not withdraw:
            return JSONResponse({"message": "Retiro no existente"}, status_code=404)

        # Actualizar el retiro
        withdraw.status = request.status
        withdraw.reason = request.reason
        withdraw.admin_id = request.admin_id

        await db.commit()
        await db.refresh(withdraw)

        return JSONResponse(
            {
                "message": "Cambio exitoso",
                "user_data": jsonable_encoder(withdraw),
            },
            status_code=200,
        )

    except Exception as e:
        print(f"Error al actualizar el retiro: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Error al actualizar el retiro. Inténtalo más tarde."
        )
    

@router.get('/{user_id}/list/')
async def list_withdraw(user_id: str, offset: int = Query(0, ge=0), limit: int = Query(10, gt=0), db: AsyncSession = Depends(get_async_db)):
      
        try:
            # Query for withdraw with pagination
            user_id_uuid = uuid.UUID(user_id)
            stmt = select(WithdrawModel).where(WithdrawModel.user_id == user_id_uuid).order_by(WithdrawModel.created_at.desc())
            validation =  await db.execute(stmt)
            total_withdraws = validation.scalars().all()
            stmt_withdraw = (
                select(WithdrawModel)
                .where(WithdrawModel.user_id == user_id_uuid)
                .order_by(WithdrawModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await db.execute(stmt_withdraw)
            withdraw_list = result.scalars().all()
            return JSONResponse({"withdraw":jsonable_encoder(withdraw_list), "Total de retiros":jsonable_encoder(len(total_withdraws))}, status_code=200)
        except Exception as error:
            print(error)
            db.rollback()
            return JSONResponse({"message":"No se pudo completar la transaccion"}, status_code=402)
   




@router.get("/list")
async def withdraws_list(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, gt=0, le=100, description="Limit for pagination (max 100)"),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        # Fetch total number of withdrawals for pagination metadata
        total_withdraws_stmt = select(WithdrawModel)
        total_withdraws_result = await db.execute(total_withdraws_stmt)
        total_withdraws = total_withdraws_result.scalars().fetchall()

        # Fetch paginated withdrawals with relationships
        paginated_withdraws_stmt = (
            select(WithdrawModel)
            .options(selectinload(WithdrawModel.user))  # Load user relationship if needed
            .order_by(WithdrawModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        paginated_withdraws_result = await db.execute(paginated_withdraws_stmt)
        paginated_withdraws = paginated_withdraws_result.scalars().fetchall()

        # Remove sensitive data
        for withdraw in paginated_withdraws:
            if withdraw.user:
                withdraw.user.password = None  # Use None instead of empty string

        return JSONResponse(
            {
                "Retiros": jsonable_encoder(paginated_withdraws),
                "total_withdraws": len(total_withdraws),
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": len(total_withdraws),
                },
            },
            status_code=200,
        )

    except Exception as e:
        print(f"Error in /list endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching withdrawals. Please try again later.",
        )