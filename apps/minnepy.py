#!/usr/bin/python
import sys

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from settings import template_path

_DEBUG = True

class Minnepy(webapp.RequestHandler):
    """Homepage"""
    def get(self):
        self.response.out.write(template.render(template_path + 'minnepy/minnepy.html', {}))

_URLS = [
    ('/', Minnepy),
]

def main(argv):
    application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
    run_wsgi_app(application)
    
if __name__ == '__main__':
    main(sys.argv)