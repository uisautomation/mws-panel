from ibisclient import *


conn = createConnection()

def get_users_from_query(search_string):
    """ Returns the list of people based on the search string using the lookup ucam service
        :param search_string: the search string
    """
    persons = PersonMethods(conn).search(query=search_string)

    return map((lambda person: {'crsid': person.identifier.value, 'visibleName': person.visibleName}),
               persons)


def return_visibleName_by_crsid(crsid):
    person = PersonMethods(conn).getPerson(scheme='crsid', identifier=crsid)
    return person.visibleName if person is not None else ''


def get_groups_from_query(search_string):
    """ Returns the list of groups based on the search string using the lookup ucam service
        :param search_string: the search string
    """
    groups = GroupMethods(conn).search(query=search_string)

    return map((lambda group: {'groupid': group.groupid, 'title': group.title}),
               groups)


def return_title_by_groupid(groupid):
    group = GroupMethods(conn).getGroup(groupid=groupid)
    return group.title if group is not None else ''


def get_groups_of_a_user_in_lookup(user):
    """ Returns the list of groups of a user in the lookup service
    :param user: the user
    :return: the list of group_ids
    """

    group_list = PersonMethods(conn).getGroups(scheme="crsid", identifier=user.username)
    return map(lambda group: int(group.groupid), group_list)