#  -*- coding: utf-8 -*- 
from werkzeug.urls import url_parse
from werkzeug.datastructures import CombinedMultiDict

from flask import Flask, flash, redirect, render_template, request, url_for, send_from_directory, session
from flask_login import login_user, logout_user, current_user, login_required

from app import process, app, db
from app.forms import LoginForm, RegistrationForm, WordForm
from wtforms import SelectField
from app.models import User, Word

import json
import requests
import datetime
from config import *

# # Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'jfe^&&*(P&^%$^&*(_)204o2}742uj)_)O_k423'


# Actions doesn't require login
@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data, language=form.language.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('Амжилттай бүртгэгдлээ!')
		return redirect(url_for('login'))
	return render_template('register.html', title='Бүртгүүлэх', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash('Хэрэглэгчийн нэр эсвэл нууц үг буруу байна!')
			return redirect(url_for('login'))
		login_user(user, remember=form.remember_me.data)
		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('index')
		session['language'] = user.language
		session['username'] = user.username
		return redirect(next_page)
	return render_template('login.html', title='Нэвтрэх', form=form)


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))


# Actions require login
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():

	if not (session.get('language') and session.get('username')):
		user = User.query.filter_by(id=current_user.get_id()).first()	
		session['language'] = user.language
		session['username'] = user.username

	if request.method == "GET" and request.args.get('word'):
		this = Word.query.filter_by(username=session['username'],word=request.args.get('word')).order_by(Word.id.desc()).first()
		if this:
			form = WordForm(obj=this)
		else:
			form = WordForm(word=request.args.get('word'))

	else:
		form = WordForm(CombinedMultiDict((request.files, request.form)))
		if form.validate_on_submit():

			this = Word.query.filter_by(username=session['username'],word=form.word.data).order_by(Word.id.desc()).first()
			if this:
				word = this
				word.language=session['language']
				word.username=session['username']
				word.datetime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
				word.word=form.word.data
				word.pos=form.pos.data
				word.pron=form.pron.data
				word.mon=form.mon.data
				word.example_pron=form.example_pron.data
				word.example=form.example.data
				word.example_mon=form.example_mon.data

				db.session.flush()
				db.session.commit()

			else:
				word = Word(
					language=session['language'],
					username=session['username'],
					datetime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
					word=form.word.data,
					pos=form.pos.data,
					pron=form.pron.data,
					mon=form.mon.data,
					example_pron=form.example_pron.data,
					example=form.example.data,
					example_mon=form.example_mon.data)
				
				db.session.add(word)
				db.session.commit()

			path, mp4_file = process.main(form)

			return send_from_directory(path, mp4_file, as_attachment=True)

	return render_template('index.html', title='Үг цээжилэх', form=form)

@app.route('/spellcheck', methods=['GET', 'POST'])
@login_required
def spellcheck():

	if request.method == "POST":
		url = "http://spellcheck.gov.mn/scripts/tiny_mce/plugins/spellchecker/rpc.php"
		data = {
			'id': 'c0',
			'method': 'checkWords',
			'params': ['mn', request.form["text"].split()]
		}
		req = requests.post(url, data=json.dumps(data))
		res = json.loads(req.text)
		mistakes = res.get('result', [])
		if mistakes:
			return json.dumps({"success":True, "mistakes":mistakes}), 200, {"ContentType":"application/json"} 
		else:
			return json.dumps({"success":False}), 200, {"ContentType":"application/json"} 


if __name__ == '__main__':
   app.run(debug = True)
