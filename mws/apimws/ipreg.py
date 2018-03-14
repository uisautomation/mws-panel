import json
import logging
import subprocess
from celery import shared_task
from django.conf import settings
from apimws.jackdaw import SSHTaskWithFailure
import dns.resolver
import dns.flags

LOGGER = logging.getLogger('mws')


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
        result = ip_reg_call(['get', 'nameinfo', str(hostname)])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def get_cname(hostname):
    try:
        result = ip_reg_call(['get', 'cname', str(hostname)])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


class DomainNameDelegatedException(Exception):
    pass


def set_cname(hostname, target):
    try:
        result = ip_reg_call(['put', 'cname', str(hostname), str(target)])
    except subprocess.CalledProcessError as excp:
        if excp.returncode == 7:
            raise DomainNameDelegatedException()
        raise excp
    return result


@shared_task(base=SSHTaskWithFailure)
def delete_cname(hostname):
    try:
        result = ip_reg_call(['delete', 'cname', str(hostname)])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def find_sshfp(hostname):
    result = []

    r = dns.resolver.Resolver()
    r.use_edns(0, dns.flags.DO, 4096) # DNSSEC query

    try:
        answer = r.query(hostname, 'SSHFP')
        for record in [rr.to_text() for rr in answer]:
            (algorithm, fptype, fingerprint) = record.split()
            result.append({'algorithm': algorithm, 'fptype': fptype, 'fingerprint': fingerprint})
    except Exception as excp:
        raise excp
    return result


def set_sshfp(hostname, algorithm, fptype, fingerprint):
    try:
        result = ip_reg_call(['put', 'sshfp', str(hostname), str(algorithm), str(fptype), str(fingerprint)])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result


def delete_sshfp(hostname, algorithm, fptype):
    try:
        result = ip_reg_call(['delete', 'sshfp', str(hostname), str(algorithm), str(fptype)])
    except subprocess.CalledProcessError as excp:
        raise excp
    return result
