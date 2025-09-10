from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from models.asset import Asset as AssetModel
from config.database import Session
from sqlalchemy.future import select
from sqlalchemy import desc, func, delete
import uuid
from middlewares.verify_token_routes import VerifyTokenRoute 


router = APIRouter(route_class=VerifyTokenRoute)

class asset(BaseModel):
    active_id : str 
    name : str
    type : str
    custom_profit : str
    available_broker:bool
    in_custom:bool

@router.post('/create')
async def register_asset(asset: asset):
        db = Session()
        try:
            new_asset = asset.model_dump()
            new_asset_register = AssetModel(**new_asset)
            db.add(new_asset_register)
            db.commit()
            db.refresh(new_asset_register)
            return JSONResponse({"message":"Asset creado", "Asset data": jsonable_encoder(new_asset_register)}, status_code=200)
        except Exception as e:
            db.rollback()
            return JSONResponse({"message":"error"}, status_code=402)
    

@router.get('/read')
async def read_asset( asset_id : str = Query()):
        db = Session()
        try:
            stmt = select(AssetModel).filter(AssetModel.id == asset_id)
            
            result =  db.execute(stmt)
            asset = result.scalars().all()
            return JSONResponse({"asset": jsonable_encoder(asset)},status_code=200)
        except Exception as e:
            return JSONResponse({"message":"Error"}, status_code=404)
    

@router.get('/read/list')
async def assets_list( offset: int = Query(0, ge=0), limit: int = Query(10, gt=0)):
  
        db = Session()
        assetslist = []
        try:
            stmt = select(AssetModel)
            validation =  db.execute(stmt)
            total_assets = validation.scalars().all()
            
            stmt =(
                select(AssetModel)
                .offset(offset)
                .limit(limit)
                .order_by(desc(AssetModel.created_at))
            ) 
            result =  db.execute(stmt)
            assetsl = result.scalars().all()
            print(f"assets endpoint f{jsonable_encoder(assetsl)}")
            
            for asset in assetsl:
                assetslist.append(jsonable_encoder(asset))
            return JSONResponse({"assets": jsonable_encoder(assetslist), "total_assets": jsonable_encoder(len(total_assets))},status_code=200)
        
        except Exception as e:
            return JSONResponse({"message":"Error"}, status_code=404)

@router.put('/update/{id}')
async def update_asset(id:str, asset : asset):
  
        db = Session()
        try:
            stmt = select(AssetModel).filter(AssetModel.id == uuid.UUID(id))
            validation =  db.execute(stmt)
            usersl = validation.scalars().all()
            result =  db.query(AssetModel).filter(AssetModel.id == uuid.UUID(id))[0]
            if len(usersl) != 0:
                if result:
                    asset_data = jsonable_encoder(result)
                    result.active_id = asset.active_id
                    result.name = asset.name
                    result.type = asset.type
                    result.custom_profit = asset.custom_profit
                    result.available_broker = asset.available_broker
                    result.updated_at = func.now()
                    db.commit()
                    db.refresh(result)
                    new_asset_data = jsonable_encoder(result)
                    return JSONResponse({"message":"asset data", "Asset data after":jsonable_encoder(asset_data),"Asset data before":jsonable_encoder(new_asset_data)},status_code=200)
                else:
                    return JSONResponse({"message":"Este id no tiene un asset asignado"}, status_code=404)
            else:
                return JSONResponse({"message":"Este id no tiene un asset asignado"}, status_code=404)
        except Exception as e:
            print(e)
            db.rollback()
            return JSONResponse({"message":"Asset no encontrado no encontrado"}, status_code=404)

@router.delete('/delete')
async def delete_asset( asset_id : str = Query()):
  
        db = Session()
        try:
            stmt = delete(AssetModel).filter(AssetModel.id == asset_id)
            result =  db.execute(stmt)
            db.commit()
            return JSONResponse({"message": "Asset eliminado correctamente"},status_code=200)

        except Exception as e:
            db.rollback()
            return JSONResponse({"message":"Error"}, status_code=404) 
    

 