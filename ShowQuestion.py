
import os
# import logging # used for debugging
import urllib
from google.appengine.api import memcache, users
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
import webapp2
from google.appengine.api import mail
from google.appengine.api import images
# import PyRSS2Gen

NUMQUESTIONPERPAGE = 10
SHORTCONTENTLEN = 500
# DEFAULT_AUTHOR = "DEFAULT_AUTHOR" # after careful implementation, this should NEVER be used!

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
    # Note: when auto_now_add is set to True, the time is set to the current time the first time the
    #       model instance is stored in the datastore, unless the property has already been assigned a value
    date_modification = ndb.DateTimeProperty(auto_now=True) 
    # Note: when auto_now is set to True, the time is set to the current time whenever the 
    #       model instance is stored in the datastore, overwriting the property's previous value
    votedauthors = ndb.StringProperty(indexed=False,repeated=True)
    votedauthorsvotes = ndb.IntegerProperty(repeated=True)
    numvoteup = ndb.IntegerProperty(default=0)
    numvotedown = ndb.IntegerProperty(default=0)
    numvote = ndb.ComputedProperty(lambda self: self.numvoteup - self.numvotedown)
    #
    image = ndb.BlobKeyProperty(indexed=False)
    imageurl = ndb.StringProperty()

class Question(ndb.Model):
    # key = ndb.KeyProperty()
    author = ndb.UserProperty()
    getemail = ndb.BooleanProperty()
    title = ndb.StringProperty(indexed=False)
    content = ndb.TextProperty(indexed=False) 
    shortcontent = ndb.TextProperty(indexed=False)
    date_create = ndb.DateTimeProperty(auto_now_add=True)
    date_modification = ndb.DateTimeProperty(auto_now=True)
    tags = ndb.StringProperty(repeated=True)
    unparsedtags = ndb.StringProperty(indexed=False)
    #
    votedauthors = ndb.StringProperty(indexed=False,repeated=True)
    votedauthorsvotes = ndb.IntegerProperty(repeated=True)
    numvoteup = ndb.IntegerProperty(default=0)
    numvotedown = ndb.IntegerProperty(default=0)
    numvote = ndb.ComputedProperty(lambda self: self.numvoteup - self.numvotedown)
    #
    image = ndb.BlobKeyProperty(indexed=False)
    imageurl = ndb.StringProperty()
    
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


SEARCHTAG_TEMPLATE = """\
<html>
  <body>
    <form action="/" method="post">
      <div><textarea name="querytag" rows="1" cols="20"></textarea></div>  
      <div><input type="submit" value="Search questions with tag" />
    </form>
  </body>
</html>
"""

SEARCHWORD_TEMPLATE = """\
<html>
  <body>
    <form action="/" method="post">
      <div><textarea name="queryword" rows="1" cols="20"></textarea></div>  
      <div><input type="submit" value="Search questions and answers with key word" />
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
    <form action="/question" method="post" enctype="multipart/form-data">
      <label>Title</label>
      <div><textarea name="title" rows="1" cols="60"></textarea></div>
      <label>Question Content</label>
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <br>
      <label>Tags: optional, please separate multiple tags with ';'</label>
      <div><textarea name="tags",rows="1",cols="60"></textarea></div>
      <input type="checkbox" name="emailanswer" value="emailanswer">Receive answers via email
      <br>
      <input type="checkbox" name="ifuploadimage" value="ifuploadimage">Upload image after sumbit question
      <br>
      <div><input type="submit" value="Post the question"></div>
    </form>
  </body>
</html>
"""


QUESTIONIMAGE_TEMPLATE = """\
<html>
  <body>
    <form action="%s" method="post" enctype="multipart/form-data">  
      <input type="hidden" name="questionid" value="%s">  
      <label>Upload image</label>
      <input type = "file" name = "image">
      <div><input type="submit" name="submit" value="Upload image"></div>
    </form>
  </body>
</html>
"""


