#!/usr/bin/python
import sys

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.util import login_required

import gdata.service
import gdata.auth
import gdata.alt.appengine
import gdata.calendar
import gdata.calendar.service

from settings import template_path

_DEBUG = True

class Event(db.Model):
  title = db.StringProperty(required=True)
  description = db.TextProperty()
  time = db.DateTimeProperty()
  location = db.TextProperty()
  creator = db.UserProperty()
  edit_link = db.TextProperty()
  gcal_event_link = db.TextProperty()
  gcal_event_xml = db.TextProperty()


class Attendee(db.Model):
  email = db.StringProperty()
  event = db.ReferenceProperty(Event)

    
class EventForm(djangoforms.ModelForm):
    class Meta:
        model = Event
        exclude = ['creator']
        
class CalendarHandler(webapp.RequestHandler):
    def __init__(self):
        super(CalendarHandler, self).__init__()
        self.calendar_client = gdata.calendar.service.CalendarService()
        gdata.alt.appengine.run_on_appengine(self.calendar_client)
    
class Events(CalendarHandler):
    """list blogs"""
    def get(self):
        content = {
            'events' : db.GqlQuery("SELECT * from Event").get(),
            'event_form' : EventForm(),
        }
        self.response.out.write(template.render(template_path + 'calendar/events.html', content))
        
    """create blog"""
    def post(self):
        content = {
            'event_form' : EventForm(request.POST or None),
        }

        if content['event_form'].is_valid():
            event = content['event_form'].save(commit=False)
            event.creator = users.get_current_user()
            event.put()
        self.redirect('/calendar')
        
    """update blog"""
    def put(self):
        self.response.out.write(template.render(template_path + 'blog/b'))
        
    """delete blog"""
    def delete(self):
        pass

class EventEdit(CalendarHandler):
    pass

class EventDelete(CalendarHandler):
    pass

class EventCreate(CalendarHandler):
    def get(self):
        content = {
            'event_form' : EventForm(),
        }
        self.response.out.write(template.render(template_path + 'calendar/events/create.html'), content)
        
    def post(self):
        content = {
            'event_form' : EventForm(request.POST or None),
        }
        
        if content['event_form'].is_valid():
            event = content['event_form'].save(commit=False)
            event.creator = users.get_current_user()
            event.put()
            self.redirect('/calendar/events')
        self.response.out.write(template.render(template_path + 'calendar/events/create.html'), content)

_URLS = [
    ('/calendar/events', Events),
    ('/calendar/events/edit', EventEdit),
    ('/calendar/events/delete', EventDelete),
    ('/calendar/events/create', EventCreate),
]

def main(argv):
    application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
    run_wsgi_app(application)
    
if __name__ == '__main__':
    main(sys.argv)
