"""
This command is used to flush old temporary accounts from the database.

Users with a username prefix of "tmp-" more than the specified number of
days old will be deleted. The default number of days is 1.

Execution: python manage.py flush_tmp_users [days]
"""

from django.core.management.base import BaseCommand, CommandError
from uniauth.utils import flush_old_tmp_users, get_input


class Command(BaseCommand):
    help = "Deletes old temporary accounts from the database."

    def add_arguments(self, parser):
        parser.add_argument('days', type=int, nargs='?', default=1)

    def handle(self, *args, **options):
        days = options['days']

        answer = get_input("Are you sure you want to delete all temporary" +
                "users more than %d days old?\nAnswer [y/n]:" % days)
        if answer == "y" or answer == "yes":
            num_deleted = flush_old_tmp_users(days=days)
            self.stdout.write("Deleted %d temporary users.\n")
        else:
            self.stdout.write("Canceled.\n")