EDITQUESTION_TEMPLATE = """\
<html>
  <body>
    <form action="/editquestion" method="post">
      <input type="hidden" name="questionid" value="%s">  
      <label>Title</label>
      <div><textarea name="title" rows="1" cols="60">
           %s     
           </textarea></div>
      <label>Question Content</label>
      <div><textarea name="content" rows="3" cols="60">
           %s
           </textarea></div>
      <label>Tags: optional, please separate multiple tags with ';'</label>
      <div><textarea name="tags",rows="1",cols="60">
           %s
           </textarea></div>
      <input type="checkbox" name="emailanswer" value="emailanswer">Receive answers via email
      <br>
      <input type="checkbox" name="ifuploadimage" value="ifuploadimage">Upload image after sumbit question      
      <div><input type="submit" value="Edit the question"></div>  
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
      <br>
      <input type="checkbox" name="ifuploadimage" value="ifuploadimage">Upload image after sumbit answer
      <br>
      <div><input type="submit" value="Post the answer"></div>
    </form>
  </body>
</html>
"""


ANSWERIMAGE_TEMPLATE = """\
<html>
  <body>
    <form action="%s" method="post" enctype="multipart/form-data">  
      <input type="hidden" name="questionid" value="%s">  
      <input type="hidden" name="answerid" value="%s"> 
      <label>Upload image</label>
      <input type = "file" name = "image">
      <div><input type="submit" name="submit" value="Upload image"></div>
    </form>
  </body>
</html>
"""


