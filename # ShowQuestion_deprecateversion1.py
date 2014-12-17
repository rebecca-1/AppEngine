"""
Final project for course Open Soure II
"""

import os
import cgi
import urllib
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
import webapp2

DEFAULT_QUESTION_NAME = 'default_question'

def question_key(question_name=DEFAULT_QUESTION_NAME):
    """
    Constructs a Datastore key for a Question entity with question_name
    """
    return ndb.Key('Ask_Question', question_name)

class Votes(ndb.Model):
    voteauthor = ndb.UserProperty()
    voteup = ndb.BooleanProperty()
    votedown = ndb.BooleanProperty()

class Answers(ndb.Model):
    answerauthor = ndb.UserProperty()
    answercontent = ndb.StringProperty(indexed=False)
    answersupplinkuri = ndb.StringProperty(indexed=False,repeated=True)
    numvote_up = ndb.IntegerProperty(default=0)
    numvote_down = ndb.IntegerProperty(default=0)
    votes = ndb.LocalStructuredProperty(Votes,repeated=True)
    
class Question(ndb.Model):
    """
    Models an individual question entry.
    """
    questionauthor = ndb.UserProperty()
    questioncontent = ndb.StringProperty(indexed=False)
    # permalinkuri  = ndb.StringProperty(indexed=False)
    # questionsupplinkuri = ndb.StringProperty(indexed=False,repeated=True) # allow multiple supplmentary links
    # tags   = ndb.StringProperty(indexed=False,repeated=True) # allow multiple tags
    date_creation = ndb.DateTimeProperty(auto_now_add=True)
    date_modification = ndb.DateTimeProperty(auto_now_add=True)
    # answers = ndb.LocalStructuredProperty(Answers, repeated=True)
                  
    
ASKQUESTION_TEMPLATE = """\
<html>
  <body>
    <form action="/Ask?%s" method="post">
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="post question"></div>
    </form>
    <hr>
    <a href="%s">%s</a>
  </body>
</html>
"""    

class Ask_Question(webapp2.RequestHandler):
    def post(self):
        self.response.write('debug infor for post in Ask_Question')
        
        question_name = DEFAULT_QUESTION_NAME
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.questionauthor = users.get_current_user()

        question.questioncontent = self.request.get('content')
        question.put()

        # query_params = {'question_name': question_name}
        # self.redirect('/?' + urllib.urlencode(query_params))
        self.redirect('/')  

        
class MainPage(webapp2.RequestHandler):
    def get(self):
        # self.response.write('debug infor')
        
        question_name = DEFAULT_QUESTION_NAME
        questions_query = Question.query(ancestor=question_key(question_name)).order(-Question.date_modification)
        #  get top 10 questions sorted by the last modification datetime
        questions = questions_query.fetch(10)
                
        self.response.write('there are {} questions so far'.format(len(questions)))
        
        if(not questions is None):
            for indquestion in questions:
                self.response.write('<blockquote>%s</blockquote>' % cgi.escape(indquestion.questionauthor))
                self.response.write('<blockquote>%s</blockquote>' % cgi.escape(indquestion.questioncontent))

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        
        askquestion_query_params = urllib.urlencode({'question_name': question_name})
        self.response.write(ASKQUESTION_TEMPLATE % (askquestion_query_params, url, url_linktext))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/Ask',Ask_Question),
], debug=True)

    
