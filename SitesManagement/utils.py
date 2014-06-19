import re
from django.contrib.auth.models import User
from django.shortcuts import _get_queryset
from ibisclient import *

conn = createConnection()


def get_institutions(user=None):
    """ Returns the list of institutions using the lookup ucam service. The institutions of the user doing
    the request will be shown first
        :param user: the user doing the request
    """

    all_institutions = InstitutionMethods(conn).allInsts(includeCancelled=False)
    # filter all the institutions that were created for store year students
    all_institutions = filter(lambda institution: re.match(r'.*\d{2}$', institution.id) is None, all_institutions)

    if user is not None:
        try:
            all_institutions = PersonMethods(conn).getInsts("crsid", user.username) + all_institutions
        except IbisException:
            pass

    return map((lambda institution: (institution.instid, institution.name)), all_institutions)


def get_users_from_query(search_string):
    """ Returns the list of people based on the search string using the lookup ucam service
        :param search_string: the search string
    """
    persons = PersonMethods(conn).search(query=search_string)

    return map((lambda person: {'crsid': person.identifier.value, 'visibleName': person.visibleName}),
               persons)


def get_or_create_user_by_crsid(crsid):
    """ Returns the django user corresponding to the crsid parameter.
        :param crsid: the crsid of the retrieved user
    """

    user = User.objects.filter(username=crsid)
    if user.exists():
        user = user.first()
    else:
        user = User(username=crsid)
        user.save()

    return user


def return_visibleName_by_crsid(crsid):
    person = PersonMethods(conn).getPerson(scheme='crsid', identifier=crsid)
    return person.visibleName if person is not None else ''


def get_institution_name_by_id(institution_id, all_institutions=None):
    if all_institutions is not None:
        instname = next((institution[1] for institution in all_institutions if institution[0] == institution_id), None)
    else:
        institution = InstitutionMethods(conn).getInst(instid=institution_id)
        instname = institution.name if institution is not None else None

    return instname if instname is not None else 'This institution no longer exists in the database'


def get_object_or_None(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None