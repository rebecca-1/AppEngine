
import os
import logging
import urllib
from google.appengine.api import memcache, users
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
import webapp2

NUMQUESTIONPERPAGE = 10
SHORTCONTENTLEN = 10 # 500
DEFAULT_AUTHOR = "DEFAULT_AUTHOR" # after careful implementation, this should NEVER be used!

##################################################################################################################################################

def answerIdToKey(answerid,questionid):
    return ndb.Key('Answer', int(answerid), parent=ndb.Key('Question', int(questionid)))
    
def questionIdToKey(questionid):
    return ndb.Key('Question', int(questionid))

class Answer(ndb.Model):
    # key = ndb.KeyProperty()
    author = ndb.UserProperty()
    content = ndb.TextProperty(indexed=False)
    date_create = ndb.DateTimeProperty(auto_now_add=True)
    date_modification = ndb.DateTimeProperty(auto_now=True)
    #
    votedauthors = ndb.StringProperty(indexed=False,repeated=True)
    votedauthorsvotes = ndb.IntegerProperty(repeated=True)
    numvoteup = ndb.IntegerProperty(default=0)
    numvotedown = ndb.IntegerProperty(default=0)
    numvote = ndb.ComputedProperty(lambda self: self.numvoteup - self.numvotedown)

class Question(ndb.Model):
    # key = ndb.KeyProperty()
    author = ndb.UserProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty(indexed=False) 
    shortcontent = ndb.TextProperty(indexed=False)
    date_create = ndb.DateTimeProperty(auto_now_add=True)
    date_modification = ndb.DateTimeProperty(auto_now=True)
    tags = ndb.StringProperty(repeated=True)
    #
    votedauthors = ndb.StringProperty(indexed=False,repeated=True)
    votedauthorsvotes = ndb.IntegerProperty(repeated=True)
    numvoteup = ndb.IntegerProperty(default=0)
    numvotedown = ndb.IntegerProperty(default=0)
    numvote = ndb.ComputedProperty(lambda self: self.numvoteup - self.numvotedown)

# Remove whatever is lingering around in the database
ndb.delete_multi(Answer.query().fetch(keys_only=True))	 	
ndb.delete_multi(Question.query().fetch(keys_only=True))

##################################################################################################################################################

LOGIN_TEMPLATE = """\
</html>
  </body>
      <br>
      <a href="%s">%s</a>
  </body>
</html>
"""

HOMEBUTTON_TEMPLATE = """\
<html>
  <body>
    <form action="/home" method="post">
      <div><input type="submit" value="Back to question lists" />
    </form>
  </body>
</html>
"""

ASKQUESTIONBUTTON_TEMPLATE = """\
<html>
  <body>
    <br> 
    <br>
    <form action="/question" method="get">
      <div><input type="submit" value="Ask a question" />
    </form>
  </body>
</html>
"""

QUESTION_TEMPLATE = """\
<html>
  <body>
    <form action="/question" method="post">
      <label>Title</label>
      <div><textarea name="title" rows="1" cols="60"></textarea></div>
      <label>Question Content</label>
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <label>Tags: optional, please separate multiple tags with ';'</label>
      <div><textarea name="tags",rows="1",cols="60"></textarea></div>
      <div><input type="submit" value="Post the question"></div>
    </form>
  </body>
</html>
"""

ANSWERQUESTIONBUTTON_TEMPLATE = """\
<html>
  <body>
    <br>
    <form action="/answer" method="get">
      <input type="hidden" name="questionid" value="%s">
      <div><input type="submit" value="Answer the question" />
    </form>
  </body>
</html>
"""

ANSWER_TEMPLATE = """\
<html>
  <body>
    <form action="/answer" method="post">
      <input type="hidden" name="questionid" value="%s">
      <label>Your answer</label>
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="Post the answer"></div>
    </form>
  </body>
</html>
"""

class HomeHandler(webapp2.RequestHandler):        
    def post(self):
        self.redirect('/')    
        
