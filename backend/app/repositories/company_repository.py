import logging
from typing import Any, Dict, Optional
from backend.app.utils.supabase_client import get_supabase_admin_client
from backend.app.utils.errors import InternalServerError

logger = logging.getLogger(__name__)


class CompanyRepository:
    """Repository handling persistence for companies (tenants)."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client or get_supabase_admin_client()

    def create(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new company into the database."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("companies").insert(company_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            raise InternalServerError("Failed to create company record")
        except Exception as e:
            logger.error(f"Error creating company: {e}")
            raise

    def get_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a company by its UUID."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("companies").select("*").eq("id", company_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching company by id {company_id}: {e}")
            raise

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Retrieves a company by its unique slug."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("companies").select("*").eq("slug", slug).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching company by slug {slug}: {e}")
            raise

    def update(self, company_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates company details."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("companies").update(data).eq("id", company_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating company {company_id}: {e}")
            raise

    def delete(self, company_id: str) -> bool:
        """Deletes a company by UUID."""
        client = self.client
        if not client:
            raise InternalServerError("Database client unavailable")

        try:
            response = client.table("companies").delete().eq("id", company_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting company {company_id}: {e}")
            raise
