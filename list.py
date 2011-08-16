import cgi
import os
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class UserInfo(db.Model):
	user = db.UserProperty()
	displayName = db.StringProperty()

class Idea(db.Model):
	author = db.UserProperty()
	upvotes = db.IntegerProperty()
	downvotes = db.IntegerProperty()
	score = db.IntegerProperty()
	content = db.StringProperty(multiline=True)
	date = db.DateTimeProperty(auto_now_add=True)
	hasVoted = db.StringListProperty()
	authorInfo = db.ReferenceProperty(UserInfo)

def getCurrentUserInfo():
	return db.GqlQuery("SELECT * FROM UserInfo WHERE user = :1", users.get_current_user()).get()

class MainPage(webapp.RequestHandler):
	def get(self):
		ideas_query = Idea.all().order('-score')
		ideas = ideas_query.fetch(100)
		
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'Logout'
		
		if users.is_current_user_admin():
			admin = 1
		else:
			admin = 0
	
		template_values = {
			'ideas': ideas,
			'url': url,
			'url_linktext': url_linktext,
			'admin': admin,
		}

		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class IdeaList(webapp.RequestHandler):
    def post(self):
			idea = Idea()
			idea.author = users.get_current_user()
			newInfo = getCurrentUserInfo()
		
			if not newInfo:
				newInfo = UserInfo()
				newInfo.user = users.get_current_user()
				newInfo.displayName = users.get_current_user().nickname()
				newInfo.put()

			idea.authorInfo = newInfo
			idea.content = self.request.get('content')
			idea.upvotes = 0
			idea.downvotes = 0
			idea.score = 0
			idea.put()
			self.redirect('/')

class UpVote(webapp.RequestHandler):
    def post(self):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		
		hasVoted = idea.hasVoted
		user = users.get_current_user()
		userid = user.user_id()
		
		try:
			i = hasVoted.index(userid)
		except ValueError:
			i = -1 # no match
		
		if i == -1: #they can only vote if this was their first time
			idea.hasVoted.append(userid)
			idea.upvotes = idea.upvotes + 1
			idea.score = idea.score + 1
			idea.put()
		
		self.redirect('/')

class DownVote(webapp.RequestHandler):
    def post(self):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		
		hasVoted = idea.hasVoted
		user = users.get_current_user()
		userid = user.user_id()
		
		try:
			i = hasVoted.index(userid)
		except ValueError:
			i = -1 # no match

		if i == -1: #can only vote on first time
			idea.hasVoted.append(userid)
			idea.downvotes = idea.downvotes + 1
			idea.score = idea.score - 1
			idea.put()

		self.redirect('/')

class Accept(webapp.RequestHandler):
	def post(self):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		idea.delete()
		self.redirect('/')

class Edit(webapp.RequestHandler):
	def get(self):
		
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'Logout'
		user = users.get_current_user()
		userinfo = getCurrentUserInfo()
		if userinfo and userinfo.displayName:
			username = userinfo.displayName
		else:
			username = user.nickname()
		
		template_values = {			
			'url': url,
			'url_linktext': url_linktext,
			'username': username,
		}
		
		path = os.path.join(os.path.dirname(__file__), 'edit.html')
		self.response.out.write(template.render(path, template_values))
	
	def post(self):
		newname = self.request.get('name')
		
		u = db.GqlQuery("SELECT * FROM UserInfo WHERE user = :1", users.get_current_user()).get()
		
		if u:
			u.displayName = newname
			self.response.out.write(u.displayName)
			u.put()
		else:
			info = UserInfo()
			info.user = users.get_current_user()
			info.displayName = newname
			info.put()
		
		self.redirect('/')



application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/newidea', IdeaList),
									  ('/upvote', UpVote),
									  ('/downvote', DownVote),
									  ('/accept', Accept),
									  ('/edit', Edit)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()