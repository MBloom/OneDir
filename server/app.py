from flask import Flask, request, g, render_template, redirect, abort, url_for
from flask.ext.login import LoginManager, login_required, login_user, logout_user

import config, models
from models import Session, User, File
from forms import LoginForm

app = Flask(__name__)
app.config.from_object(config)

login_manager = LoginManager()
login_manager.init_app(app)

# initializes a per request db session
@app.before_request
def create_session():
    g.db = Session()

# closes and commits that session
@app.after_request
def commit_session(resp):
    g.db.commit()
    return resp

@login_manager.user_loader
def load_user(uname):
    # returns none if user does not exist
    print "yay"
    return models.get_user(uname)

@app.route('/login/', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if form.validate():
        # since the form isn't bad, we check for valid user
        if User.check_password(form.data['username'], 
                               form.data['password']):
            user = models.get_user(form.data['username'])
            login_user(user)
	    return redirect(request.args.get("next") or url_for("home"))
    return render_template("login.html", form=form)

@app.route('/logout/')
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route('/admin')
@login_required
def admin():
    users = g.db.query(User).all()
    return render_template('admin.html', users=users)

@app.route('/')
def home():
    files = g.db.query(File).all()
    print len(files)
    return render_template('home.html', files=files)

@app.route('/file/<string:hash>')
def file_view(hash):
    file = g.db.query(File).filter_by(name=hash).first() 
    if file is None:
	abort(404)
    return str(file.content)

if __name__ == '__main__':
    app.run('0.0.0.0', port=19199,  debug=True)
