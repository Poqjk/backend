from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_async_db
from models.operation import Operation as OperationModel
from sqlalchemy.future import select
from sqlalchemy import func, cast, Numeric
from middlewares.verify_token_admin import VerifyTokenAdmin
from models.asset import Asset as AssetModel


router = APIRouter(route_class=VerifyTokenAdmin)


@router.get('/assets-op')
async def get_assets_operations(db: AsyncSession = Depends(get_async_db)):
    # Modifica la consulta para contar operaciones por cada asset
    query = (
        select(  
            AssetModel.name.label("asset_name"),
            func.count(OperationModel.operation_id).label("operations_count")
        )
        .join(OperationModel, OperationModel.asset_id == AssetModel.id)
        .group_by(AssetModel.id, AssetModel.name)
    )
    
    # Ejecuta la consulta
    result = await db.execute(query)
    assets_operations = result.all()
    
    # Devuelve los resultados en un formato más claro
    return {
        "assets_operations": [
            {
                
                "asset_name": asset_name,
                "operations_count": operations_count
            }
            for asset_name, operations_count in assets_operations
        ]
    }
    

@router.get('/assets-op-between-dates')
async def get_assets_operations(
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    db: AsyncSession = Depends(get_async_db)):
    # Modifica la consulta para contar operaciones por cada asset entre fechas
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    query = (
        select(
            AssetModel.name.label("asset_name"),
            func.count(OperationModel.operation_id).label("operations_count")
        )
        .join(OperationModel, OperationModel.asset_id == AssetModel.id)
        .where(OperationModel.created_at.between(start, end))
        .group_by(AssetModel.id, AssetModel.name)
    )
    
    # Ejecuta la consulta
    result = await db.execute(query)
    assets_operations = result.all()
    
    # Devuelve los resultados en un formato más claro
    return {
        "assets_operations": [
            {
                "asset_name": asset_name,
                "operations_count": operations_count
            }
            for asset_name, operations_count in assets_operations
        ]
    }


@router.get('/total-wins')
async def get_total_wins(db: AsyncSession = Depends(get_async_db)):
    query = select(func.sum(cast(OperationModel.income, Numeric))).where(OperationModel.winner == True)
    result = await db.execute(query)
    total_wins = result.scalar()
    return {"total_wins": total_wins or 0}


@router.get('/income-between-dates')
async def get_income_between_dates(
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = select(func.sum(cast(OperationModel.amount, Numeric))).where(
        OperationModel.winner == False,
       
    )
    result = await db.execute(query)
    total_income = result.scalar()
    return {"total_income": total_income or 0}


@router.get('/operation-count-between-dates')
async def get_operation_count_between_dates(
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = select(func.count(OperationModel.operation_id)).where(
        OperationModel.created_at.between(start, end)
    )
    result = await db.execute(query)
    total_operations = result.scalar()
    return {"total_operations": total_operations or 0}


@router.get('/operations-by-type')
async def get_operations_by_type(
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DDTHH:MM:SS)"),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    demo_query = select(func.count(OperationModel.operation_id)).where(
        OperationModel.operation_mode == 0,
       
    )
    real_query = select(func.count(OperationModel.operation_id)).where(
        OperationModel.operation_mode == 1,  # Real
      
    )

    demo_result = await db.execute(demo_query)
    real_result = await db.execute(real_query)

    demo_count = demo_result.scalar() or 0
    real_count = real_result.scalar() or 0

    return {"demo_count": demo_count, "real_count": real_count}
