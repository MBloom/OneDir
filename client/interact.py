import random
import os
import json

import requests

USER = "nick"
H = {"Content-Type": 'application/json'}

def path_formulator(func):
    def inner(*args, **kwargs):
        path = args[1]
        api = args[0]
        filename = os.path.relpath(path, api.root)
        args = [a for a in args]
        args[1] = filename
        print "Running: %s\nparams: %s" % (func.func_name, str(args[1:])) 
        return func(*args, **kwargs)
    return inner


class ClientAPI():
    def __init__(self, path, user):
        """User of api and root path of filesystem"""
        self.root = path
        self.user = user

    def make_url(self, fname):
        url = "http://localhost:5000/api/file/{}/{}"
        return url.format(self.user, fname)

    @path_formulator
    def create_file(self, fname, to_send):
        """Creates a file from the provided dictionary"""
       
        url = self.make_url(fname)
        resp = requests.post(url, data=json.dumps(to_send), headers=H)

        return resp.status_code

    @path_formulator
    def change_file(self, fname, to_send):
        """Modifies a file upstream"""
        url = self.make_url(fname)
        resp = requests.put(url, data=json.dumps(to_send), headers=H)
        return resp.status_code

    @path_formulator
    def get_file(self, fname):

        url = self.make_url(fname)
        resp = requests.get(url, headers=H)
        print resp.json()
        return resp.status_code

    @path_formulator
    def delete_file(self, fname):
        url = self.make_url(fname)
        resp = requests.delete(url, headers=H)
        return resp.status_code


if __name__ == '__main__':
    
    fname = "T"*random.randint(0,10)+"Bats.txt"
    content = "NaNa"*random.randint(4,50) + " Baaaaaatman!"

    api = ClientAPI('.', 'nick')

    api.create_file(fname, {'content': content})
    #print create_file(fname, content)
    #print get_file(fname)
    print api.delete_file(fname)


