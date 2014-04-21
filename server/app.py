from flask import Flask, request, g, render_template, redirect, abort, url_for, Response
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user

import config, models
from models import Session, User, File
from forms import LoginForm, AccountForm
import collections

app = Flask(__name__, static_folder='static')
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
    # print "yay"
    return models.get_user(uname)

@app.route('/create/', methods=["GET", "POST"])
def create_user():
    form = AccountForm(request.form)
    if form.validate():
        user = models.get_user(form.data['username'])
        if user != None:
            message = "User already exists. Please choose another username."
            return render_template("create.html", form=form, message=message)
        elif form.data['password'] != form.data['auth_pass']:
            message = "Passwords do not match."
            return render_template("create.html", form=form, message=message)
        else:
            new_user = User(name=form.data['username'],
                            password=form.data['password'],
                            userClass="scrub")
            g.db.add(new_user)
            login_user(new_user)
            return redirect(url_for("home"))
    print form.data
    return render_template("create.html", form=form, message=None)

@app.route('/login/', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if form.validate():
        # since the form isn't bad, we check for valid user
        user = models.get_user(form.data['username'])
        if user != None and User.check_password(form.data['username'], form.data['password']):
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
    num_files = len(g.db.query(File).all())
    user_files = {}
    users = g.db.query(User).all()
    for u in users:
        user_files[u] = g.db.query(File).filter_by(owner=u.name).all()
    return render_template('admin.html', user_files=user_files, num_files=num_files)
    # admin authentication
    admins = g.db.query(User).filter_by(userClass="admin")
    if current_user.get_id() in admins:
        return render_template('admin.html', user_files=user_files, num_files=num_files)
    else:
        abort(404)

@app.route('/')
def home():
    uname = current_user.get_id()
    files = g.db.query(File).filter_by(owner=uname).all()
    # print len(files)
    return render_template('home.html', files=files, uname=uname)

@app.route('/file/<string:name>')
def file_view(name):
    file = g.db.query(File).filter_by(name=name).first() 
    resp = Response(mimetype='text/plain')
    resp.set_data(file.content)
    if file is None:
		abort(404)
    return resp

if __name__ == '__main__':
    app.run('0.0.0.0', port=19199,  debug=True)
