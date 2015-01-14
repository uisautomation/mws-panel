import logging
from django.core.urlresolvers import resolve
from django.http import HttpResponseForbidden
from django.template import loader, RequestContext
from ucamlookup import user_in_groups
from mwsauth.utils import get_or_create_group_by_groupid


logger = logging.getLogger('mws')


#TODO The CheckBannedUsers middleware check if users are banned before serving any page
# This class checks if the user is banned, and in that case, it redirects her to a 403 http response
class CheckBannedUsers():
    def __init__(self, *args, **kwargs):
        pass

    def process_request(self, request):
        try:
            if request.user.is_authenticated() and hasattr(request.user, 'suspendeduser') \
                    and (request.user.suspendeduser.suspended is True)\
                    and (resolve(request.path).url_name != 'logout')\
                    or request.user.is_authenticated \
                            and not user_in_groups(request.user, [get_or_create_group_by_groupid(101888),
                                                                  get_or_create_group_by_groupid(101128)]):
                t = loader.get_template('403.html')
                c = RequestContext(request, {})
                return HttpResponseForbidden(t.render(c))
            else:
                return None
        except Exception as e:
            logger.error(str(request.user) + ' user cannot be found in lookup')
            t = loader.get_template('403.html')
            c = RequestContext(request, {})
            return HttpResponseForbidden(t.render(c))