#!/usr/bin/env python
from settings import template_path
import sys
import mimetypes
import os
import re
import markdown
import datetime
import time
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import simplejson
from pymntos_utilities import SlugProperty, strip_html_tags
import appengine_admin

_DEBUG = False


class Tweet(db.Model):
    body = db.TextProperty()
    author = db.StringProperty()
    timestamp = db.DateTimeProperty()
    tweet_id = db.StringProperty()

    @property
    def parsed(self):
        hyperlinks = re.sub(
            r'(http://[A-Za-z0-9_\-\./]+)',
            r'<a href="\1">\1</a>',
            self.body)
        at_replies = re.sub(
            r'\@([A-Za-z0-9_\-]+)',
            r'<a href="http://twitter.com/\1">@\1</a>',
            hyperlinks)
        hashtags = re.sub(
            r'\#([A-Za-z0-9_\-]+)',
            r'<a href="http://search.twitter.com/search?q=%23\1">#\1</a>',
            at_replies)
        return unicode(hashtags)


class Meeting(db.Model):
    date = db.DateTimeProperty()
    agenda = db.TextProperty()

    @property
    def rendered_agenda(self):
        return markdown.markdown(self.agenda)


class Attendee(db.Model):
    meeting = db.ReferenceProperty(Meeting, collection_name="attendees")
    name = db.StringProperty()
    vegetarian = db.BooleanProperty()


class BlogPost(db.Model):
    title = db.StringProperty()
    body = db.TextProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)
    slug = SlugProperty(title)

    @property
    def rendered_body(self):
        return markdown.markdown(self.body)

    @property
    def rendered_excerpt(self):
        body = self.body
        # Remove carriage returns in the event Windows inserts them.
        body = body.replace("\r", '')
        excerpt = re.split("\n+", body)[0]
        return markdown.markdown(excerpt)

    def __unicode__(self):
        return self.title

    @property
    def permalink(self):
        return '/blog/%s/' % self.slug


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

    def __unicode__(self):
        return self.title


#### Handlers ####
def render(template_name, **kw):
    kw['sidebar'] = Page.by_name('/sidebar/').rendered_body
    user = users.get_current_user()
    kw['user'] = user
    if kw['user']:
        kw['logout_url'] = users.create_logout_url('/')
    else:
        kw['login_url'] = users.create_login_url('/')
    return template.render(template_path + template_name, kw)


