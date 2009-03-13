#!/usr/bin/python
import sys

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.util import login_required

from settings import template_path

_DEBUG = True

class Blog(db.Model):
    author = db.UserProperty(required=True)
    title = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True, required=True)
    
class Entry(db.Model):
    author = db.UserProperty(required=True)
    title = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    published = db.DateTimeProperty()
    updated = db.DateTimeProperty(auto_now=True, required=True)
    created = db.DateTimeProperty(auto_now_add=True, required=True)
    
class BlogForm(djangoforms.ModelForm):
    class Meta:
        model = Blog
        exclude = ['created', 'author']
        
class EntryForm(djangoforms.ModelForm):
    class Meta:
        model = Entry
        exclude = ['updated', 'created']
    
class Blogs(webapp.RequestHandler):
    """list blogs"""
    @login_required
    def get(self):
        content = {
            'blogs' : db.GqlQuery("SELECT * FROM Blog"),
            'blog_form' : BlogForm(),
        }
        self.response.out.write(template.render(template_path + 'blog/blogs.html', content))
        
    """create blog"""
    def post(self):
        content = {
            'blog_form' : BlogForm(data=self.request.POST),
        }
        
        if content['blog_form'].is_valid():
            blog = content['blog_form'].save(commit=False)
            blog.author = users.get_current_user()
            blog.put()
        self.redirect('/blogs')
        
    """update blog"""
    def put(self):
        self.response.out.write(template.render(template_path + 'blog/b'))
        
    """delete blog"""
    def delete(self):
        pass
        
class Blog(webapp.RequestHandler):
    """list blog entries"""
    def get(self):
        author = None
        content = {
            'entries' : db.Query(Entry).filter('author =', author)
        }
        self.response.out.write(template.render(template_path + 'blog/blog.html', {}))
        
    """create blog entry"""
    def post(self):
        content = {
            'entry_form' : EntryForm(),
        }
        self.response.out.write(template.render(template_path + 'blog/create_entry.html', {}))

_URLS = [
    ('/blogs', Blogs),
    ('/blog', Blog),
]

def main(argv):
    application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
    run_wsgi_app(application)
    
if __name__ == '__main__':
    main(sys.argv)