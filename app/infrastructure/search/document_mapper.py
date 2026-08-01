from typing import Any, Dict
from app.modules.organizations.models import Organization
from app.modules.memberships.models import Membership
from app.modules.files.models import FileRecord
from app.modules.audit.models import AuditLog

def map_organization(org: Organization) -> Dict[str, Any]:
    """Map Organization ORM model to Meilisearch document."""
    return {
        "id": str(org.id),
        "name": org.name,
        "owner_id": str(org.owner_id),
        "created_at": int(org.created_at.timestamp()) if org.created_at else None,
    }

def map_member(membership: Membership) -> Dict[str, Any]:
    """Map Membership ORM model to Member Meilisearch document."""
    role_val = membership.role.value if hasattr(membership.role, "value") else str(membership.role)
    email_val = membership.user.email if membership.user else ""
    created_at_val = None
    if membership.user and membership.user.created_at:
        created_at_val = int(membership.user.created_at.timestamp())
        
    return {
        "id": str(membership.id),
        "user_id": str(membership.user_id),
        "organization_id": str(membership.organization_id),
        "role": role_val,
        "email": email_val,
        "created_at": created_at_val,
    }

def map_file(file: FileRecord) -> Dict[str, Any]:
    """Map FileRecord ORM model to File Meilisearch document."""
    return {
        "id": str(file.id),
        "organization_id": str(file.organization_id),
        "uploaded_by": str(file.uploaded_by),
        "file_name": file.file_name,
        "file_path": file.file_path,
        "file_size": file.file_size,
        "created_at": int(file.created_at.timestamp()) if file.created_at else None,
    }

def map_audit_log(audit: AuditLog) -> Dict[str, Any]:
    """Map AuditLog ORM model to Audit Log Meilisearch document."""
    action_val = audit.action.value if hasattr(audit.action, "value") else str(audit.action)
    metadata_val = audit.metadata_ if hasattr(audit, "metadata_") else getattr(audit, "metadata", None)
    
    return {
        "id": str(audit.id),
        "organization_id": str(audit.organization_id),
        "actor_user_id": str(audit.actor_user_id) if audit.actor_user_id else None,
        "action": action_val,
        "resource_type": audit.resource_type,
        "resource_id": str(audit.resource_id) if audit.resource_id else None,
        "metadata": metadata_val,
        "created_at": int(audit.created_at.timestamp()) if audit.created_at else None,
    }
