import cgi
import os
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from operator import attrgetter


class UserInfo(db.Model):
	user = db.UserProperty()
	displayName = db.StringProperty()
	listIDs = db.ListProperty(long) #ids  of the Lists that they are in
	votes = db.ListProperty(db.Key) # keys of the Vote objects for this user

class List(db.Model):
	name = db.StringProperty()
	hasPassword = db.BooleanProperty()
	password = db.StringProperty()
	userList = db.ListProperty(db.Key) #keys of the UserInfos of people in this list
	url = db.StringProperty()
	hasComments = db.BooleanProperty()

class Idea(db.Model):
	author = db.UserProperty()
	upvotes = db.IntegerProperty()
	downvotes = db.IntegerProperty()
	score = db.IntegerProperty()
	content = db.StringProperty(multiline=True)
	date = db.DateTimeProperty(auto_now_add=True)
	authorInfo = db.ReferenceProperty(UserInfo)
	theList = db.ReferenceProperty(List)
	listID = db.IntegerProperty()
	
class Vote(db.Model):
	idea = db.ReferenceProperty(Idea)
	userInfo = db.ReferenceProperty(UserInfo)
	theVote = db.IntegerProperty() # +1 (upvote), -1 (downvote), 0 (novote)

def createUserInfo():
	info = UserInfo()
	info.user = users.get_current_user()
	info.displayName = users.get_current_user().nickname()
	info.put()
	return info

def getCurrentUserInfo():
	return db.GqlQuery("SELECT * FROM UserInfo WHERE user = :1", users.get_current_user()).get()


def getRedirectUrl(listID):
	return '/list/' + str(listID)
	
	
class LoginToList(webapp.RequestHandler):
	def get(self, listID):
		list = List.get_by_id(int(listID))
		if not list.hasPassword:
			self.redirect(getRedirectUrl(listID))
			
		template_values = {
			'listID': listID,
			'list': list
		}

		path = os.path.join(os.path.dirname(__file__), 'listlogin.html')
		self.response.out.write(template.render(path, template_values))

	def post(self, listID):
		password = self.request.get('listPassword')
		
		curInfo = getCurrentUserInfo()
		list = List.get_by_id(int(listID))
		
		if list.password == password:
			self.redirect(getRedirectUrl(listID))
			list.userList.append(curInfo.key())
			list.put()
			curInfo.listIDs.append(int(listID))
			curInfo.put()
		else:
			self.response.out.write("wrong password")
	

class Profile(webapp.RequestHandler):
	def get(self, infoID):
		userInfo = UserInfo.get_by_id(int(infoID))
		
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'logout'
		
		template_values = {
			'userInfo': userInfo,
			'url': url,
			'url_linktext': url_linktext,
		}

		path = os.path.join(os.path.dirname(__file__), 'profile.html')
		self.response.out.write(template.render(path, template_values))


class Login(webapp.RequestHandler):
	def post(self):
		listID = self.request.get('listID')
		listPassword = self.request.get('listPassword')
		
		if len(listID) == 0:
			self.redirect('/')
			return
	
		curInfo = getCurrentUserInfo()
		list = List.get_by_id(int(listID))
		
		if list:
			self.response.out.write(list.name)
		else:
			self.response.out.write("there was no list with that id<br/>")
		
		if not list.hasPassword:
			self.redirect(getRedirectUrl(listID))
			list.userList.append(curInfo.key())
			list.put()
			curInfo.listIDs.append(listID)
			curInfo.put()
			
		if list.password == listPassword:
			self.redirect(getRedirectUrl(listID))
			list.userList.append(curInfo.key())
			list.put()
			curInfo.listIDs.append(int(listID))
			curInfo.put()
		else:
			self.response.out.write("wrong password")
			

class CreateList(webapp.RequestHandler):
	def post(self):
		listName = self.request.get('listName')
		listPassword = self.request.get('listPassword')
		
		if len(listName) == 0:
			self.redirect('/')
			return
		
		currentUserInfo = getCurrentUserInfo()
		
		if not currentUserInfo:
			currentUserInfo = UserInfo()
			currentUserInfo.user = users.get_current_user()
			currentUserInfo.displayName = users.get_current_user().nickname()
			currentUserInfo.put()
		
		newList = List()
		newList.name = listName
		if listPassword:
			newList.hasPassword = True
			newList.password = listPassword
		else:
			newList.hasPassword = False
		
		# add the user to the List

		newList.userList.append(currentUserInfo.key())
		newList.put()
		
		# add the List to the UserInfo
		currentUserInfo.listIDs.append(newList.key().id())
		currentUserInfo.put()
		
		url = getRedirectUrl(newList.key().id())
		self.redirect(url)

class MainPage(webapp.RequestHandler):
	def get(self):
		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'logout'
			
			info = getCurrentUserInfo()
		
			if not info:
				info = UserInfo()
				info.user = users.get_current_user()
				info.displayName = users.get_current_user().nickname()
				info.put()
				
			greeting = info.displayName
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'login'
			greeting = ""


		
		mylists = []
		for listID in info.listIDs:
			#get that list and append it
			theList = List.get_by_id(int(listID))
			mylists.append(theList)
			
		#mylists.sort(key=attrgetter('name'))
		
		exception = None #"Error"
		
		template_values = {
			'url': url,
			'url_linktext': url_linktext,
			'greeting': greeting,
			'mylists': mylists,
			'exception': exception,
		}

		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))


