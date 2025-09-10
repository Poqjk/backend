"""affiliate id in payments table

Revision ID: 8085138e5da3
Revises: ae86671b2e80
Create Date: 2025-02-15 16:51:02.370974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8085138e5da3'
down_revision: Union[str, None] = 'ae86671b2e80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar la columna affiliate_id (si es necesario)
    op.add_column('payments', sa.Column('affiliate_id', sa.String(), nullable=True))
    
    # Ejecutar la sentencia ALTER TABLE con USING
    op.execute(
        "ALTER TABLE payments ALTER COLUMN status TYPE paymentstatusenum USING status::text::paymentstatusenum"
    )



def downgrade() -> None:
    # Volvemos a cambiar el tipo de la columna 'status' de paymentstatusenum a VARCHAR()
    op.alter_column(
        'payments',
        'status',
        existing_type=sa.Enum(
            'waiting', 'confirming', 'confirmed', 'sending', 'partially_paid',
            'finished', 'failed', 'refunded', 'expired',
            name='paymentstatusenum'
        ),
        type_=sa.VARCHAR(),
        nullable=True
    )
    # Eliminamos la columna affiliate_id
    op.drop_column('payments', 'affiliate_id')
