"""
Central import of all SQLAlchemy models.

Alembic and Base.metadata need every table class loaded once so migrations
and create_all() see the full schema. Do not define models here — only import them.
"""

from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.auth.models import User  # noqa: F401
from app.modules.files.models import FileRecord  # noqa: F401
from app.modules.invitations.models import Invitation  # noqa: F401
from app.modules.memberships.models import Membership  # noqa: F401
from app.modules.organizations.models import Organization  # noqa: F401
