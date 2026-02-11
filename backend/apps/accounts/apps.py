from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'
    verbose_name = 'Gestion des Comptes'

    def ready(self):
        import apps.accounts.signals
