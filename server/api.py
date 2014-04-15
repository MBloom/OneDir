#!/usr/bin/python
import os

from flask.ext.api import FlaskAPI, status
from flask import g, request

from models import User, Directory, File, Session, get_dir, get_user

api = FlaskAPI(__name__)


# initializes a per request db session
@api.before_request
def create_session():
    g.db = Session()

# closes and commits that session
@api.after_request
def commit_session(resp):
    g.db.commit()
    return resp

@api.route("/api/file/<string:username>", 
           methods=["GET", "POST", "PUT", "DELETE"])
def file(username):
    """All of our api methods for dealing with file changes live within this method"""
    # Must Check credentials for every method
    user = g.db.query(User).get(username)
    # url params
    path = request.args['path']
    filename = request.args['file']

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
        if file is None:
            return "", status.HTTP_404_NOT_FOUND
        return file.to_dict()
             
@api.route("/api/dir/<string:username>", methods=["POST", "DELETE", "GET"])
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
                                

@api.route("/api/<string:username>")
def all_files(username):
    """Returns all the active file our user has in their dir"""
    user = g.db.query(User).get(username)
    actives = filter(lambda x: x.active, user.files)
    return [a.to_dict() for a in actives] 

@api.route("/api/<string:username>/files")
def files(username):
    """Gets all files for specific user"""
    user = g.db.query(User).get(username)
    files = [f.to_dict() for f in user.files]
    return files

if __name__ == '__main__':
    api.run(debug=True)
