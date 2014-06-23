from django.core.exceptions import ValidationError
import re
from mwsauth.utils import get_or_create_user_by_crsid


def validate_crsids(crsids_text):
    """ Validates the list of authorsied users from input
        :param crsids: list of crsids from the form
    """

    crsid_re = re.compile(r'^[a-z][a-z0-9]{3,7}$')
    crsids = crsids_text.split(',')
    users = ()

    for crsid in crsids:
        if crsid_re.match(crsid):
            users += (get_or_create_user_by_crsid(crsid),)
        else:
            raise ValidationError("The list of users contains an invalid user")

    return users