from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

def superuser_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_active and u.is_superuser
    )(view_func)
    return decorated_view_func

@superuser_required
def create_sftp_account_instructions(request):
    return render(request, "vendor/create_sftp_account_instructions.html")
