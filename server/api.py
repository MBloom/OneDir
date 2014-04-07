#!/usr/bin/python
from flask.ext.api import FlaskAPI, status
from flask import g, request

from models import User, File, Session

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

@api.route("/api/<string:username>/<string:filename>", methods=["GET", "POST", "PUT", "DELETE"])
def file(username, filename):
    user = g.db.query(User).get(username)
    if user is None:
        return "", status.HTTP_405_METHOD_NOT_ALLOWED
    if request.method == "PUT":
        file = g.db.query(File).get(name)
        pass
    # if user is authorized
    elif request.method == "POST":
            content = request.data.get('content', '')    
            to_make = File(filename, content)
            user.files.append(to_make)
            g.db.add(to_make)
            return "It worked", status.HTTP_201_CREATED
    elif request.method == "DELETE":
        pass
    else: #GET
        file = g.db.query(File).get(name)
        if file is None:
            return "", status.HTTP_404_NOT_FOUND
        return file.to_dict()
             


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
