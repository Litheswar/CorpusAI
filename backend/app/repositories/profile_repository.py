import logging
from typing import Any, Dict, List, Optional
from backend.app.utils.supabase_client import get_supabase_admin_client
from backend.app.utils.errors import InternalServerError

logger = logging.getLogger(__name__)


class ProfileRepository:
    """Repository handling persistence for user profiles."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client or get_supabase_admin_client()

    def create(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new profile tied to auth.users and a company."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").insert(profile_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            raise InternalServerError("Failed to create profile record")
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            raise

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a profile by Supabase Auth user ID."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching profile by id {user_id}: {e}")
            raise

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves a profile by email."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").select("*").eq("email", email).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching profile by email {email}: {e}")
            raise

    def list_by_company(self, company_id: str) -> List[Dict[str, Any]]:
        """Lists all active profiles belonging to a specific company."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").select("*").eq("company_id", company_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing profiles for company {company_id}: {e}")
            raise

    def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates profile details."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").update(data).eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating profile {user_id}: {e}")
            raise

    def delete(self, user_id: str) -> bool:
        """Deletes a profile by user ID."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("profiles").delete().eq("id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting profile {user_id}: {e}")
            raise
