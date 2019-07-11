"""set all email as lowercase

Revision ID: d4ed9c6991ae
Revises: 32e629b17e2e
Create Date: 2019-07-04 10:59:59.900831

"""
# revision identifiers, used by Alembic.
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Unicode
from sqlalchemy import func

revision = "d4ed9c6991ae"
down_revision = "32e629b17e2e"

users = sa.Table(
    "users",
    sa.MetaData(),
    sa.Column("user_id", sa.Integer, primary_key=True),
    sa.Column("email", Unicode(255), unique=True, nullable=False),
)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    connection = op.get_bind()
    connection.execute(users.update(values={users.c.email: func.lower(users.c.email)}))


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