class BlogIndex(webapp.RequestHandler):
    def get(self):
        posts = BlogPost.all().order('-timestamp')
        paginator = Paginator(posts, 10)

        try:
            raw_page = int(self.request.GET['page'])
        except:
            raw_page = 1

        try:
            page = paginator.page(raw_page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results.
            page = paginator.page(paginator.num_pages)

        if page.has_previous():
            previous_page = page.previous_page_number()
        else:
            previous_page = False

        if page.has_next():
            next_page = page.next_page_number()
        else:
            next_page = False

        self.response.out.write(render(
            'blog_index.html',
            title="Blog",
            posts=page,
            pages=paginator.num_pages,
            previous_page=previous_page,
            next_page=next_page))
        return


class BlogDetail(webapp.RequestHandler):
    def get(self):
        slug = self.request.path_info[:-1].split('/')[-1]
        post = BlogPost.all().filter('slug =', slug)[0]
        self.response.out.write(render(
            'blog_detail.html',
            post=post,
            title=post.title))
        #except:
        #    self.response.set_status(404)
        #    self.response.out.write(render(
        #        '404.html',
        #        title="Page Not Found"))
        return


class LandingPage(webapp.RequestHandler):
    """Landing Page, since it's different from other pages."""
    def get(self):
        blog_posts = BlogPost.all().order('-timestamp').fetch(limit=5)
        try:
            meeting = Meeting.all().order('-date').fetch(limit=1)[0]
        except:
            meeting = None

        tweets = Tweet.all().order('-timestamp').fetch(limit=10)

        self.response.out.write(render(
            'landing.html',
            title='PyMNtos: Twin Cities Python User Group',
            blog_posts=blog_posts,
            meeting=meeting,
            tweets=tweets))
        return


class NextMeeting(webapp.RequestHandler):
    def get(self):
        success_message = False
        failure_message = False
        try:
            meeting = Meeting.all().order('-date').fetch(limit=1)[0]

            if 'success' in self.request.GET:
                success_message = "Thank you for RSVPing."

            if 'failure' in self.request.GET:
                failure_message = "Something went wrong.  Please try again."

            try:
                # TODO: FIX THIS
                # I don't understand why I can't typecast meeting.attendees
                # to a list and call len(), but that appears to fail for
                # reasons I haven't uncovered yet.
                attendees = 0
                vegetarians = 0
                for attendee in meeting.attendees:
                    attendees += 1
                    if attendee.vegetarian:
                        vegetarians += 1
            except:
                attendees = False
                vegetarians = False
        except:
            meeting = False
            attendees = False
            vegetarians = False
        self.response.out.write(render(
            'meeting.html',
            title='Next Meeting',
            meeting=meeting,
            message=success_message,
            error=failure_message,
            attendees=attendees,
            vegetarians=vegetarians))
        return

    def post(self):
        meeting_key = self.request.POST['meeting']
        meeting = db.get(meeting_key)

        name = strip_html_tags(self.request.POST['name'])
        if len(name) > 0:
            attendee = Attendee()
            attendee.name = name

            if ('vegetarian' in self.request.POST and
                    self.request.POST['vegetarian'] == 'on'):
                attendee.vegetarian = True
            else:
                attendee.vegetarian = False
            attendee.meeting = meeting
            attendee.put()
            self.redirect(self.request.path_info + '?success')
        else:
            self.redirect(self.request.path_info + '?failure')
        return


class MeetingList(webapp.RequestHandler):
    def get(self):
        # TODO: Set up a pager for this.  We'll only have 12
        # meetings per year, though, so there's no hurry.
        meetings = Meeting.all().order('-date')
        self.response.out.write(render(
            'meeting_list.html',
            title="All Meetings",
            meetings=meetings))


class Wiki(webapp.RequestHandler):
    """Wiki"""
    def get(self):
        page_name = self.request.path_info

        # Append trailing slashes to make URLs look pretty
        if ('.' not in self.request.path_info and
                self.request.path_info[-1] != '/'):
            self.redirect(self.request.path_info + '/')
            return

        page = Page.by_name(page_name)
        if not page.exists or 'edit' in self.request.GET:
            if users.is_current_user_admin():
                self.response.out.write(render(
                    'edit.html',
                    page=page,
                    title='Edit %s' % page_name))
            else:
                if 'edit' in self.request.GET and not users.get_current_user():
                    # Redirect to login page if not logged in.
                    self.redirect(users.create_login_url(page_name + '?edit'))
                else:
                    # 404
                    self.response.set_status(404)
                    self.response.out.write(render(
                        '404.html',
                        title="Page Not Found"))
            return
        extension = os.path.splitext(page_name)[1]
        if extension:
            type, encoding = mimetypes.guess_type(extension)
            self.response.headers.add_header('Content-Type', type)
            self.response.out.write(page.body)
            return
        self.response.out.write(render(
            'view.html',
            page=page,
            title=page.title))

    def post(self):
        page = Page.by_name(self.request.path_info)
        page.title = self.request.POST['title']
        page.body = self.request.POST['body']
        page.put()
        self.redirect(self.request.url)


#### Cron Jobs ####
class TwitterFeed(webapp.RequestHandler):
    def get(self):
        feed = urlfetch.fetch(
            'http://search.twitter.com/search.json?q=%23pymntos',
        )
        # Fail silently, since this will run from cron.  We'll get just
        # our updates the next time around if something goes wrong.
        if feed.status_code == 200:
            json = feed.content
            json = simplejson.loads(json)
            tweets = json['results']

            # TODO: This is inefficient, since it makes many calls to
            # the datastore.  Make it go faster.
            for tweet in tweets:
                try:
                    Tweet.all().filter('tweet_id =', str(tweet['id']))[0]
                except IndexError:
                    # Tweet does not exist.  Add it.
                    t = Tweet()
                    t.tweet_id = str(tweet['id'])
                    t.body = tweet['text']
                    t.author = tweet['from_user']
                    ts = tweet['created_at']
                    ts = time.strptime(ts, '%a, %d %b %Y %H:%M:%S +0000')
                    ts = datetime.datetime(ts[0], ts[1], ts[2], ts[3], ts[4],
                                           ts[5])
                    t.timestamp = ts
                    t.put()


#### Admin Stuff ####
class AdminPage(appengine_admin.ModelAdmin):
    model = Page
    listFields = ('title', 'path')
#    editFields = ('title', 'content')
#    readonlyFields = ('whencreated', 'whenupdated')


class AdminBlogPost(appengine_admin.ModelAdmin):
    model = BlogPost
    listFields = ('title', 'timestamp')
    editFields = ('title', 'body')


class AdminMeeting(appengine_admin.ModelAdmin):
    model = Meeting
    listFields = ('date',)
    editFields = ('date', 'agenda')


appengine_admin.register(AdminPage, AdminBlogPost, AdminMeeting)

_URLS = [
    (r'/', LandingPage),
    (r'^/blog/', BlogIndex),
    (r'^/blog/.+/', BlogDetail),
    (r'^/meetings/', NextMeeting),
#    (r'^/meetings/all/', MeetingList),
    (r'^/cron/twitter/', TwitterFeed),
    (r'^(/admin)(.*)$', appengine_admin.Admin),
    ('.*', Wiki),
]


def main(argv):
    application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
    run_wsgi_app(application)


if __name__ == '__main__':
    main(sys.argv)
