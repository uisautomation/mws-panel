import logging
from django.http import HttpResponseForbidden
from django.template import loader, RequestContext


logger = logging.getLogger('mws')


def user_in_jackdaw(request):
    ''' Do not allow people that haven't been added to jackdaw yet,
    or that have been deleted from jackdaw to enter to the app
    (no User ID can cause problems)
    :param request: the http request
    :return: True if they are in jackdaw, False otherwise'''
    if hasattr(request.user, 'mws_user'):
        return True
    else:
        return False


def user_is_active(request):
    ''' Do not allow unactive user to enter the app
    :param request: the http request
    :return: True if they are active, False otherwise
    '''
    return request.user.is_active


# The CheckBannedUsers middleware check if users are banned before serving any page
# This class checks if the user is banned, and in that case, it redirects her to a 403 http response
class CheckBannedUsers():
    def __init__(self, *args, **kwargs):
        pass

    def process_request(self, request):
        try:
            if not request.user.is_authenticated() or (user_in_jackdaw(request) and user_is_active(request)):
                return None
            else:
                t = loader.get_template('403.html')
                c = RequestContext(request, {})
                return HttpResponseForbidden(t.render(c))
        except Exception as e:
            logger.error(str(request.user) + ' user cannot be found in lookup')
            t = loader.get_template('403.html')
            return HttpResponseForbidden(t.render())
