from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User


class Command(BaseCommand):

    help = 'Creates SuperUser Accounts'

    def handle(self, *args, **options):
        for user in settings.ADMINS:
            username = user[0].strip()
            email = user[1]
            password = settings.ADMIN_INITIAL_PASSWORD
            print('Creating account for %s (%s)' % (username, email))
            admin = User.objects.create_superuser(
                email=email, username=username, password=password
            )
            admin.is_active = True
            admin.is_staff = True
            admin.save()
