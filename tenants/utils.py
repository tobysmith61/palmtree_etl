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
    is_staging = getattr(settings, "IS_STAGING_SERVER", False)
    
    if is_staging:
        base_dir = f"{settings.BASE_DIR}/temp_files"
    else:
        base_dir = "/srv"

    try:
        folder_path = accountjob.sftp_drop_zone.folder_path
    except Exception as e:
        raise

    try:
        cleaned = folder_path.strip("/").split("/")
    except Exception as e:
        raise

    try:
        subpath = "/".join(cleaned[-3:-1])
    except Exception as e:
        raise

    p = f"{base_dir}/sftp_drops/{subpath}/ready"

    if is_staging:
        try:
            os.makedirs(p, exist_ok=True)
        except Exception as e:
            raise
    
    return p
