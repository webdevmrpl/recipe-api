"""
Test django management test commands
"""

from unittest.mock import patch
# This error is returned when postgres didn't start and isn't ready to accept new connections
from psycopg2 import OperationalError as Psycopg2Error
from django.core.management import call_command
# This error is returned when postgres has already started but hasn't setup db we want to use
from django.db.utils import OperationalError
from django.test import SimpleTestCase


@patch('core.management.commands.wait_for_db.Command.check')
class CommandTest(SimpleTestCase):

    def test_wait_for_db_ready(self, patched_check):
        """Waiting for db to get ready"""
        patched_check.return_value = True

        call_command("wait_for_db")

        patched_check.assert_called_once_with(databases=['default'])

    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """ Waiting for db when getting OperationalError."""
        patched_check.side_effect = [Psycopg2Error] * 2 + \
                                    [OperationalError] * 3 + [True]

        call_command('wait_for_db')

        self.assertEqual(patched_check.call_count, 6)
        patched_check.assert_called_with(databases=['default'])
