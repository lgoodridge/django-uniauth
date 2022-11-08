"""
This command is used to migrate a project previously using
CAS for authentication over to Uniauth.

Execution: python manage.py migrate_cas <slug>
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from uniauth.models import Institution, InstitutionAccount, UserProfile
from uniauth.utils import get_input


class Command(BaseCommand):
    help = "Migrates a project using CAS to Uniauth."

    def add_arguments(self, parser):
        parser.add_argument("slug")

    @transaction.atomic
    def handle(self, *args, **options):
        slug = options["slug"]

        try:
            institution = Institution.objects.get(slug=slug)
        except Institution.DoesNotExist:
            raise CommandError("No institution with slug '%s' exists." % slug)

        message = (
            "This command is intended to migrate projects "
            "previously using CAS for authentication to using Uniauth.\n\nYou "
            "should only proceed with this command if your project was "
            "previously using CAS for authentication, and the usernames for "
            "all existing Users are equivalent to their CAS ID. This command "
            "will create UserProfiles for each user with the Institution "
            "specified by the slug argument.\n\nDo you still wish to "
            "continue?\n\nAnswer [y/n]: "
        )
        answer = get_input(message)

        if answer != "y" and answer != "yes":
            self.stdout.write("\nCanceled.\n")
            return

        self.stdout.write("\nProceeding... ")
        for user in get_user_model().objects.all():
            # Skip users that already have UserProfiles
            if hasattr(user, "uniauth_profile"):
                continue
            # Update the username to the proper format
            cas_id = user.username
            user.username = "cas-%s-%s" % (slug, cas_id)
            user.save()
            # Add the profile
            profile = UserProfile.objects.create(user=user)
        self.stdout.write("Done!\n")
