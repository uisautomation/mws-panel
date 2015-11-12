import json
import subprocess

from django.conf import settings

from apimws.ansible import LOGGER


class NameNotFoundException(Exception):
    pass


def get_nameinfo(name):
    try:
        response = subprocess.check_output(settings.IP_REG_API_END_POINT + ['get', 'nameinfo', name])
    except subprocess.CalledProcessError as excp:
        error_message = json.loads(excp.output)['message']
        LOGGER.error("get nameinfo call to IPREG API failed with exit code %i:\n\n%s\n\nCall:\n%s"
                     % (excp.returncode, excp.output, excp.cmd))
        raise NameNotFoundException(error_message)
    try:
        result = json.loads(response)
    except ValueError as e:
        LOGGER.error("IPREG API response is not properly formated: %s", response)
        raise e
    return result
