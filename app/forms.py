from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, IntegerField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import ValidationError, InputRequired, DataRequired, Email, EqualTo
from app.models import User


class LoginForm(FlaskForm):
	username = StringField('Хэрэглэгчийн нэр', validators=[DataRequired()])
	password = PasswordField('Нууц үг', validators=[DataRequired()])
	remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
	username = StringField('Хэрэглэгчийн нэр', validators=[DataRequired()])
	email = StringField('И-мэйл хаяг', validators=[DataRequired(), Email()])
	password = PasswordField('Нууц үг', validators=[DataRequired()])
	password2 = PasswordField(
		'Нууц үг баталгаажуулах', validators=[DataRequired(), EqualTo('password')])
	language = StringField('Үг оруулах хэл', validators=[DataRequired()])

	def validate_username(self, username):
		user = User.query.filter_by(username=username.data).first()
		if user is not None:
			raise ValidationError('Хэрэглэгчийн нэр бүртгэгдсэн байна.')

	def validate_email(self, email):
		user = User.query.filter_by(email=email.data).first()
		if user is not None:
			raise ValidationError('И-мэйл хаяг бүртгэгдсэн байна.')

class WordForm(FlaskForm):
	word = StringField('Үг', validators=[DataRequired()])
	# pos = SelectField("Үгсийн аймаг", choices=[("名","名"),("形","形"),("动","动"),("副","副")], default="名")
	pos = StringField('Үгсийн аймаг', validators=[DataRequired()])
	pron = StringField('Галиг', validators=[DataRequired()])
	mon = StringField('Орчуулга', validators=[DataRequired()])
	example_pron = StringField('Жишээний галиг')
	example = StringField('Жишээ', validators=[DataRequired()])
	example_mon = StringField('Жишээний орчуулга', validators=[DataRequired()])
	audio = FileField('Үгийн дуудлага', validators=[FileAllowed(['mp3'], 'mp3 only!')])	
	audio_example = FileField('Жишээний дуудлага', validators=[FileAllowed(['mp3'], 'mp3 only!')])
	image = FileField('Зураг', validators=[FileRequired(), FileAllowed(['png','jpg','jpeg'], 'png, jgp, jpeg only!')])	
	shadow = IntegerField('Зурагийн сүүдэр')
	cropped_image = StringField('Хайчилсан зураг') #, validators=[FileRequired()])