# Gets the Vote on this idea for the current user or returns none if they have not voted	
def getVoteOnIdea(idea):
	userInfo = getCurrentUserInfo()
	return db.GqlQuery("SELECT * FROM Vote WHERE userInfo = :1 AND idea = :2", userInfo, idea).get()

class ListView(webapp.RequestHandler):
	def get(self, listID):
		userInfo = getCurrentUserInfo()
		theList = List.get_by_id(int(listID))
		
		if not userInfo:
			userInfo = createUserInfo()
		if not int(listID) in userInfo.listIDs:
			if theList.hasPassword:
				url = '/loginfor/' + str(listID)
				self.redirect(url)
				
				
		#add user to list, and add list to user###########
		if not int(listID) in userInfo.listIDs:
			userInfo.listIDs.append(int(listID))
			userInfo.put()
		
	
		ideas_query = Idea.all().order('-score')
		ideas_query.filter('listID =', int(listID))
		ideas = ideas_query.fetch(100)
		
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'logout'
		
		if users.is_current_user_admin():
			admin = 1
		else:
			admin = 0
		
		exception = None
		
		infoList = []
		for idea in ideas:
			curVote = getVoteOnIdea(idea)
			infoList.append( (idea,curVote) )

		#instead of returning ideas and votes, return a list of 
		#tuples of ideas and votes, this way we can know if the user has voted
			
		template_values = {
			'ideas': ideas,
			'infoList': infoList,
			'list': theList,
			'theUrl': self.request.uri,
			'listID': listID,
			'listName': theList.name,
			'url': url,
			'url_linktext': url_linktext,
			'admin': admin,
			'exception': exception,
		}

		path = os.path.join(os.path.dirname(__file__), 'list.html')
		self.response.out.write(template.render(path, template_values))
		

class IdeaList(webapp.RequestHandler):
    def post(self, listID):
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
		
		if len(idea.content) == 0:
			self.redirect(getRedirectUrl(listID))
			return
		
		idea.upvotes = 0
		idea.downvotes = 0
		idea.score = 0
		idea.listID = int(listID)
		idea.put()
		url = getRedirectUrl(listID)
		self.redirect(url)
			
def addToVoteCount(idea, voteType, switch):
	if voteType == 1:
		idea.upvotes = idea.upvotes + 1
		if switch:
			idea.downvotes -= 1
	if voteType == -1:
		idea.downvotes = idea.downvotes + 1
		if switch:
			idea.upvotes -= 1
	
	idea.score += voteType
	
	if switch:
		idea.score += voteType
	
	idea.put()
			
def modifyOrCreateVote(idea, voteType):
	#first check to see if this user has voted on this idea before
	vote = getVoteOnIdea(idea)
	
	if vote: #we only need to modify the vote
		previousVote = vote.theVote
		if previousVote == voteType:
			return
		switch = True
		vote.theVote = voteType
		
	else:
		vote = Vote()
		vote.idea = idea
		vote.theVote = voteType
		vote.userInfo = getCurrentUserInfo()
		switch = False
	
	vote.put()
	addToVoteCount(idea, voteType, switch)


class UpVote(webapp.RequestHandler):
    def post(self, listID):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		modifyOrCreateVote(idea, 1)
		url = getRedirectUrl(listID)
		self.redirect(url)

class DownVote(webapp.RequestHandler):
    def post(self, listID):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		modifyOrCreateVote(idea, -1)
		url = getRedirectUrl(listID)
		self.redirect(url)

class Accept(webapp.RequestHandler):
	def post(self, listID):
		id = self.request.get('id')
		idea = Idea.get_by_id(int(id))
		idea.delete()
		# we also need to delete all of the votes that reference this idea
		self.redirect(getRedirectUrl(listID))

class Edit(webapp.RequestHandler):
	def get(self, listID):
		
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
			'listID': listID
		}
		
		path = os.path.join(os.path.dirname(__file__), 'edit.html')
		self.response.out.write(template.render(path, template_values))
	
	def post(self, listID):
		newname = self.request.get('name')

		u = db.GqlQuery("SELECT * FROM UserInfo WHERE user = :1", users.get_current_user()).get()
		
		if len(newname) != 0:
			if u:
				u.displayName = newname
				u.put()
			else:
				info = UserInfo()
				info.user = users.get_current_user()
				info.displayName = newname
				info.put()
			
		if len(listID) == 0:  #if they are editing from the home page redirect them back
			url = '/'
		else:
			url = getRedirectUrl(listID)
			
		self.redirect(url)



application = webapp.WSGIApplication(
                                     [('/', MainPage),
									  ('/create', CreateList),
									  (r'/list/(.*)', ListView),
                                      (r'/newidea/(.*)', IdeaList),
									  (r'/upvote/(.*)', UpVote),
									  (r'/downvote/(.*)', DownVote),
									  (r'/accept/(.*)', Accept),
									  (r'/edit/(.*)', Edit),
									  ('/login', Login),
									  (r'/loginfor/(.*)', LoginToList),
									  (r'/profile/(.*)', Profile)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()