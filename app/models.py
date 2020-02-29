from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    language = db.Column(db.String(10))


    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
    
class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(10))
    username = db.Column(db.String(64))
    datetime = db.Column(db.String(16))
    word = db.Column(db.String(128))
    pos = db.Column(db.String(128))
    pron = db.Column(db.String(128))
    mon = db.Column(db.String(256))
    example_pron = db.Column(db.String(256))
    example = db.Column(db.String(256))
    example_mon = db.Column(db.String(256))
    # audio = db.Column(db.String(128))
    # audio_example = db.Column(db.String(128))
    # image = db.Column(db.String(128))
