"""product images feature 65

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'h8c9d0e1f2a3'
down_revision: Union[str, None] = 'g7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('business_id', sa.String(36), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('variant_id', sa.String(36), sa.ForeignKey('product_variants.id'), nullable=True),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_product_images_business_product', 'product_images', ['business_id', 'product_id'])
    op.create_index('ix_product_images_product_active', 'product_images', ['product_id', 'status'])
    op.execute("""
        CREATE UNIQUE INDEX uq_product_image_active_primary
        ON product_images (business_id, product_id, COALESCE(variant_id, ''), is_primary)
        WHERE is_primary = true AND status = 'ACTIVE'
    """)


def downgrade() -> None:
    op.drop_index("uq_product_image_active_primary", "product_images")
    op.drop_index('ix_product_images_product_active', 'product_images')
    op.drop_index('ix_product_images_business_product', 'product_images')
    op.drop_table('product_images')
