from django.conf import settings

def developer_quick_login_buttons(request):
    return {
        'DEVELOPER_QUICK_LOGIN_BUTTONS': getattr(settings, 'DEVELOPER_QUICK_LOGIN_BUTTONS', False)
    }
