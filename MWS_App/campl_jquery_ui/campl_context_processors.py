# If your Project Light page uses tabs as part of its subheading (like the "search" page)
# define them here, along with their destinations, and then add
# TEMPLATE_CONTEXT_PROCESSORS = ('myapp.campl_context_processors.tabs',)
# to your settings.py
def tabs(request):
    tabs = {}
    tabs[0] = dict(name="Main",url='index')
    tabs[1] = dict(name="Example",url='example')
    tabs[2] = dict(name="Test",url='test')
    return {'tabs': tabs}