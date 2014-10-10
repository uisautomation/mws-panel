from django.test import TestCase
from django.core.management.base import CommandError

# Don't just import as Command, or "test_ansible_inventory" appears to be
# a command as well.
from .ansible_inventory import Command as TestCommand

class CommandTests(TestCase):
    def test_options(self):
        with self.assertRaises(CommandError):
            TestCommand().handle_noargs(list=None, host=None)
        with self.assertRaises(CommandError):
            TestCommand().handle_noargs(list=True, host="foo")
    def test_args(self):
        with self.assertRaises(CommandError):
            TestCommand().handle("foo", list=True)
