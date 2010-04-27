import imp
import sys
import traceback
from django.core.handlers.wsgi import WSGIHandler
from django import conf
from django import utils

def make_app(config, **kwargs):
    return WSGIApplication(**kwargs)

class WSGIApplication(object):
    def __init__(self, settings=None):
        # set up django environment
        imp.load_source("settings", settings)
        settings = conf.Settings("settings")
        conf.settings.configure(settings)

        # activate language
        utils.translation.activate(conf.settings.LANGUAGE_CODE)

        self.handler = WSGIHandler()

    def __call__(self, environ, start_response):
        response = ["500 Internal Server Error", [], None]

        def _start_response(*args):
            response[:] = args

        try:
            chunks = self.handler(environ, _start_response)
        except:
            exc_info = sys.exc_info()
            chunks = traceback.format_exception(*exc_info)

        start_response(*response)
        return chunks
