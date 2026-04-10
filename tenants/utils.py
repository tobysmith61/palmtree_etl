from .models import Tenant, UserAccount, Account
from django.conf import settings
import os

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class NoTenantError(Exception):
    pass


class MultipleTenantsError(Exception):
    pass


def resolve_user_tenant(request):
    """
    Determines tenant for the logged-in user.
    May set request.session["tenant_id"].
    """
    user = request.user
    
    if not user.is_authenticated:
        return None

    # Superusers: do nothing automatically
    if user.is_superuser:
        return None

    # Get the user's account (exactly 1)
    account = UserAccount.objects.get(user=user).account

    # Get all tenants linked to that account
    tenants = Tenant.objects.filter(account=account)
    
    if tenants.count() == 0:
        raise NoTenantError("User has no tenants")

    if tenants.count() == 1:
        tenant = tenants.first()
        request.session["tenant_id"] = str(tenant.rls_key)
        return tenant

    # More than one → user must choose
    raise MultipleTenantsError("User has multiple tenants")

def get_current_tenant(request):
    tenant_id = request.session.get("tenant_id")
    if tenant_id:
        return Tenant.objects.get(rls_key=tenant_id)
    return None

def ensure_local_ready_folder(accountjob):
    logger.warning("🔧 ensure_local_ready_folder START")
    logger.warning(f"accountjob_id={getattr(accountjob, 'id', None)}")

    is_staging = getattr(settings, "IS_STAGING_SERVER", False)
    logger.warning(f"IS_STAGING_SERVER={is_staging}")
    logger.warning(f"BASE_DIR={getattr(settings, 'BASE_DIR', None)}")

    if is_staging:
        base_dir = f"{settings.BASE_DIR}/temp_files"
    else:
        base_dir = "/srv"

    logger.warning(f"base_dir={base_dir}")

    try:
        folder_path = accountjob.sftp_drop_zone.folder_path
    except Exception as e:
        logger.exception("❌ Failed to access folder_path on accountjob")
        raise

    logger.warning(f"raw folder_path={folder_path}")

    try:
        cleaned = folder_path.strip("/").split("/")
        logger.warning(f"split folder_path={cleaned}")
    except Exception as e:
        logger.exception("❌ Failed processing folder_path")
        raise

    try:
        subpath = "/".join(cleaned[-3:-1])
        logger.warning(f"subpath ([-3:-1])={subpath}")
    except Exception as e:
        logger.exception("❌ Failed building subpath")
        raise

    p = f"{base_dir}/sftp_drops/{subpath}/ready"

    logger.warning(f"FINAL PATH={p}")

    if is_staging:
        try:
            os.makedirs(p, exist_ok=True)
            logger.warning(f"Created directory (staging): {p}")
        except Exception as e:
            logger.exception(f"❌ Failed to create directory: {p}")
            raise
    else:
        logger.warning("Skipping mkdir (production mode)")

    logger.warning("🔧 ensure_local_ready_folder END")

    return p
