"""
This command is used to add an Institution to the database.

Execution: python manage.py add_institution <name> <cas_server_url>
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import URLValidator
from django.utils.text import slugify
from uniauth.models import Institution

class Command(BaseCommand):
    help = "Adds an institution to the database."

    def add_arguments(self, parser):
        parser.add_argument('name')
        parser.add_argument('cas_server_url')

    def handle(self, *args, **options):
        slug = slugify(options['name'])
        cas_server_url = options['cas_server_url']

        if Institution.objects.filter(slug=slug).exists():
            self.stdout.write("An institution with slug '" +
                    slug + "' already exists.\n")
            return

        try:
            validator = URLValidator()
            validator(options['cas_server_url'])
        except ValidationError:
            self.stdout.write("Provided CAS server URL '" +
                    cas_server_url + "' is malformed.\n")
            return

        institution = Institution.objects.create(name=options['name'],
                slug=slug, cas_server_url=cas_server_url)
        self.stdout.write("Created institution '%s'.\n" % str(institution))
