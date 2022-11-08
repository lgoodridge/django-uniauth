"""
This command is used to migrate a project previously using
custom User authentication over to Uniauth.

Execution: python manage.py migrate_custom
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from uniauth.models import LinkedEmail, UserProfile
from uniauth.utils import get_input


class Command(BaseCommand):
    help = "Migrates a project using custom User auhentication to Uniauth."

    @transaction.atomic
    def handle(self, *args, **options):
        message = (
            "This command is intended to migrate projects "
            "previously using custom User authentication to using Uniauth.\n\n"
            "You should only proceed with this command if your project had "
            "users sign up with a username / email address and password. This "
            "command will create UserProfile for each user with a username or "
            "email address, and a non-blank password. A verified LinkedEmail "
            "will also be created if the email field is non-blank.\n\n"
            "Do you still wish to continue?\n\nAnswer [y/n]: "
        )
        answer = get_input(message)

        if answer != "y" and answer != "yes":
            self.stdout.write("\nCanceled.\n")
            return

        self.stdout.write("\nProceeding... ")
        skipped = []
        for user in get_user_model().objects.all():
            # Skip users that already have UserProfiles
            if hasattr(user, "uniauth_profile"):
                continue
            # Skip users lacking a username/email address or password
            if (not user.username and not user.email) or not user.password:
                skipped.append(user.username or user.email or "(none)")
                continue
            # Add the profile + LinkedEmail if email field is non-blank
            profile = UserProfile.objects.create(user=user)
            if user.email:
                LinkedEmail.objects.create(
                    profile=profile, address=user.email, is_verified=True
                )
        self.stdout.write("Done!\n")

        if len(skipped) > 0:
            self.stdout.write(
                "\nThe following users could not be "
                + "migrated: %s\n" % str(skipped)
            )
