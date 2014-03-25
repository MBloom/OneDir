from sqlalchemy import Column, String, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import g

DB_NAME = 'app.db'

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

class File(Base):
    __tablename__ = 'files'

    name = Column(String, primary_key=True)
    content = Column(LargeBinary)

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    session = Session()
    session.add(User(name='nick', password='pass'))
    import os
    for fname in os.listdir('.'):
        try:
            d = open(fname).read()
            f = File(name=fname, content=d) 
            session.add(f)
        except IOError:
            pass
    session.commit()
