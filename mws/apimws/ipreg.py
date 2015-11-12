import json
import subprocess

from django.conf import settings

from apimws.ansible import LOGGER


def ip_reg_call(call):
    try:
        response = subprocess.check_output(settings.IP_REG_API_END_POINT + call)
    except subprocess.CalledProcessError as excp:
        error_message = json.loads(excp.output)['message']
        LOGGER.error("IPREG API Call: %s\n\nFAILED with exit code %i:\n%s"
                     % (excp.cmd, excp.returncode, excp.output))
        raise excp
    try:
        result = json.loads(response)
    except ValueError as e:
        LOGGER.error("IPREG API response to call (%s) is not properly formatted: %s", call, response)
        raise e
    return result



def get_nameinfo(hostname):
    try:
        result = ip_reg_call(['get', 'nameinfo', hostname])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def get_cname(hostname):
    try:
        result = ip_reg_call(['get', 'cname', hostname])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def set_cname(hostname, target):
    try:
        result = ip_reg_call(['put', 'cname', hostname, target])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def delete_cname(hostname):
    try:
        result = ip_reg_call(['delete', 'cname', hostname])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def find_sshfp(hostname):
    try:
        result = ip_reg_call(['find', 'sshfp', hostname])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def set_sshfp(hostname, algorithm, fptype, fingerprint):
    try:
        result = ip_reg_call(['put', 'sshfp', hostname, algorithm, fptype, fingerprint])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def delete_sshfp(hostname, algorithm, fptype):
    try:
        result = ip_reg_call(['delete', 'sshfp', hostname, algorithm, fptype])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result
