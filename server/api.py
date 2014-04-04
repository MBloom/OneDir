#!/usr/bin/python
from flask.ext.api import FlaskAPI, status
from flask import g, request

from models import User, File, FileMeta, Session

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

@api.route("/api/file/<string:_hash>", methods=["GET", "POST",])
def file(_hash):
    if request.method == "POST":
        content = request.data.get('content', '')        
        to_make = File(content)
        if to_make._hash == _hash:
            g.db.add(to_make)
        return "", status.HTTP_201_CREATED
    else:
        f = g.db.query(File).get(_hash)
        return f.to_dict()

@api.route("/api/meta/<string:name_hash>", methods=['GET', 'POST'])
def meta(name_hash):
    if request.method == "POST":
        permissions = request.data.get('permissions', '')
        file = request.data.get('hash', '')
        new_file_meta = FileMeta(name_hash)        
        # save meta data
        g.db.add(file_meta)
        return "", status.HTTP_201_CREATED
    else:
        fm = g.db.query(FileMeta).get(name_hash)
        return fm.to_dict()

@api.route("/api/<string:username>/active")
def active(username):
    """Returns all the active file our user has in their dir"""
    user = g.db.query(User).get(username)
    actives = filter(lambda x: x.active, user.meta_files)
    return [a.to_dict() for a in actives] 

@api.route("/api/<string:username>/files")
def files(username):
    """Gets all files for specific user"""
    user = g.db.query(User).get(username)
    mfs = user.meta_files
    files = [meta.file.to_dict() for meta in mfs]
    return files

if __name__ == '__main__':
    api.run(debug=True)
