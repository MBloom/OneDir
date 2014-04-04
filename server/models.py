from hashlib import sha256

from sqlalchemy import Column, String, LargeBinary, create_engine, ForeignKey, Boolean
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

class User(Base):
    __tablename__ = 'users'

    name = Column(String, primary_key=True)
    password = Column(String)
    meta_files = relationship("FileMeta")

    def __repr__(self):
        return "<User(name={}, pw={})>".format(self.name, self.password)

    @classmethod
    def check_password(cls, uname, password):
        actual = get_user(uname)
        return actual.password == password

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

class FileMeta(Base):
    __tablename__ = 'files_meta'

    # name + creation date is primary key
    name = Column(String, primary_key=True)
    stored_on = Column(String) 
    active = Column(Boolean)
    permissions = Column(String)

    # foreign keys out
    _hash = Column(String, ForeignKey('files._hash'))
    file = relationship("File", backref='meta_list')
    owner = Column(String, ForeignKey('users.name'))
    

    def __init__(self, name):
        self.name = name
        self.stored_on = "blah"
        self.permissions = "0600"
        self.active = True

    def to_dict(self):
        out = { 'name': self.name,
                'permissions': self.permissions,
                'stored_on': self.stored_on,
                'file': self._hash
               }
        return out


class File(Base):
    __tablename__ = 'files'

    _hash = Column(String, primary_key=True)
    content = Column(LargeBinary)

    def to_dict(self):
        from binascii import hexlify
        out = { 'content': hexlify(self.content),
                '_hash': self._hash,
              }
        return out

    def __init__(self, content):
       self.content = content
       self._hash = sha256(content).hexdigest()

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    session = Session()
    nick = User(name="nick", password="pass")
    session.add(nick)
    import os
    for fname in os.listdir('.'):
        try:
            d = open(fname).read()
            f = File(content=d) 
            fm = FileMeta(name=fname)
            f.meta_list.append(fm)
            nick.meta_files.append(fm)
            session.add(f)
            session.add(fm)
        except IOError:
            pass
    session.commit()
