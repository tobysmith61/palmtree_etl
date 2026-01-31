# tenants/tests/test_account_switch.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from tenants.models import UserAccount, Account, Tenant

User = get_user_model()

class AccountTenantUserTests(TestCase):
    def setUp(self):
        # Create account
        self.account = Account.objects.create(name="acme_test_account")

        # Create a tenant group (leaf node for simplicity)
        self.tenant = Tenant.objects.create(desc="Acme Tenant Group", account=self.account)

        # Create user
        self.user = User.objects.create_user(username="jondoe", password="password123")

        # Link user to account
        UserAccount.objects.create(user=self.user, account=self.account)

        # Django test client
        self.client = Client()

    def test_login_set_account_and_logout(self):
        """Login user, set account in session, then logout and verify session cleared."""
        # Log in user
        logged_in = self.client.login(username="jondoe", password="password123")
        self.assertTrue(logged_in, "Login failed")

        # Set account in session
        session = self.client.session
        session["account_id"] = self.account.id
        session["tenant_id"] = str(self.tenant.rls_key)
        session.save()

        # Confirm session is set
        self.assertEqual(self.client.session["account_id"], self.account.id)
        self.assertEqual(self.client.session["tenant_id"], str(self.tenant.rls_key))

        # POST to logout view
        response = self.client.post(reverse("logout"), follow=True)

        # Confirm redirect to login page
        self.assertRedirects(response, "/login/")

        # Session should no longer have account_id or tenant_id
        self.assertNotIn("account_id", self.client.session)
        self.assertNotIn("tenant_id", self.client.session)

        # Confirm user is logged out
        self.assertNotIn("_auth_user_id", self.client.session)
