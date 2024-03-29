import collections
import os

from flask import Flask, request, g, render_template, redirect, abort, url_for, Response, Blueprint
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user

import config, models
from models import Session, User, File, Transaction, Directory
from forms import LoginForm, AccountForm, RemovalForm, AccountRemoval, UserPwdChange, AdminPwdChange

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
            new_home_dir = Directory(owner=new_user.name,
                                     path='/')
            g.db.add(new_home_dir)
            g.db.add(new_user)
            login_user(new_user)
            return redirect(url_for("home"))
    print form.data
    return render_template("create.html", form=form, message=None)

@app.route('/remove_user/', methods=["GET", "POST"])
def remove_user():
    all_users = g.db.query(User).all()
    form = AccountRemoval(request.form)
    if form.validate():
        user_toRemove = models.get_user(form.data['username'])
        if user_toRemove == None:
            message = "User does not exist."
            return render_template("remove_user.html", all_users=all_users, form=form, message=message)
        else:
            map(lambda f: g.db.delete(f), user_toRemove.files)
            g.db.delete(user_toRemove)
            return redirect(url_for("admin"))
    # admin authentication
    admins = g.db.query(User).filter_by(userClass="admin").all()
    if current_user in admins:
        return render_template("remove_user.html", all_users=all_users, form=form, message=None)
    else:
        abort(404)

@app.route('/change_pwd/', methods=["GET", "POST"])
def change_pwd():
    form = AdminPwdChange(request.form)
    if form.validate():
        user = models.get_user(form.data['username'])
        if user == None:
            message = "No such user exists"
            return render_template("change_pwd.html", form=form, message=message)
        elif form.data['new_pwd'] != form.data['auth_pwd']:
            message = "Passwords do not match."
            return render_template("change_pwd.html", form=form, message=message)
        else:
            user.password = form.data['new_pwd']
            return redirect(url_for("admin"))
    return render_template("change_pwd.html", form=form, message=None)

@app.route('/info/', methods=["GET", "POST"])
def info():
    form = UserPwdChange(request.form)
    if form.validate():
        if form.data['new_pwd'] != form.data['auth_pwd']:
            message = "Passwords do not match."
            return render_template("info.html", user=current_user, form=form, message=message)
        else:
            current_user.password = form.data['new_pwd']
            return render_template("info.html", user=current_user, form=form, message=None)
    return render_template("info.html", user=current_user, form=form, message=None)

@app.route('/login/', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if form.validate():
        # since the form isn't bad, we check for valid user
        user = models.get_user(form.data['username'])
        if user != None and User.check_password(form.data['username'], form.data['password']):
            login_user(user)
            return redirect(request.args.get("next") or url_for("home"))
        else:
            return render_template("login.html", form=form, message="Username/password do not match.")
    return render_template("login.html", form=form, message=None)


@app.route('/logout/')
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route('/admin/')
@login_required
def admin():
    num_files = len(g.db.query(File).all())
    user_files = {}
    users = g.db.query(User).all()
    for u in users:
        user_files[u] = g.db.query(File).filter_by(owner=u.name).all()
    # admin authentication
    admins = g.db.query(User).filter_by(userClass="admin").all()
    if current_user in admins:
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

@app.route('/log/<string:user>')
@login_required
def log_view(user):
    txns = g.db.query(Transaction).filter_by(user=user).all()
    txns.sort(key=lambda x: x.timestamp, reverse=True)
    return render_template('logs.html', txns=txns)

@app.route('/upload/<string:user>', methods=["POST"])
@login_required
def file_upload(user):
    
    _file = request.files['file']
    cont = ''
    for d in _file.stream:
        cont += d
    from binascii import hexlify
    cont = hexlify(cont)
    
    name = _file.filename
    root = models.get_dir(name=user, path='/')
    db_f = g.db.query(File).filter_by(owner=user, name=name, dir=root.inode).first()
    if db_f is not None:
        return "File already exists", 409

    new_file = File(name=name, owner=user, content=cont, dir=root.inode)
    new_file.directory = root
    tx = Transaction(user=user, 
                     action="CREATE", 
                     type="FILE", 
                     pathname=new_file.pathname(),
                     ip_address=request.remote_addr)
    g.db.add(new_file)
    g.db.add(tx)
    return "Success"

@app.route('/delete/', methods=["POST"])
@login_required
def file_delete():
    form = RemovalForm(request.form)
    if form.validate():
        file_toRemove = models.get_file(form.data['filename'], form.data['path'], form.data['owner'])
        if file_toRemove == None:
            print "No file exists."
        else:
            tx = Transaction(user=current_user.name, 
                     action="DELETE", 
                     type="FILE", 
                     pathname=file_toRemove.pathname(),
                     ip_address=request.remote_addr)
            g.db.add(tx)
            g.db.delete(file_toRemove)
    return redirect(request.referrer)

if __name__ == '__main__':
    app.run('0.0.0.0', port=19199,  debug=True)