class QuestionAnswerList(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        questionid = self.request.get('questionid')
        question_key = questionIdToKey(questionid)
        # logging.info('questionkey in QuestionAnswerList is {}'.format(question_key))
        question = question_key.get()
        # logging.info('question vote is {}'.format(question.numvote))
        
        # no restriction on number of answers to display
        answers = Answer.query(ancestor=question_key).order(-Answer.date_modification).fetch()
        # logging.info('len(answers) in QuestionAnswerList is {}'.format(len(answers)))

        memcache.add('answers', answers)
        context = {
            'user':         user,
            'login':        users.create_login_url(self.request.uri),
            'logout':       users.create_logout_url(self.request.uri),
            'question':     question,
            # 'questionid':   questionid,  => directly use question.key.id instead passing in
            'answers':      answers,
        }   
        tmpl = os.path.join(os.path.dirname(__file__), 'questionanswer.html')
        self.response.out.write(template.render(tmpl, context)) 
        
        if users.get_current_user():
            self.response.write(ANSWERQUESTIONBUTTON_TEMPLATE % (questionid))
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Answer the question" # which will lead to login page
            self.response.write(LOGIN_TEMPLATE % (url, url_linktext))                                     

        self.response.write(HOMEBUTTON_TEMPLATE)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'                      
        self.response.write(LOGIN_TEMPLATE % (url, url_linktext)) 


# Note: duplication of codes between QuestionList and MainHandler,
#       can use function call to simplify
class QuestionList(webapp2.RequestHandler): # Handle requests like /summarylist?cursor=1234567
    def get(self):
        user = users.get_current_user()
        curs = Cursor(urlsafe=self.request.get('cursor'))
        questions, next_curs, more = Question.query().\
                                          order(-Question.date_modification).\
                                          fetch_page(NUMQUESTIONPERPAGE, start_cursor=curs)
        # deprecated: questions = questions_query.fetch(NUMQUESTIONPERPAGE)
            
        # display all questions:        
        memcache.add('questions', questions)
        context = {
            'user':      user,
            'login':     users.create_login_url(self.request.uri),
            'logout':    users.create_logout_url(self.request.uri),
            'questions': questions,
        }   
        tmpl = os.path.join(os.path.dirname(__file__), 'allquestions.html')
        self.response.out.write(template.render(tmpl, context))        
    
        if more and next_curs:
            self.response.out.write('<a href="/summarylist?cursor=%s">Eariler questions</a>' %
                                  next_curs.urlsafe())
                                 
        # provide a button which goes to ask question page
        if users.get_current_user():
            self.response.write(ASKQUESTIONBUTTON_TEMPLATE)
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Ask a question" # which will lead to login page
            self.response.write(LOGIN_TEMPLATE % (url, url_linktext))                                 
        


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('debug infor for get in mainHandler <hr>')
        user = users.get_current_user()
        self.response.write('user is {} <hr>'.format(user))
        
        self.response.out.write('<html><body>')
        curs = Cursor(urlsafe=self.request.get('cursor'))
        questions, next_curs, more = Question.query().\
                                          order(-Question.date_modification).\
                                          fetch_page(NUMQUESTIONPERPAGE, start_cursor=curs)

        # display all questions:        
        memcache.add('questions', questions)
        context = {
            'user':      user,
            'questions': questions,
            'login':     users.create_login_url(self.request.uri),
            'logout':    users.create_logout_url(self.request.uri),
        }   
        tmpl = os.path.join(os.path.dirname(__file__), 'allquestions.html')
        self.response.out.write(template.render(tmpl, context))   
                                
        if more and next_curs:
          self.response.out.write('<a href="/summarylist?cursor=%s">Eariler questions</a>' %
                                  next_curs.urlsafe())
                                  
        if users.get_current_user():
            self.response.write(ASKQUESTIONBUTTON_TEMPLATE)
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Ask a question" # which will lead to login page
            self.response.write(LOGIN_TEMPLATE % (url, url_linktext))                                     

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'                      
        self.response.write(LOGIN_TEMPLATE % (url, url_linktext))
        
    def post(self):
        self.response.write('debug infor for post in mainHandler <hr>')
        pass


class VoteQuestionHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        question_key = questionIdToKey(questionid)
        question = question_key.get()       
        
        #logging.info('VOTEH: got question')
        #logging.info('author {}'.format(question.author))
        #logging.info('title {}'.format(question.title))
        #logging.info('content {}'.format(question.content))
        #logging.info('tags {}'.format(question.tags))
        #logging.info('votedauthors {}'.format(question.votedauthors))
        #logging.info('votedauthorsvotes {}'.format(question.votedauthorsvotes))
        #logging.info('numvoteup {}'.format(question.numvoteup))
        #logging.info('numvotedown {}'.format(question.numvotedown))
        #logging.info('numvote {}'.format(question.numvote))
        
        # search through vote authors to make sure no multiple voting from same author!
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'                      
            self.response.write(LOGIN_TEMPLATE % (url, url_linktext)) 
            return
            
        # logging.info('currentauthor is {}'.format(currentauthor))            
            
        thisvote = self.request.get('votequestion')        
        if(thisvote=="Up"):
            currentvote = 1
        elif(thisvote=="Down"):
            currentvote = -1
        else:
            raise Exception('error in VoteQuestionHandler')
               
        assert(len(question.votedauthors)==len(question.votedauthorsvotes))
        counter = 0
        for prevauthor,prevvote in zip(question.votedauthors,question.votedauthorsvotes):
            # logging.info('inside loop')
            # logging.info('prevauthor is {}, currentauthor is {}'.format(prevauthor,currentauthor))
            # logging.info('prevauthor == currentauthor is {}'.format(str(prevauthor)==str(currentauthor)))
            if(str(prevauthor)==str(currentauthor)):
                # logging.info('indeed prevauthor == currentauthor is {}'.format(str(prevauthor)==str(currentauthor)))
                # logging.info('prevvote is {}, currentvote is {}'.format(prevvote,currentvote))
                # logging.info('prevvote == currentvote is {}'.format(int(prevvote)==int(currentvote)))
                if(int(prevvote)==int(currentvote)):
                    # logging.info('indeed prevvote == currentvote is {}'.format(int(prevvote)==int(currentvote)))
                    question.put()
                    self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
                    return
                else:
                    question.votedauthorsvotes[counter] = -1*question.votedauthorsvotes[counter]
                    question.numvoteup += 2*(currentvote>0)*currentvote
                    question.numvotedown -= 2*(currentvote<0)*currentvote
                    question.put()
                    self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
                    return
            counter+=1
               
        # if has not returned yet - new author is tring to vote:            
        question.votedauthors.append(currentauthor.email())
        question.votedauthorsvotes.append(currentvote)
        question.numvoteup += (currentvote>0)*currentvote
        question.numvotedown -= (currentvote<0)*currentvote
        
        #logging.info('VOTEH: updated question')
        #logging.info('author {}'.format(question.author))
        #logging.info('title {}'.format(question.title))
        #logging.info('content {}'.format(question.content))
        #logging.info('tags {}'.format(question.tags))
        #logging.info('votedauthors {}'.format(question.votedauthors))
        #logging.info('votedauthorsvotes {}'.format(question.votedauthorsvotes))
        #logging.info('numvoteup {}'.format(question.numvoteup))
        #logging.info('numvotedown {}'.format(question.numvotedown))
        #logging.info('numvote {}'.format(question.numvote))
        
        question.put()
        
        # logging.info('in VoteQuestionHandler, ready to redirect!')
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))


class VoteAnswerHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
        answer = answer_key.get()       
 
        #logging.info('VOTEAH: got answer')
        #logging.info('author {}'.format(answer.author))
        #logging.info('content {}'.format(answer.content))
        #logging.info('votedauthors {}'.format(answer.votedauthors))
        #logging.info('votedauthorsvotes {}'.format(answer.votedauthorsvotes))
        #logging.info('numvoteup {}'.format(answer.numvoteup))
        #logging.info('numvotedown {}'.format(answer.numvotedown))
        #logging.info('numvote {}'.format(answer.numvote))
        
        # search through vote authors to make sure no multiple voting from same author!
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            currentauthor = DEFAULT_AUTHOR
            
        # logging.info('currentauthor is {}'.format(currentauthor))            
            
        thisvote = self.request.get('voteanswer')
        if(thisvote=="Up"):
            currentvote = 1
        elif(thisvote=="Down"):
            currentvote = -1
        else:
            raise Exception('error in VoteAnswerHandler')
               
        assert(len(answer.votedauthors)==len(answer.votedauthorsvotes))
        counter = 0
        for prevauthor,prevvote in zip(answer.votedauthors,answer.votedauthorsvotes):
            # logging.info('inside loop')
            # logging.info('prevauthor is {}, currentauthor is {}'.format(prevauthor,currentauthor))
            # logging.info('prevauthor == currentauthor is {}'.format(str(prevauthor)==str(currentauthor)))
            if(str(prevauthor)==str(currentauthor)):
                # logging.info('indeed prevauthor == currentauthor is {}'.format(str(prevauthor)==str(currentauthor)))
                # logging.info('prevvote is {}, currentvote is {}'.format(prevvote,currentvote))
                # logging.info('prevvote == currentvote is {}'.format(int(prevvote)==int(currentvote)))
                if(int(prevvote)==int(currentvote)):
                    # logging.info('indeed prevvote == currentvote is {}'.format(int(prevvote)==int(currentvote)))
                    answer.put()
                    self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
                    return
                else:
                    answer.votedauthorsvotes[counter] = -1*answer.votedauthorsvotes[counter]
                    answer.numvoteup += 2*(currentvote>0)*currentvote
                    answer.numvotedown -= 2*(currentvote<0)*currentvote
                    answer.put()
                    self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
                    return
            counter+=1
               
        # if has not returned yet - new author is tring to vote:            
        answer.votedauthors.append(currentauthor.email())
        answer.votedauthorsvotes.append(currentvote)
        answer.numvoteup += (currentvote>0)*currentvote
        answer.numvotedown -= (currentvote<0)*currentvote
        
        #logging.info('VOTEAH: got answer - updated')
        #logging.info('author {}'.format(answer.author))
        #logging.info('content {}'.format(answer.content))
        #logging.info('votedauthors {}'.format(answer.votedauthors))
        #logging.info('votedauthorsvotes {}'.format(answer.votedauthorsvotes))
        #logging.info('numvoteup {}'.format(answer.numvoteup))
        #logging.info('numvotedown {}'.format(answer.numvotedown))
        #logging.info('numvote {}'.format(answer.numvote))
        
        answer.put()
        # logging.info('in VoteAnswerHandler, ready to redirect!')
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))


class EditQuestionHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        question_key = questionIdToKey(questionid)
        question = question_key.get()       
        
        logging.info('EditQ: got question')
        logging.info('author {}'.format(question.author))
        logging.info('title {}'.format(question.title))
        logging.info('content {}'.format(question.content))
        logging.info('shortcontent {}'.format(question.shortcontent))
        logging.info('date_create {}'.format(question.date_create))
        logging.info('date_modification {}'.format(question.date_modification))
        logging.info('tags {}'.format(question.tags))

        # search through vote authors to make sure no multiple voting from same author!
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            currentauthor = DEFAULT_AUTHOR
            
        logging.info('currentauthor is {}'.format(currentauthor))
        
        # not allowed to modify the question is the author is not the author who asked the question            
        if(str(question.author)!=str(currentauthor)):
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            return    
        else:
            # same author:

                
            #@@@@@                
                
                
            logging.info('EditQ: updated question')
            logging.info('author {}'.format(question.author))
            logging.info('title {}'.format(question.title))
            logging.info('content {}'.format(question.content))
            logging.info('shortcontent {}'.format(question.shortcontent))
            logging.info('date_create {}'.format(question.date_create))
            logging.info('date_modification {}'.format(question.date_modification))
            logging.info('tags {}'.format(question.tags))
    
            question.put()
            
            logging.info('in EditQuestionHandler, ready to redirect!')
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))


class EditAnswerHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
        answer = answer_key.get()       
 
        logging.info('EditAnswerH: got answer')
        logging.info('author {}'.format(answer.author))
        logging.info('content {}'.format(answer.content))
        logging.info('date_create {}'.format(answer.date_create))
        logging.info('date_modification {}'.format(answer.date_modification))
    
        # search through vote authors to make sure no multiple voting from same author!
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            currentauthor = DEFAULT_AUTHOR
            
        logging.info('currentauthor is {}'.format(currentauthor))            
            
        # not allowed to modify the question is the author is not the author who asked the question            
        if(str(answer.author)!=str(currentauthor)):
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            return    
        else:
            # same author:

            #@@@@@

            logging.info('VOTEAH: got answer - updated')
            logging.info('author {}'.format(answer.author))
            logging.info('content {}'.format(answer.content))
            logging.info('date_create {}'.format(answer.date_create))
            logging.info('date_modification {}'.format(answer.date_modification))
            
        answer.put()
        logging.info('in VoteAnswerHandler, ready to redirect!')
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))



class AnswerHandler(webapp2.RequestHandler):
    """
    """
    def get(self):
        questionid = self.request.get('questionid')
        self.response.write(ANSWER_TEMPLATE % (questionid))
        # debugging: self.response.write('questionid is {}'.format(questionid))
    
    def post(self):
        questionid = self.request.get('questionid')        
        # logging.info('questionid is {}'.format(questionid))  
        question_key = questionIdToKey(questionid)
        # logging.info('questionkey is {}'.format(question_key))
        answer = Answer(parent=question_key)
        if users.get_current_user():
            answer.author = users.get_current_user()
        answer.content = self.request.get('content')
        # create corresponding vote object
        answer.votedauthors = []
        answer.votedauthorsvotes = []
        answer.numvoteup = 0
        answer.numvotedown = 0
        # only keep valid answers!
        # logging.info('content of the answer is {}'.format(answer.content))
        if(not answer.content is None):
            answer.put()
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
        # or can just back to home self.redirect('/')        
  
class QuestionHandler(webapp2.RequestHandler):
    """
    """
    def get(self):
        # self.response.write('debug infor for get in QuestionHandler <hr>')
        self.response.write(QUESTION_TEMPLATE)
    def post(self):
        # self.response.write('debug infor for post in QuestionHandler <hr>')
        question = Question()
        if users.get_current_user():
            question.author = users.get_current_user()
        question.title = self.request.get('title')
        question.content = self.request.get('content')
        question.shortcontent = self.request.get('content')[:SHORTCONTENTLEN]
        temptags = self.request.get('tags')
        if((not temptags is None)and(not temptags=='')):
            question.tags = temptags.split(";")
            
        # create the corresponding vote for this question:
        question.votedauthors = []
        question.votedauthorsvotes = []
        question.numvoteup = 0
        question.numvotedown = 0
        # only keep valid questions!
        if(not ((question.title is None)and(question.content is None))):
            question.put()
        self.redirect('/')
        # Note: to see the most recent question, need to refresh the webpage
                
                             
application = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        ('/home',HomeHandler),
        ('/question', QuestionHandler),
        ('/answer', AnswerHandler),
        ('/votequestion', VoteQuestionHandler),
        ('/editquestion',EditQuestionHandler),
        ('/voteanswer', VoteAnswerHandler),
        ('/editanswer',EditAnswerHandler),
        ('/summarylist.*',QuestionList),
        ('/detaillist.*',QuestionAnswerList),
    ], debug=True)
    
        