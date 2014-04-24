#!/usr/bin/python
import os
from datetime import datetime
from functools import wraps

from sqlalchemy.sql import and_
from flask import g, request
from flask.ext.api import FlaskAPI, status
from flask.ext.httpauth import HTTPBasicAuth

import config
from models import (User, Directory, File,
                   Session, get_dir, get_user,
                   Transaction)

api = FlaskAPI(__name__)
api.config.from_object(config)

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    return User.check_password(username, password)

# initializes a per request db session
@api.before_request
def create_session():
    g.db = Session()

# closes and commits that session
@api.after_request
def commit_session(resp):
    g.db.commit()
    return resp

def log_transaction(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        res = func(*args, **kwargs)
        if type(res) == dict or 200 <= res[1] <= 210:
            LOG = True
            # Successful txn, log it.
            _type='DIR'
            path = request.args.get('path')
            if 'file' in request.args:
                p = request.args['path']
                f = request.args['file']
                _type = 'FILE'
                path = os.path.join(p, f)
            action = ''
            if 'move' in request.path:
                action = 'MOVE'
                path  = 'TO: ' + request.args['to']
                path += ' FROM: ' + request.args['from']
            elif request.method == 'POST':
                action ='CREATE'
            elif request.method == 'PUT':
                action ='UPDATE'
            elif request.method == 'DELETE':
                action = 'DELETE'
            else:
                LOG = False
            if LOG: 
                tx = Transaction(user=kwargs['username'],
                                 type=_type,
                                 action=action,
                                 pathname=path,
                                 ip_address=request.remote_addr  
                                 )
                g.db.add(tx)
        return res

    return decorator


@api.route("/api/file/<string:username>", 
           methods=["GET", "POST", "PUT", "DELETE"])
@auth.login_required
@log_transaction
def file(username):
    """All of our api methods for dealing with file changes live within this method"""
    # Must Check credentials for every method
    user = g.db.query(User).get(username)
    # url params
    path = request.args.get('path')
    filename = request.args.get('file')
    if None in [filename or path]:
        return "BAD PARAMS", status.HTTP_406_NOT_ACCEPTABLE
    dir = g.db.query(Directory).filter_by(path=path, owner=user.name).first()
    # ensure needed objects exist in the data store
    if user is None:
        return "NO USER", status.HTTP_405_METHOD_NOT_ALLOWED
    if dir is None:
        return "NO PATH", status.HTTP_406_NOT_ACCEPTABLE
    file = g.db.query(File).filter(File.name == filename,
                        File.owner == user.name,
                        File.dir == dir.inode).first()
    if request.method == "PUT":
        if file is None:
            return "", status.HTTP_405_METHOD_NOT_ALLOWED
        data = request.get_json()
        to_update = File(name=filename,
                         owner=user.name,
                         dir=dir.inode,
                         **data)
        g.db.delete(file)
        g.db.add(to_update)
        return "", status.HTTP_202_ACCEPTED
    elif request.method == "POST":
        if file is not None:
            return "", status.HTTP_409_CONFLICT
        data = request.get_json()
        to_make = File(name=filename,
                       owner=user.name,
                       dir=dir.inode,
                       **data)
        g.db.add(to_make)
        return "", status.HTTP_201_CREATED
    elif request.method == "DELETE":
        if file is None:
            return "", status.HTTP_405_METHOD_NOT_ALLOWED
        g.db.delete(file)
        return "", status.HTTP_202_ACCEPTED
    else: #GET
        print 'yes'
        if file is None:
            return "", status.HTTP_404_NOT_FOUND
        return file.to_dict()
             
@api.route("/api/dir/<string:username>", methods=["POST", "DELETE", "GET"])
@auth.login_required
@log_transaction
def dir(username):
    """Methods for dealing with individual dirs live here"""
    user = g.db.query(User).get(username)
    if user is None:
        return "", status.HTTP_405_METHOD_NOT_ALLOWED
    path = request.args['path']
    dir = g.db.query(Directory).filter_by(owner=user.name, path=path).first()
    if request.method == "POST":
        # Create a directory
        if dir is not None:
            return "", status.HTTP_405_METHOD_NOT_ALLOWED
        new_dir = Directory(path=path, owner=user.name)
        g.db.add(new_dir)
        return "", status.HTTP_201_CREATED
    elif request.method == "GET":
        if dir is None:
            return "", status.HTTP_404_NOT_FOUND
        return dir.to_dict()
    else: #DELETE
        if dir is None:
            return "", status.HTTP_404_NOT_FOUND
        [g.db.delete(f) for f in dir.files]
        g.db.delete(dir)
        return "", status.HTTP_202_ACCEPTED


@api.route("/api/move-dir/<string:username>", methods=["POST"])
@auth.login_required
@log_transaction
def move_dir(username):
    """This method requires to=<path>&from=<path> as url params"""
    to_path = request.args["to"]
    from_path = request.args["from"]

    from_dir = get_dir(username, from_path)
    to_dir   = get_dir(username, to_path)
    user     = get_user(username)

    if not to_dir is None:
        return "", status.HTTP_409_CONFLICT

    if None in [from_dir, user]:
        print from_dir, to_dir, user
        return "", status.HTTP_405_METHOD_NOT_ALLOWED

    from_dir.path = to_path
    g.db.add(from_dir) 
    return "", status.HTTP_202_ACCEPTED


@api.route("/api/move-file/<string:username>", methods=["POST"])
@auth.login_required
@log_transaction
def move_file(username):
    """Requires to=<> and from=<> parameters"""
    to_fpath   = request.args["to"]
    from_fpath = request.args["from"]
    from_path, old_name = os.path.split(from_fpath)
    to_path, new_name = os.path.split(to_fpath)

    from_dir = get_dir(username, from_path)
    to_dir   = get_dir(username, to_path)
    user     = get_user(username)

    if None in [from_dir, to_dir, user]:
        print from_dir, to_dir, user
        return "", status.HTTP_405_METHOD_NOT_ALLOWED

    file = g.db.query(File).filter_by(owner=user.name,
                                      dir=from_dir.inode,
                                      name=old_name).first()
    file.dir = to_dir.inode
    file.name = new_name
    g.db.add(file)
    return "", status.HTTP_202_ACCEPTED
                                
@api.route("/api/latest-change/<string:username>")
@auth.login_required
def latest(username):
    latest = g.db.query(Transaction)\
                 .filter_by(user=username)\
                 .order_by(Transaction.timestamp.desc())\
                 .first()

    out = {'latest-change': datetime(1941, 12, 7)}
    if latest is not None:
    # return a change from last century to keep the api simple by default
        out = latest.to_dict()
    ts = out['latest-change']
    out['latest-change'] = ts.strftime('%Y-%m-%d %H:%M:%S.%f') 
    return out

@api.route("/api/all/<string:username>")
@auth.login_required
def everything(username):
    files = g.db.query(File)\
                .filter_by(owner=username)\
                .all()

    dirs = g.db.query(Directory)\
               .filter(and_(Directory.owner == username,
                            Directory.path !=  "/")
                      )\
               .all()

    files = [f.to_dict() for f in files]
    dirs  = [d.path for d in dirs]
    return {'files': files, 'dirs': dirs}

if __name__ == '__main__':
    api.run(debug=True)
