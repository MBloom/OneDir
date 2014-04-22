from hashlib import sha256
from datetime import datetime
from binascii import hexlify, unhexlify
import os

from sqlalchemy import (Column, String, LargeBinary, 
                        create_engine, ForeignKey, 
                        Boolean, DateTime, Integer,
                        Enum,)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from flask import g

DB_NAME = 'test.db'

engine = create_engine('sqlite:///%s' % DB_NAME, echo=True)
Base = declarative_base()

# global application level session, which handles all conversations with the db
Session = sessionmaker(bind=engine)

#returns a single user from the db
def get_user(name):
    return g.db.query(User).filter_by(name=name).first()

def get_dir(name, path):
    if path == '':
        path = '/'
    return g.db.query(Directory).filter_by(path=path, owner=name).first()

class User(Base):
    __tablename__ = 'users'

    name      = Column(String, primary_key=True)
    password  = Column(String)
    userClass = Column(String)

    files     = relationship("File")
    dirs      = relationship("Directory")

    def __repr__(self):
        return "<User(name={}, pw={}, class={})>".format(self.name, self.password, self.userClass)

    @classmethod
    def check_password(cls, uname, password):
        actual = get_user(uname)
        return actual.password == password

    @classmethod
    def is_admin(cls, uname):
        actual = get_user(uname)
        return actual.userClass == "admin"

    #Flask-login required functions
    def is_authenticated(self):
            return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        u = get_user(self.name)
        return u.name

class Directory(Base):
    __tablename__ = 'dirs'

    inode    = Column(Integer, autoincrement=True, primary_key=True)
    owner    = Column(String, ForeignKey('users.name'),) #primary_key=True)
    path     = Column(String, unique=True)

    files    = relationship('File', backref="container")

    def __init__(self, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val)

    def to_dict(self):
        return {
                 'path': self.path,
                 'files': [file.name for file in self.files]
                }


class File(Base):
    __tablename__ = 'files'

    name        = Column(String, primary_key=True)
    # foreign keys to other tables
    owner       = Column(String, ForeignKey('users.name'), primary_key=True)
    dir         = Column(Integer, ForeignKey('dirs.inode'), primary_key=True)
    stored_on   = Column(DateTime) 
    permissions = Column(String)
    content     = Column(LargeBinary)

    def to_dict(self):
        out = { 'content': hexlify(self.content),
                'name': self.name,
                'permissions': self.permissions,
                'stored_on': self.stored_on,
                'file_path': os.path.join(self.container.path, self.name)
              }
        return out

    def __init__(self, **kwargs):
        """takes a set of kwargs and assigns them to the objects attributes 
        of the same name"""
        # These are sane defaults
        self.permissions = "0600"
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
        if "content" in kwargs:
            self.content = unhexlify(self.content)
        self.stored_on = datetime.now()
        # self.size = os.path.getsize(???)

class Transaction(Base):
    __tablename__ = 'txns'

    user        = Column(String, ForeignKey('users.name'), primary_key=True)
    ip_address  = Column(String, primary_key=True)
    action      = Column(Enum('CREATE', 'DELETE', 'UPDATE'))
    timestamp   = Column(DateTime, default=datetime.utcnow, primary_key=True)
    pathname    = Column(String)
    type        = Column(Enum('DIR', 'FILE'))

    def to_dict(self):
        out = {'latest-changes': str(self.timestamp),
                'action': self.action,
                'pathname': self.pathname
              }
        return out


if __name__ == '__main__':
    Base.metadata.create_all(engine)
    session = Session()
    admin = User(name="admin", password="pass", userClass="admin")
    root = Directory()
    admin.dirs.append(root)
    root.path = "/"
    session.add(admin)
    session.add(root)
    import os
    path = '../playground'
    for fname in os.listdir(path):
        try:
            d = hexlify(open(os.path.join(path,fname)).read())
            f = File(name=fname, content=d) 
            root.files.append(f)
            admin.files.append(f)
            session.add(f)

            # create a txn for the admin
            tx = Transaction()
            tx.user = admin.name
            tx.ip_address = 'localhost:53434'
            tx.pathname = fname
            session.add(tx)
        except IOError:
            pass
    session.commit()
