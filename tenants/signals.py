from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from tenants.models import UserAccount, Account
from django.shortcuts import redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required

@receiver(user_logged_out)
def clear_tenant_on_logout(sender, request, user, **kwargs):
    if request:
        request.session.pop("tenant_id", None)

def set_current_account(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    request.session["account_id"] = account.id
    return redirect(request.META.get("HTTP_REFERER", "/"))
