from wtforms.form import Form
from wtforms import StringField, PasswordField
from wtforms.validators import Length

class LoginForm(Form):
    username = StringField('Username', validators=[Length(min=3, max=30)])
    password = PasswordField('Password', validators=[Length(min=3, max=30)])
