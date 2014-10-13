from django.test import TestCase
from django.core.management.base import CommandError
import json
from StringIO import StringIO

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
    def test_list_minimal(self):
        s = StringIO()
        Command().handle_noargs(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertTrue('_meta' in r)
        self.assertTrue('hostvars' in r['_meta'])
        self.assertTrue(isinstance(r['_meta']['hostvars'], dict))
        self.assertTrue('mwsclients' in r)
        self.assertTrue(isinstance(r['mwsclients'], list))

            
