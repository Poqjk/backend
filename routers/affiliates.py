from fastapi import APIRouter, Depends, HTTPException
from config.database import AsyncSession, get_async_db
from models import User as UserModel
from sqlalchemy.future import select
from models.affiliates import Affiliates
from models.affiliateClicks import AffiliateClicks
from uuid import UUID
import random
import string
from models.affiliateLinks import LinkTypeEnum
from models.affiliateLinks import LinkProgram
from models.affiliateLinks import AffiliateLinks
from pydantic import BaseModel
from models.affiliateReferrals import AffiliateReferrals
from sqlalchemy import func

class AffiliateLinkCreate(BaseModel):
    link_type: LinkTypeEnum
    affiliate_program: LinkProgram
    comment: str

def generate_affiliate_code(length=8):
    # Caracteres permitidos: letras mayúsculas y números
    characters = string.ascii_uppercase + string.digits
    # Generar un código aleatorio
    return ''.join(random.choice(characters) for _ in range(length))

router = APIRouter()

@router.get("/join/{user_id}")
async def joinAffiliateProgram(user_id: str, db: AsyncSession = Depends(get_async_db)):
    try:
        # Verificar si el user_id es un UUID válido
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        # Buscar el usuario en la base de datos
        query = await db.execute(select(UserModel).where(UserModel.user_id == user_uuid))
        userFound = query.scalars().first()

        if not userFound:
            raise HTTPException(status_code=404, detail="We couldn't find a user with the given ID")

        # Verificar si el usuario ya es afiliado
        if userFound.is_affiliate:
            raise HTTPException(status_code=400, detail="User is already an affiliate")

        # Actualizar el estado del usuario a afiliado
        userFound.is_affiliate = True

        # Crear un registro en la tabla affiliates
        new_affiliate = Affiliates(
            user_id=user_uuid,
            
        )
        db.add(new_affiliate)

        # Guardar los cambios en la base de datos
        await db.commit()

        # Devolver los datos mínimos del usuario y el affiliate code
        minimal_data = {
            "user_id": userFound.user_id,
            "firstname": userFound.firstname,
            "lastname": userFound.lastname,
            "email": userFound.email,
            "role": userFound.role,
            "is_affiliate": userFound.is_affiliate,
            "affiliate_id":new_affiliate.id
        }

        return {"message": "User successfully joined the affiliate program", "user_data": minimal_data}

    except Exception as e:
        # Revertir la transacción en caso de error
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"There was an error trying to make this user an affiliate: {str(e)}")
    
    
@router.post("/{affiliate_id}/links/")
async def create_affiliate_link(
    affiliate_id: str,
    payload: AffiliateLinkCreate,  # Los parámetros vienen del body
    db: AsyncSession = Depends(get_async_db)
):
    # Validación del formato UUID
    try:
        UUID(affiliate_id)
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid user ID format")
     
    # Verificar que el afiliado exista
    try:
        affiliate_result = await db.execute(select(Affiliates).where(Affiliates.id == affiliate_id))
        affiliate = affiliate_result.scalars().first()
        if not affiliate:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        # Generar un código único para el enlace
        link_code = generate_affiliate_code()

        # Crear el enlace utilizando los datos del body
        new_link = AffiliateLinks(
            affiliate_id=affiliate_id,
            link_type=payload.link_type,
            affiliate_program=payload.affiliate_program,
            comment=payload.comment,
            link_code=link_code
        )
        db.add(new_link)
        await db.commit()
        return {"message": "Link created successfully", "link_code": link_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating link: {str(e)}")
    

    
@router.get("/{affiliate_id}/links/")
async def get_affiliate_links(
    affiliate_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        affiliate_uuid = UUID(affiliate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid affiliate ID format")

    # Check if the affiliate exists
    affiliate = await db.execute(select(Affiliates).where(Affiliates.id == affiliate_uuid))
    affiliate = affiliate.scalars().first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    # Get clicks grouped by link
    click_count_by_link = await db.execute(
        select(
            AffiliateLinks.link_code,
            AffiliateLinks.affiliate_program,
            AffiliateLinks.comment,
            AffiliateLinks.id,
            func.count(AffiliateClicks.id).label("click_count")
        )
        .outerjoin(AffiliateClicks, AffiliateClicks.link_id == AffiliateLinks.id)
        .where(AffiliateLinks.affiliate_id == affiliate_uuid)
        .group_by(AffiliateLinks.link_code, AffiliateLinks.affiliate_program, AffiliateLinks.comment, AffiliateLinks.id)
    )

    click_count_by_link = click_count_by_link.all()

    # Format the response
    result = [
        {
            "link_code": row.link_code,
            "affiliate_program": row.affiliate_program,
            "comment": row.comment,
            "id": row.id,
            "click_count": row.click_count
        }
        for row in click_count_by_link
    ]

    return {"affiliate_id": affiliate_id, "click_count_by_link": result}

 
@router.post("/links/{link_code}/click/")
async def register_affiliate_click(
    link_code: str,
    ip_address: str = None,
    user_agent: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Buscar el enlace por su código
        query = await db.execute(select(AffiliateLinks).where(AffiliateLinks.link_code == link_code))
        affiliate_link = query.scalars().first()

        if not affiliate_link:
            raise HTTPException(status_code=404, detail="Affiliate link not found")

        # Registrar el click
        new_click = AffiliateClicks(
            affiliate_id=affiliate_link.affiliate_id,
            link_id=affiliate_link.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(new_click)
        await db.commit()

        return {"message": "Click registered successfully", "link_code": link_code}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error registering click: {str(e)}")
    
@router.get("/{affiliate_id}/referral-count/")
async def get_affiliate_referral_count(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Contar las referencias de este afiliado
        referral_count = await db.execute(
            select(func.count(AffiliateReferrals.id))
            .where(AffiliateReferrals.affiliate_id == affiliate_id)
        )
        referral_count = referral_count.scalar()

        return {"affiliate_id": affiliate_id, "referral_count": referral_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting referral count: {str(e)}")


    
@router.get("/{affiliate_id}/click-count/")
async def get_affiliate_click_count(
    affiliate_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # Verificar que el afiliado exista
        affiliate = await db.execute(select(Affiliates).where(Affiliates.id == affiliate_id))
        affiliate = affiliate.scalars().first()
        if not affiliate:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        # Contar los clicks asociados a este afiliado
        click_count = await db.execute(
            select(func.count(AffiliateClicks.id))
            .join(AffiliateLinks, AffiliateLinks.id == AffiliateClicks.link_id)
            .where(AffiliateLinks.affiliate_id == affiliate_id)
        )
        click_count = click_count.scalar()

        return {"affiliate_id": affiliate_id, "click_count": click_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting click count: {str(e)}")