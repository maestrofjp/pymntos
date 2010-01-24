#!/usr/bin/env python
from settings import template_path
import sys
import mimetypes
import os

import markdown

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

_DEBUG = True

class Page(db.Model):
    path = db.StringProperty()
    title = db.StringProperty()
    body = db.TextProperty()
    @classmethod
    def by_name(cls, name):
        pages = list(Page.all().filter('path =', name))
        if not pages:
            return Page(path=name, title='', body='')
        return pages[0]

    @property
    def exists(self):
        return self.is_saved()

    @property
    def rendered_body(self):
        return markdown.markdown(self.body)
        #return unicode(sys.path)

def render(template_name, **kw):
    kw['sidebar'] = Page.by_name('/sidebar').rendered_body
    return template.render(template_path + template_name, kw)

class Blog(webapp.RequestHandler):
    pass

class LandingPage(webapp.RequestHandler):
    """Landing Page, since it's different from other pages."""
    def get(self):
        self.response.out.write(
            render(
                'landing.html',
                title='PyMNtos: Twin Cities Python User Group'))
        return

class Wiki(webapp.RequestHandler):
    """Wiki"""
    def get(self):
        page_name = self.request.path_info
        page = Page.by_name(page_name)
        if not page.exists or 'edit' in self.request.GET:
            self.response.out.write(render('edit.html',
                                           page=page, title='Edit %s' % page_name))
            return
        extension = os.path.splitext(page_name)[1]
        if extension:
            type, encoding = mimetypes.guess_type(extension)
            self.response.headers.add_header('Content-Type', type)
            self.response.out.write(page.body)
            return
        self.response.out.write(render('view.html',
                                       page=page, title=page.title))

    def post(self):
        page = Page.by_name(self.request.path_info)
        page.title = self.request.POST['title']
        page.body = self.request.POST['body']
        page.put()
        self.redirect(self.request.url)

_URLS = [
    ('/', LandingPage),
    ('^/blog', Blog),
    ('.*', Wiki),
]

def main(argv):
    application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
    run_wsgi_app(application)
    
if __name__ == '__main__':
    main(sys.argv)