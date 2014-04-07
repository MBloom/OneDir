import random

import requests
import json

USER = "nick"
H = {"Content-Type": 'application/json'}

def make_url(fname):
    url = "http://localhost:5000/api/file/{}/{}"
    return url.format(USER, fname)

def create_file(fname, content):
    """Creates a file from the provided dictionary"""

    to_send = {'content': content,
               'path': 'batcave',
               'active': True,
               'permissions': '0600' 
              }
    
    resp = requests.post(make_url(fname), data=json.dumps(to_send), headers=H)

    return resp.status_code

def get_file(fname):

    resp = requests.get(make_url(fname), headers=H)
    print resp.json()
    return resp.status_code

def delete_file(fname):
    resp = requests.delete(make_url(fname), headers=H)

    return resp.status_code


if __name__ == '__main__':
    
    fname = "T"*random.randint(0,10)+"Bats.txt"
    content = "NaNa"*random.randint(4,50) + " Baaaaaatman!"
    print create_file(fname, content)
    print get_file(fname)
    print delete_file(fname)


