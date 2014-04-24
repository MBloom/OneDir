import random, time, os, json, sys
from datetime import datetime
from binascii import unhexlify, hexlify

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError

DEBUG= True
USER = "nick"
H = {"Content-Type": 'application/json'}

def relpath(file_path, root):
    """Always takes a full path"""
    path = os.path.relpath(file_path, root)
    return path

def path_formulator(func):
    def inner(*args, **kwargs):
        file_path = args[1]
        api = args[0]
        # normalizes file_path
        file_path = relpath(file_path, api.root)
        args = list(args)
        args[1] = file_path
        url = api.dir_url(file_path) if "dir" in func.func_name else api.file_url(file_path)
        if DEBUG:
            print "Running: %s\nParams: %s\nAgainst: %s" % (func.func_name, str(args[1:]), url)
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            print "Connection error: ", e
    return inner


class ClientAPI():
    def __init__(self, path, user, host="localhost:5000", password="empty"):
        """User of api and root path of filesystem"""
        self.root = path
        self.user = user
        self.host = host
        self.auth = HTTPBasicAuth(user, password)



    def file_url(self, file_path):
        path, file = os.path.split(file_path)
        if path == '':
            path = '/'

        # we have a file op
        url = "http://{}/api/file/{}?file={}&path={}"
        return url.format(self.host, self.user, file, path)

    def dir_url(self, path):
        # we have a dir operations
        url = "http://{}/api/dir/{}?path={}"
        return url.format(self.host, self.user, path)

    @path_formulator
    def create_file(self, file_path, to_send):
        """Creates a file from the provided dictionary"""
       
        url = self.file_url(file_path)
        resp = requests.post(url, data=json.dumps(to_send), headers=H, auth=self.auth)

        return resp.status_code

    @path_formulator
    def change_file(self, file_path, to_send):
        """Modifies a file upstream"""
        url = self.file_url(file_path)
        resp = requests.put(url, data=json.dumps(to_send), headers=H, auth=self.auth)
        return resp.status_code

    @path_formulator
    def get_file(self, file_path):
        url = self.file_url(file_path)
        resp = requests.get(url, headers=H, auth=self.auth)
        print resp.json()
        return resp.status_code

    @path_formulator
    def delete_file(self, file_path):
        url = self.file_url(file_path)
        resp = requests.delete(url, headers=H, auth=self.auth)
        return resp.status_code

    def move_file(self, from_path, to_path):
        from_path = relpath(from_path, self.root)
        to_path =  relpath(to_path, self.root)
        url = "http://{}/api/move-file/{}?to={}&from={}"\
                                        .format( self.host,
                                                self.user,
                                                to_path,
                                                from_path,
                                              )
        if DEBUG:
            print "Url:\n%s\nFrom: %s\nTo: %s" % (url, from_path, to_path)
        resp = requests.post(url, headers=H, auth=self.auth)
        return resp.status_code

    def move_dir(self, from_path, to_path):
        from_path = relpath(from_path, self.root)
        to_path = relpath(to_path, self.root)

        url = "http://{}/api/move-dir/{}?to={}&from={}"\
                                    .format( self.host,
                                            self.user,
                                            to_path,
                                            from_path,
                                          )
        if DEBUG:
            print "Url:\n%s\nFrom: %s\nTo: %s" % (url, from_path, to_path)
        resp = requests.post(url, headers=H, auth=self.auth)
        return resp.status_code

    @path_formulator
    def create_dir(self, path):
        url = self.dir_url(path)
        resp = requests.post(url, headers=H, auth=self.auth)
        return resp.status_code

    @path_formulator
    def get_dir(self, path):
        url = self.dir_url(path)
        resp = requests.get(url, headers=H, auth=self.auth)
        return resp.status_code

    @path_formulator
    def delete_dir(self, path):
        url = self.dir_url(path)
        resp = requests.delete(url, headers=H, auth=self.auth)
        return resp.status_code

    def get_latest(self):
        url = "http://{}/api/latest-change/{}"\
                                    .format(self.host,
                                            self.user)
        resp = None
        success = False
        first = True
        while not success:
            try:
                resp = requests.get(url, headers=H, auth=self.auth)
                success = True
                if not first:
                    print " Reconnected!"
            except ConnectionError as e:
                if first:
                    sys.stdout.write("Connection to the server down! . . . Retrying ")
                    first = False
                else: 
                    sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(1)   
        if resp.status_code == 401:
            print "Bad Login"
            sys.exit()
        assert resp.status_code == 200
        _json = resp.json()
        str_date = _json.get('latest-change')
        latest_upstream = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S.%f') 
        return latest_upstream

    def get_everything(self):
        """The initial download from the server"""
        url = "http://{}/api/all/{}".format(self.host, self.user)
        resp = requests.get(url, headers=H, auth=self.auth)
        assert resp.status_code == 200
        _json = resp.json()
        dirs = _json['dirs']
        files = _json['files']
        for d in files:
            d['content'] = unhexlify(d['content'])
        return (dirs, files)

        

if __name__ == '__main__':
    full_path = os.path.realpath('.')
    file_path = os.path.join(full_path, "T"*random.randint(0,10)+"Bats.txt")
    content = "NaNa"*random.randint(4,50) + " Baaaaaatman!"

    api = ClientAPI('.', user='admin', password='pass')
    
    from binascii import hexlify
    api.create_file(file_path, {'content': hexlify(content)})
    print api.get_file(file_path)
    print api.delete_file(file_path)


