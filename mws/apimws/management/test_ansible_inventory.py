from django.test import TestCase
from django.core.management.base import CommandError

from .commands.ansible_inventory import Command

class CommandTests(TestCase):
    def test_options(self):
        with self.assertRaises(CommandError):
            Command().handle_noargs(list=None, host=None)
        with self.assertRaises(CommandError):
            Command().handle_noargs(list=True, host="foo")
    def test_args(self):
        with self.assertRaises(CommandError):
            Command().handle("foo", list=True)
