from django.core.exceptions import ValidationError
import re
from mwsauth.utils import get_or_create_user_by_crsid, get_or_create_group_by_groupid


def validate_crsids(crsids_text):
    """ Validates the list of authorsied users from input
        :param crsids_text: list of crsids from the form
    """

    users = ()

    if crsids_text is None:
        return users

    crsids = crsids_text.split(',')

    if len(crsids) == 1 and crsids[0] == '':
        return users

    crsid_re = re.compile(r'^[a-z][a-z0-9]{3,7}$')
    for crsid in crsids:
        if crsid_re.match(crsid):
            users += (get_or_create_user_by_crsid(crsid),)
        else:
            raise ValidationError("The list of users contains an invalid user")

    return users


def validate_groupids(groupids_text):
    """ Validates the list of authorsied users from input
        :param groupids_text: list of groupids from the form
    """

    groups = ()

    if groupids_text is None:
        return groups

    groupids = groupids_text.split(',')

    if len(groupids) == 1 and groupids[0] == '':
        return groups

    groupid_re = re.compile(r'^[0-9]{1,6}$')

    for groupid in groupids:
        if groupid_re.match(groupid):
            groups += (get_or_create_group_by_groupid(int(groupid)),)
        else:
            raise ValidationError("The list of groups contains an invalid group")

    return groups
