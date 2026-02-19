from tenants.models import Account

def tenant_context(request):
    tenant = getattr(request, "current_tenant", None)
    user = request.user
    can_edit = False

    if tenant and user.is_authenticated:
        can_edit = user.is_superuser or user.has_perm("tenants.change_tenant")
        
    # Add current account
    account = None
    account_id = request.session.get("account_id")
    if account_id:
        account = Account.objects.filter(id=account_id).first()
    print ('Account: '+str(account))

    return {
        "tenant": tenant,
        "can_edit_tenant": can_edit,
        "current_account": account,
    }

def account_context(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.is_superuser:
        accounts = Account.objects.exclude(name='palmTree')
    else:
        accounts = Account.objects.filter(
            useraccount__user=request.user
        )

    return {
        "available_accounts": accounts,
        "account_id": request.session.get("account_id"),
    }