EDITANSWER_TEMPLATE = """\
<html>
  <body>
    <form action="/editanswer" method="post">
      <input type="hidden" name="questionid" value="%s">
      <input type="hidden" name="answerid" value="%s">
      <label>Your answer</label>
      <div><textarea name="content" rows="3" cols="60">
           %s
           </textarea></div>
      <input type="checkbox" name="ifuploadimage" value="ifuploadimage">Upload image after sumbit answer     
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
        if(len(Answer.query(ancestor=question_key).fetch())<1):
            answers = []
        else:
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
        
        self.response.write(SEARCHTAG_TEMPLATE)
        # self.response.write(SEARCHWORD_TEMPLATE)
        
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
        # logging.info('debug infor for post in mainHandler')
        
        querytag = self.request.get('querytag')
        queryword = self.request.get('queryword')
        
        # logging.info('querytag is {}'.format(querytag))
        # logging.info('queryword is {}'.format(queryword))        
        
        #######################################################################
        ##### if the user is querying tag
        if(not querytag is None):
            curs = Cursor(urlsafe=self.request.get('cursor'))
            questions, next_curs, more = Question.query(Question.tags.IN([str(querytag)])).\
                                              order(-Question.date_modification).\
                                              fetch_page(NUMQUESTIONPERPAGE, start_cursor=curs)
        #######################################################################
        ##### if the user is querying word
        elif(not queryword is None):                                              
            curs = Cursor(urlsafe=self.request.get('cursor'))
            # questions = Question.query(Question.contentword.IN([str(queryword)])).\
            #                                   fetch(keys_only=True)
            # answers = Answer.query(Answer.contentword.IN([str(queryword)])).\
            #                                   fetch(keys_only=True)                                                  
                          
            # logging.info('questions with keys_only {}'.format(questions))
            # logging.info('answers with keys_only {}'.format(answers))
                          
            questions, next_curs, more = Question.query().\
                                              order(-Question.date_modification).\
                                              fetch_page(NUMQUESTIONPERPAGE, start_cursor=curs)                                              
        #######################################################################                                              
        else: # if both querytag and queryword are None
            curs = Cursor(urlsafe=self.request.get('cursor'))
            questions, next_curs, more = Question.query().\
                                              order(-Question.date_modification).\
                                              fetch_page(NUMQUESTIONPERPAGE, start_cursor=curs)
            
        self.response.out.write('<html><body>')                                                                                    
        user = users.get_current_user()                                
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
        
        self.response.write(HOMEBUTTON_TEMPLATE)
                

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
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
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
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
            return
            
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
        
        # edit the question
        question.title = self.request.get('title')
        question.content = self.request.get('content')
        question.shortcontent = self.request.get('content')[:SHORTCONTENTLEN]
        temptags = self.request.get('tags')
        question.unparsedtags = self.request.get('tags')
        if((not temptags is None)and(not temptags=='')):
            question.tags = temptags.split(";")      
        ifemailanswer = self.request.get('emailanswer')
        if(str(ifemailanswer)=="emailanswer"):
            question.getemail = True
        else:
            question.getemail = False    
        question.put()
        
        ifuploadimage = self.request.get('ifuploadimage') 
        # logging.info('ifuploadimage is {}'.format(ifuploadimage))
        if(str(ifuploadimage)=="ifuploadimage"):
            upload_url = blobstore.create_upload_url('/edit_question_image')
            self.response.write(QUESTIONIMAGE_TEMPLATE % (upload_url,question.key.id()))
        else:
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))    
            

class EditQuestionHandler_generateform(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        question_key = questionIdToKey(questionid)
        question = question_key.get()       
        
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
            return
            
        # logging.info('currentauthor is {}'.format(currentauthor))
        
        # not allowed to modify the question is the author is not the author who asked the question            
        if(str(question.author)!=str(currentauthor)):
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            return    
        else:
            # same author:
            self.response.write(EDITQUESTION_TEMPLATE % (
                    questionid, question.title, question.content, question.unparsedtags ))
            
            
class RemoveQuestionHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        question_key = questionIdToKey(questionid)
        # question = question_key.get() 
        
        if(users.get_current_user() and users.is_current_user_admin()):
            question_key.delete()
            # after removing the question, go back to home since the question does not exist anymore
            self.redirect('/') 
        else:
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
            return
            

class EditAnswerHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
        answer = answer_key.get()       
        
        #logging.info('EditAnswerH: got answer')
        #logging.info('author {}'.format(answer.author))
        #logging.info('content {}'.format(answer.content))
        #logging.info('date_create {}'.format(answer.date_create))
        #logging.info('date_modification {}'.format(answer.date_modification))
        
        # edit the answer
        
        answer.content = self.request.get('content')
        
        answer.put()
        
        #logging.info('EditAnswerH: got answer - updated')
        #logging.info('author {}'.format(answer.author))
        #logging.info('content {}'.format(answer.content))
        #logging.info('date_create {}'.format(answer.date_create))
        #logging.info('date_modification {}'.format(answer.date_modification))        
        
        question_key = questionIdToKey(questionid)
        question = question_key.get()
        sendemail = question.getemail
        # logging.info('sendemail in EditAnswerHandler is {}'.format(sendemail)) 
        to_addr = question.author.email()
        if((mail.is_email_valid(to_addr)) and (sendemail)):
            message = mail.EmailMessage()
            message.sender = question.author.email()
            message.to = to_addr
            message.body = """
                            Your posted question %s is recently answered: %s
                           """ % (question.title, answer.content)
            message.send()        
          
        ifuploadimage = self.request.get('ifuploadimage') 
        # logging.info('ifuploadimage is {}'.format(ifuploadimage))
        if(str(ifuploadimage)=="ifuploadimage"):
            upload_url = blobstore.create_upload_url('/upload_answer_image')
            self.response.write(ANSWERIMAGE_TEMPLATE % (upload_url,questionid,answer.key.id()))
        else:
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))        
                
          
class EditAnswerHandler_generateform(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
        answer = answer_key.get()       
 
        # search through vote authors to make sure no multiple voting from same author!
        if users.get_current_user():
            currentauthor = users.get_current_user()
        else:
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
            return
            
        # logging.info('currentauthor is {}'.format(currentauthor))            
            
        # not allowed to modify the question is the author is not the author who asked the question            
        if(str(answer.author)!=str(currentauthor)):
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            return    
        else:
            # same author
            self.response.write(EDITANSWER_TEMPLATE % (questionid, answerid, answer.content ))


class RemoveAnswerHandler(webapp2.RequestHandler):
    def post(self):
        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
   
        if(users.get_current_user() and users.is_current_user_admin()):
            answer_key.delete()
            self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))
        else:
            url = users.create_login_url(dest_url='/detaillist?'+  urllib.urlencode({'questionid': questionid}))
            self.redirect(url)
            return
            

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
        question = question_key.get()
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
            
        # if the question author chose to receive emails, send the email:
        sendemail = question.getemail
        # logging.info('sendemail in AnswerHandler is {}'.format(sendemail)) 
        to_addr = question.author.email()
        if((mail.is_email_valid(to_addr)) and (sendemail)):
            message = mail.EmailMessage()
            message.sender = question.author.email()
            message.to = to_addr
            message.body = """
                            Your posted question %s is recently answered: %s
                           """ % (question.title, answer.content)
            message.send()
            
        ifuploadimage = self.request.get('ifuploadimage') 
        # logging.info('ifuploadimage is {}'.format(ifuploadimage))
        if(str(ifuploadimage)=="ifuploadimage"):
            upload_url = blobstore.create_upload_url('/upload_answer_image')
            self.response.write(ANSWERIMAGE_TEMPLATE % (upload_url,questionid,answer.key.id()))
        else:
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
        question.unparsedtags = self.request.get('tags')
        if((not temptags is None)and(not temptags=='')):
            question.tags = temptags.split(";")
            
        ifemailanswer = self.request.get('emailanswer')
        if(str(ifemailanswer)=="emailanswer"):
            question.getemail = True
        else:
            question.getemail = False
        
        # logging.info('getemail has value {}'.format(question.getemail))
            
        # create the corresponding vote for this question:
        question.votedauthors = []
        question.votedauthorsvotes = []
        question.numvoteup = 0
        question.numvotedown = 0
        # only keep valid questions!
        if(not ((question.title is None)and(question.content is None))):
            question.put()
        
        ifuploadimage = self.request.get('ifuploadimage') 
        # logging.info('ifuploadimage is {}'.format(ifuploadimage))
        if(str(ifuploadimage)=="ifuploadimage"):
            upload_url = blobstore.create_upload_url('/upload_question_image')
            self.response.write(QUESTIONIMAGE_TEMPLATE % (upload_url,question.key.id()))
        else:
            self.redirect('/')
        # Note: to see the most recent question, need to refresh the webpage
                
               
class QuestionImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload = self.get_uploads('image')[0] 
        # logging.info('upload is {}'.format(upload))
        
        questionid = self.request.get('questionid')
        # logging.info('QuestionImageUploadH questionid is {}'.format(questionid))        
        
        question_key = questionIdToKey(questionid)
        question = question_key.get()       
        
        question.image = upload.key()
        question.imageurl = images.get_serving_url(upload.key())
        
        question.put()
        # self.redirect(str(question.imageurl))
        self.redirect("/")
        
        
class EditQuestionImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload = self.get_uploads('image')[0] 
        # logging.info('upload is {}'.format(upload))
        
        questionid = self.request.get('questionid')
        # logging.info('QuestionImageUploadH questionid is {}'.format(questionid))        
        
        question_key = questionIdToKey(questionid)
        question = question_key.get()       
        
        question.image = upload.key()
        question.imageurl = images.get_serving_url(upload.key())
        
        question.put()
        # self.redirect(str(question.imageurl))
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))


class AnswerImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload = self.get_uploads('image')[0] 

        questionid = self.request.get('questionid')
        answerid = self.request.get('answerid')
        # logging.info('questionid is {} answer id is {}'.format(questionid,answerid)) 
        answer_key = answerIdToKey(answerid,questionid)
        answer = answer_key.get()       
 
        answer.image = upload.key()
        answer.imageurl = images.get_serving_url(upload.key())
        
        answer.put()
        # self.redirect(str(question.imageurl))
        self.redirect('/detaillist?'+  urllib.urlencode({'questionid': questionid}))


class RSSHandler(webapp2.RequestHandler):
    def post(self):   
        questionid = self.request.get('questionid')

        # logging.info('in RSSHandler, question id is {}'.format(questionid))        
        
        question_key = questionIdToKey(questionid)
        question = question_key.get()
        if(len(Answer.query(ancestor=question_key).fetch())<1):
            answers = []
        else:
            answers = Answer.query(ancestor=question_key).order(-Answer.date_modification).fetch()
        context = {
            'question':     question,
            'answers':      answers,
        }   
        self.response.headers['Content-Type'] = 'application/rss+xml'
        tmpl = os.path.join(os.path.dirname(__file__), 'RSS.xml')
        self.response.out.write(template.render(tmpl, context)) 
        
        
application = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        ('/home',HomeHandler),
        ('/question', QuestionHandler),
        ('/upload_question_image', QuestionImageUploadHandler),
        ('/edit_question_image', EditQuestionImageUploadHandler),
        ('/votequestion', VoteQuestionHandler),
        ('/editquestion_form',EditQuestionHandler_generateform),
        ('/editquestion',EditQuestionHandler),
        ('/removequestion',RemoveQuestionHandler),
        ('/answer', AnswerHandler),
        ('/upload_answer_image', AnswerImageUploadHandler),
        ('/voteanswer', VoteAnswerHandler),
        ('/editanswer_form',EditAnswerHandler_generateform),
        ('/editanswer',EditAnswerHandler),
        ('/removeanswer',RemoveAnswerHandler),
        ('/summarylist.*',QuestionList),
        ('/detaillist.*',QuestionAnswerList),
        # ('/RSS',RSSHandler),
    ], debug=True)
    
        