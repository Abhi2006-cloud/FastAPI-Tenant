"""
Central import of all SQLAlchemy models.

Alembic and Base.metadata need every table class loaded once so migrations
and create_all() see the full schema. Do not define models here — only import them.
"""

from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.auth.models import User  # noqa: F401
from app.modules.auth.session_model import UserSession  # noqa: F401
from app.modules.auth.auth_audit_model import AuthAuditLog  # noqa: F401
from app.modules.files.models import FileRecord  # noqa: F401
from app.modules.invitations.models import Invitation  # noqa: F401
from app.modules.memberships.models import Membership  # noqa: F401
from app.modules.organizations.models import Organization  # noqa: F401
from app.modules.search.models import SearchIndexFailure  # noqa: F401
from app.modules.email.models import EmailLog  # noqa: F401


