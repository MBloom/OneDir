from wtforms.form import Form
from wtforms import StringField, PasswordField
from wtforms.validators import Length

class LoginForm(Form):
	username = StringField('Username', validators=[Length(min=3, max=30)])
	password = PasswordField('Password', validators=[Length(min=3, max=30)])

class AccountForm(Form):
	username = StringField('Username', validators=[Length(min=3, max=30)])
	password = PasswordField('Password', validators=[Length(min=3, max=30)])
	auth_pass = PasswordField('Repeat Password')

class AccountRemoval(Form):
	username = StringField('Username', validators=[Length(min=3, max=30)])

class RemovalForm(Form):
	filename = StringField('FileName')
	path = StringField('Path')
	owner = StringField('Owner')
