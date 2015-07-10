import click
import json
import six
import ipaddress
from jsonschema import validate


default_options = {
    'os': 'debian8',
    'features': {
        'cpu': 1,
        'memory': 2048,
        'disk': 20
    }
}


OS_SUPPORTED = ['debian8']
BUTTON_ACTIONS_ALLOWED = ['shutdown', 'reboot', 'poweroff', 'poweron']


parameters_json_schema = {
    "title": "JSON Schema for the create command",
    "type": "object",
    "properties": {
        "netconf": {
            "type": "object",
            "properties": {
                "IPv4": {
                    "type": "string",
                },
                "IPv6": {
                    "type": "string",
                },
                "hostname": {
                    "type": "string",
                },
            },
            "anyOf": [
                {"required": ["IPv4", "hostname"]},
                {"required": ["IPv6", "hostname"]}
            ]
        },
        "secrets": {
            "type": "object",
            "properties": {
                "sshrsa": {
                    "type": "string",
                },
                "sshdsa": {
                    "type": "string",
                },
                "sshecdsa": {
                    "type": "string",
                },
                "sshed25519": {
                    "type": "string",
                },
            },
        },
        "features": {
            "type": "object",
            "properties": {
                "cpu": {
                    "description": "the number of CPUs assigned",
                    "type": "integer",
                },
                "memory": {
                    "description": "the number of MB of RAM assigned",
                    "type": "integer",
                },
                "disk": {
                    "description": "the number of GB of disk assigned",
                    "type": "integer",
                },
            },
        },
        "os": {
            "type": "string",
        },
        "callback": {
            "description": "the URL to call after the installation process has finished",
            "type": "object",
            "properties": {
                "endpoint": {
                    "description": "the callback url where to POST the following two parameters",
                    "type": "string",
                },
                "vm_id": {
                    "description": "POST parameter for the callback with the VM id",
                    "type": "integer",
                },
                "secret": {
                    "description": "POST parameter for the callback with the token/secret",
                    "type": "string",
                },
            },
        },
    },
    "required": ["netconf"]
}


class OSNotSupportedException(Exception):
    pass


class JsonParamType(click.ParamType):
    name = 'json'

    def convert(self, value, param, ctx):
        try:
            parameters = json.loads(value)
            validate(parameters, parameters_json_schema)
            # Validation of IPv4 address
            if 'IPv4' in parameters['netconf']:
                ipaddress.ip_address(parameters['netconf']['IPv4'])
            if 'IPv6' in parameters['netconf']:
                ipaddress.ip_address(parameters['netconf']['IPv6'])
            if 'os' not in parameters:
                parameters['os'] = default_options['os']
            if parameters['os'] not in OS_SUPPORTED:
                raise OSNotSupportedException
            return parameters
        except ValueError:
            self.fail("The JSON parameter needs to be properly formatted")
            # raise click.ClickException("The JSON parameter needs to be properly formatted")
        except OSNotSupportedException:
            self.fail("The OS selected is not supported")
            # raise click.ClickException("The OS selected is not supported")

    def __repr__(self):
        return 'JSON'


JSONTYPE = JsonParamType()


class VirtualMachinesManager(object):
    """The virtual machines manager to create, clone, delete... VMs"""

    @classmethod
    def create(self, parameters):
        """This function creates a new VM with the parameters and options passed in parameters"""
        subprocess.check_output(["userv", "root", "vm_create", parameters])
        return {"vmid": parameters['netconf']['hostname']}

    @classmethod
    def delete(self, vmid):
        """This function deletes the vm with id = vmid"""
        pass

    @classmethod
    def button(self, vmid, action):
        """This function manages all the options related with power management of the VM.
        It can power on or power off the VM, and shutdown or reboot it."""
        pass

    @classmethod
    def copy(self, vmid_o, vmid_d):
        """This function replicates the content of the disk from the VM with id = vmid_o to the VM with
        id = vmid_d"""
        pass


@click.group()
def cli():
    pass


@cli.command()
@click.argument('json-parameters', required=True, type=JSONTYPE)
def create(json_parameters):
    response = VirtualMachinesManager.create(json_parameters)
    click.echo(json.dumps(response))


@cli.command()
@click.argument('vmid', required=True, type=click.STRING)
def delete(vmid):
    VirtualMachinesManager.delete(vmid)


@cli.command()
@click.argument('vmid', required=True, type=click.STRING)
@click.argument('action', required=True, type=click.Choice(BUTTON_ACTIONS_ALLOWED))
def button(vmid, action):
    VirtualMachinesManager.button(vmid, action)


@cli.command()
@click.argument('vmid', required=True, type=click.STRING)
@click.argument('json-parameters', required=True, type=JSONTYPE)
def clone(vmid, json_parameters):
    response = VirtualMachinesManager.create(json_parameters)
    VirtualMachinesManager.copy(vmid, response['vmid'])
    click.echo(json.dumps(response))
