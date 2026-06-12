"""
MEMBERSHIPS MODULE — router.py

V1 has no public membership endpoints. Membership is managed indirectly:
  - create org -> owner membership
  - accept invite -> member membership

This router is a placeholder for future routes (list members, change role, etc.).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/memberships", tags=["memberships"])
