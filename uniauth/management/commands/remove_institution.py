"""
This command is used to remove an Institution from the database.

Execution: python manage.py remove_institution <slug>
"""

from django.core.management.base import BaseCommand, CommandError
from uniauth.models import Institution
from uniauth.utils import get_input


class Command(BaseCommand):
    help = "Removes an institution from the database."

    def add_arguments(self, parser):
        parser.add_argument('slug')

    def handle(self, *args, **options):
        slug = options['slug']

        try:
            institution = Institution.objects.get(slug=slug)
        except Institution.DoesNotExist:
            raise CommandError("No institution with slug '%s' exists." % slug)

        answer = get_input("Are you sure you want to delete institution '" +
                str(institution) +"'?\nThis will also delete all " +
                "InstitutionAccounts for that institution.\nAnswer [y/n]: ")
        if answer == "y" or answer == "yes":
            institution.delete()
            self.stdout.write("Deleted institution '%s'.\n" % str(institution))
        else:
            self.stdout.write("Canceled.\n")

