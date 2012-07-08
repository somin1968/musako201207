# -*- coding:utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
A barebones AppEngine application that uses Facebook for login.
Make sure you add a copy of facebook.py (from python-sdk/src/) into this
directory so it can be imported.
"""

FACEBOOK_APP_ID = '340983539315516'
FACEBOOK_APP_SECRET = '6dec856841aa54989effcb3b6c15645f'

CORRECT_ANSWER = '2322311'

import facebook
import os.path
import wsgiref.handlers
import logging
import urllib2
import re

try:
	import simplejson as json
except ImportError:
	try:
		from django.utils import simplejson as json
	except ImportError:
		import json
_parse_json = json.loads

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api.urlfetch import fetch

import sys
stdin = sys.stdin
stdout = sys.stdout
reload(sys)
sys.setdefaultencoding( 'utf-8' )
sys.stdin = stdin
sys.stdout = stdout

def gf_getBrowser( auser_agent ) :
	lv_user_agent = auser_agent.lower()
	ln_ret = lv_user_agent.find( 'iphone' )
	if ln_ret != -1 :
		return 1
	ln_ret = lv_user_agent.find( 'android' )
	if ln_ret != -1 :
		return 1
	return 0

class User( db.Model ) :
	id = db.StringProperty( required = True )
	created = db.DateTimeProperty( auto_now_add = True )
	updated = db.DateTimeProperty( auto_now = True )
	name = db.StringProperty( required = True )
	profile_url = db.StringProperty( required = True )
	access_token = db.StringProperty( required = True )


class BaseHandler( webapp.RequestHandler ) :
	"""Provides access to the active Facebook user in self.current_user

	The property is lazy-loaded on first access, using the cookie saved
	by the Facebook JavaScript SDK to determine the user ID of the active
	user. See http://developers.facebook.com/docs/authentication/ for
	more information.
	"""
	@property
	def current_user( self ) :
		if not hasattr( self, '_current_user' ) :
			self._current_user = None
			cookie = facebook.get_user_from_cookie(
				self.request.cookies,
				FACEBOOK_APP_ID,
				FACEBOOK_APP_SECRET
			)
			if cookie :
				# Store a local instance of the user data so we don't need
				# a round-trip to Facebook on every request
				user = User.get_by_key_name( cookie['uid'] )
				if not user :
					graph = facebook.GraphAPI( cookie['access_token'] )
					profile = graph.get_object( 'me' )
					user = User(
						key_name = str( profile['id'] ),
						id = str( profile['id'] ),
						name = profile['name'],
						profile_url = profile['link'],
						access_token = cookie['access_token'],
					)
					user.put()
				elif user.access_token != cookie['access_token'] :
					user.access_token = cookie['access_token']
					user.put()
				self._current_user = user
		return self._current_user

class HomeHandler( BaseHandler ) :
	def get( self ) :
		if not self.current_user :
			path = os.path.join( os.path.dirname( __file__ ), 'index.html' )
			args = dict(
				facebook_app_id = FACEBOOK_APP_ID,
				ua_check = gf_getBrowser( self.request.user_agent ),
			)
			self.response.out.write( template.render( path, args ) )
		else :
			self.redirect( '/first' )

	def post( self ) :
		self.get()

class FirstHandler( BaseHandler ) :
	def get( self ) :
		path = os.path.join( os.path.dirname( __file__ ), 'first.html' )
		args = dict(
			facebook_app_id = FACEBOOK_APP_ID,
			ua_check = gf_getBrowser( self.request.user_agent ),
		)
		self.response.out.write( template.render( path, args ) )

class BreakHandler( BaseHandler ) :
	def get( self ) :
		if self.request.get( 'check' ) :
			path = os.path.join( os.path.dirname( __file__ ), 'break.html' )
			args = dict(
				facebook_app_id = FACEBOOK_APP_ID,
				ua_check = gf_getBrowser( self.request.user_agent ),
				answers = {
					'q1': self.request.get( 'q1' ),
					'q2': self.request.get( 'q2' ),
					'q3': self.request.get( 'q3' ),
					'q4': self.request.get( 'q4' ),
					'q5': self.request.get( 'q5' ),
				},
				id = self.request.get( 'id' )
			)
			self.response.out.write( template.render( path, args ) )
		else :
			self.redirect( '/first' )

	def post( self ) :
		self.get()

class SecondHandler( BaseHandler ) :
	def get( self ) :
		if self.request.get( 'check' ) :
			path = os.path.join( os.path.dirname( __file__ ), 'second.html' )
			args = dict(
				facebook_app_id = FACEBOOK_APP_ID,
				ua_check = gf_getBrowser( self.request.user_agent ),
				answers = {
					'q1': self.request.get( 'q1' ),
					'q2': self.request.get( 'q2' ),
					'q3': self.request.get( 'q3' ),
					'q4': self.request.get( 'q4' ),
					'q5': self.request.get( 'q5' ),
				},
			)
			self.response.out.write( template.render( path, args ) )
		else :
			self.redirect( '/first' )

	def post( self ) :
		self.get()

class ResultHandler( BaseHandler ) :
	def get( self ) :
		if self.request.get( 'check' ) :
			answer = self.request.get( 'q1' ) + self.request.get( 'q2' ) + self.request.get( 'q3' ) + self.request.get( 'q4' ) + self.request.get( 'q5' ) + self.request.get( 'q6' ) + self.request.get( 'q7' )
			passing_flg = False
			if answer == CORRECT_ANSWER :
				passing_flg = True
			user = self.current_user
			if user :
				graph_url = 'https://graph.facebook.com/' + user.id + '&locale=ja_JP'
				file = urllib2.urlopen( graph_url )
				content = file.read()
				response = _parse_json( content )
				file.close()
				if passing_flg :
					message = "%s さんは「武蔵小山検定 2012初級」に見事合格されました。おめでとうございます。皆さんも試してみませんか？\nhttp://apps.facebook.com/musako_novice/" % ( response['name'].encode( 'utf-8' ) )	
					graph = facebook.GraphAPI( user.access_token )
					image = open( 'passed_2012_novice.jpg' )
					graph.put_photo( image, message )
					image.close()
			else :
				response = { 'name': 'unknown' }
			path = os.path.join( os.path.dirname( __file__ ), 'result.html' )
			args = dict(
				facebook_app_id = FACEBOOK_APP_ID,
				ua_check = gf_getBrowser( self.request.user_agent ),
				flg = passing_flg,
				username = response['name'],
			)
			self.response.out.write( template.render( path, args ) )
		else :
			self.redirect( '/first' )

	def post( self ) :
		self.get()

class SampleHandler( BaseHandler ) :
	def get( self ) :
		path = os.path.join( os.path.dirname( __file__ ), 'sample.html' )
		args = dict()
		self.response.out.write( template.render( path, args ) )

def main() :
	logging.getLogger().setLevel( logging.DEBUG )
	routes = [
		( r'/', HomeHandler ),
		( r'/first', FirstHandler ),
		( r'/break', BreakHandler ),
		( r'/second', SecondHandler ),
		( r'/result', ResultHandler ),
		( r'/sample', SampleHandler ),
	]
	util.run_wsgi_app( webapp.WSGIApplication( routes ) )


if __name__ == '__main__' :
	main()
