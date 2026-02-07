class AccountScopedMixin:
    account_field = "account"

    def filter_by_account(self, request, qs):
        account_id = request.session.get("account_id")
        if account_id:
            return qs.filter(**{f"{self.account_field}_id": account_id})
        return qs

class AccountScopedAdminMixin(AccountScopedMixin):
    # -------------------------
    # Queryset filtering
    # -------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return self.filter_by_account(request, qs)

    # -------------------------
    # Make account read-only if session account is set
    # -------------------------
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.session.get("account_id"):
            readonly.append(self.account_field)
        return readonly

    # -------------------------
    # Auto-assign account on creation
    # -------------------------
    def save_model(self, request, obj, form, change):
        if not change and request.session.get("account_id"):
            setattr(obj, f"{self.account_field}_id", request.session["account_id"])
        super().save_model(request, obj, form, change)


    # Pass info to template: disable dropdown on change/add pages
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = False
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["disable_account_dropdown"] = True
        return super().add_view(request, form_url, extra_context=extra_context)
    
class AccountScopedInlineMixin(AccountScopedMixin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return self.filter_by_account(request, qs)
