import re
import logging
from typing import Any, Dict, Optional
from backend.app.repositories.company_repository import CompanyRepository
from backend.app.repositories.profile_repository import ProfileRepository
from backend.app.utils.errors import ValidationError, ConflictError, NotFoundError

logger = logging.getLogger(__name__)


def generate_slug(name: str) -> str:
    """Generates a clean URL-friendly slug from a company name."""
    cleaned = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", cleaned)
    return slug[:100] if slug else "company"


class CompanyService:
    """Service handling company lifecycle and onboarding."""

    def __init__(
        self,
        company_repository: Optional[CompanyRepository] = None,
        profile_repository: Optional[ProfileRepository] = None,
    ):
        self.company_repo = company_repository or CompanyRepository()
        self.profile_repo = profile_repository or ProfileRepository()

    def create_company_with_owner(
        self,
        user_id: str,
        user_email: str,
        company_name: str,
        owner_name: Optional[str] = None,
        company_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atomically provisions a new company tenant and links the authenticated user as Owner.
        Ensures a user cannot create multiple tenant workspaces simultaneously in Phase 1.
        """
        # Validate company name
        if not company_name or not isinstance(company_name, str):
            raise ValidationError("Company name is required and must be a string")

        clean_name = company_name.strip()
        if len(clean_name) < 2 or len(clean_name) > 255:
            raise ValidationError("Company name must be between 2 and 255 characters")

        # Check if the user already has a company profile
        existing_profile = self.profile_repo.get_by_id(user_id)
        if existing_profile and existing_profile.get("company_id"):
            raise ConflictError("User is already associated with an existing company workspace")

        # Determine slug
        slug = company_slug.strip().lower() if company_slug else generate_slug(clean_name)
        if len(slug) < 2 or len(slug) > 100:
            raise ValidationError("Company slug must be between 2 and 100 characters")

        existing_company_by_slug = self.company_repo.get_by_slug(slug)
        if existing_company_by_slug:
            raise ConflictError(f"Company slug '{slug}' is already taken")

        full_name = owner_name.strip() if owner_name else clean_name + " Owner"

        # Attempt atomic database RPC (Migration 002: public.create_company_with_owner)
        try:
            rpc_result = self.company_repo.create_with_owner_rpc(
                name=clean_name,
                slug=slug,
                full_name=full_name,
                settings={},
            )
            if rpc_result and "company" in rpc_result and "profile" in rpc_result:
                return rpc_result
        except AttributeError:
            # Fallback if injected client does not expose .rpc (e.g. basic mock)
            pass
        except Exception as rpc_err:
            logger.warning(f"RPC onboarding failed or not available, attempting repository fallback: {rpc_err}")

        # Fallback Multi-Step Execution with Compensating Rollback
        # 1. Create Company
        company_payload = {
            "name": clean_name,
            "slug": slug,
            "subscription_tier": "starter",
            "settings": {},
        }

        created_company = self.company_repo.create(company_payload)
        company_id = created_company["id"]

        # 2. Create Owner Profile
        profile_payload = {
            "id": user_id,
            "company_id": company_id,
            "email": user_email,
            "full_name": full_name,
            "role": "owner",
            "is_active": True,
        }

        try:
            created_profile = self.profile_repo.create(profile_payload)
        except Exception as e:
            # Rollback: Clean up created company to prevent orphan tenant records
            logger.error(f"Failed to create profile for user {user_id}, rolling back company {company_id}: {e}")
            try:
                self.company_repo.delete(company_id)
            except Exception as rollback_err:
                logger.critical(f"Failed to rollback company {company_id}: {rollback_err}")
            raise

        return {
            "company": created_company,
            "profile": created_profile,
        }

    def get_company_details(self, company_id: str) -> Dict[str, Any]:
        """Retrieves sanitized company details."""
        if not company_id:
            raise NotFoundError("Company not found")

        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise NotFoundError("Company not found")

        return {
            "id": company["id"],
            "name": company["name"],
            "slug": company.get("slug"),
            "subscription_tier": company.get("subscription_tier", "starter"),
            "created_at": company.get("created_at"),
            "updated_at": company.get("updated_at"),
        }
