"""
This command is used to add an Institution to the database.

Execution: python manage.py add_institution <name> <cas_server_url>
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.utils.text import slugify

from uniauth.models import Institution


class Command(BaseCommand):
    help = "Adds an institution to the database."

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument("cas_server_url")
        parser.add_argument(
            "--update-existing",
            action="store_true",
            default=False,
            help="Update the institution, if it already exists.",
        )

    def handle(self, *args, **options):
        slug = slugify(options["name"])
        cas_server_url = options["cas_server_url"]

        if (
            not options["update_existing"]
            and Institution.objects.filter(slug=slug).exists()
        ):
            raise CommandError(
                "An institution with slug '" + slug + "' already exists."
            )

        try:
            validator = URLValidator()
            validator(options["cas_server_url"])
        except ValidationError:
            raise CommandError(
                "Provided CAS server URL '"
                + cas_server_url
                + "' is malformed."
            )

        institution, created = Institution.objects.get_or_create(
            name=options["name"],
            slug=slug,
            defaults={"cas_server_url": cas_server_url},
        )

        if created:
            self.stdout.write("Created institution '%s'.\n" % str(institution))
        elif institution.cas_server_url != cas_server_url:
            # If institution already exists but with a different URL,
            # update it.
            institution.cas_server_url = cas_server_url
            institution.save()
            self.stdout.write("Updated institution '%s'.\n" % str(institution))
