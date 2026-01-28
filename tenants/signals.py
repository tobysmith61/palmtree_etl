from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

@receiver(user_logged_out)
def clear_tenant_on_logout(sender, request, user, **kwargs):
    if request:
        request.session.pop("tenant_id", None)
