"""Email settings and transactional outbox."""
from alembic import op
from models import EmailSetting, EmailOutbox
revision = '7e1a9b2c3d4e'
down_revision = '2f9da76eb2e2'
branch_labels = None
depends_on = None

def upgrade():
    EmailSetting.__table__.create(op.get_bind(), checkfirst=True)
    EmailOutbox.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    EmailOutbox.__table__.drop(op.get_bind())
    EmailSetting.__table__.drop(op.get_bind())
