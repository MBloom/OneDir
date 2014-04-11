import os, sys
import time
from datetime import datetime
from binascii import hexlify

from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

from interact import ClientAPI

PATH = os.path.realpath('.')
API = None


def print_diff(diff):
    out = """
Time: {time}
Files created:\n {diff.files_created}
Files modified:\n {diff.files_modified}
Files moved: \n {diff.files_moved}
Files deleted: \n {diff.files_deleted}
Dirs created: \n {diff.dirs_created}
    """.format(diff=diff, time=datetime.now())
    print out

def has_changed(diff):
    creat, mod = diff.files_created, diff.files_modified
    mov, delet = diff.files_moved, diff.files_deleted

    d_creat, d_mod = diff.dirs_created, diff.dirs_modified
    d_mov, d_delet = diff.dirs_moved, diff.dirs_deleted

    all_things = [creat, mod, mov, delet, d_creat, d_mod, d_mov, d_delet]

    changes = filter(lambda x: len(x) > 0, all_things)
    
    if len(changes) > 0:
        return True
    else:
        return False

def make_change_set(diff):
    creat, mod = diff.files_created, diff.files_modified
    mov, delet = diff.files_moved, diff.files_deleted

    d_creat, d_mod = diff.dirs_created, diff.dirs_modified
    d_mov, d_delet = diff.dirs_moved, diff.dirs_deleted

    # file reports it has been created and deleted
    conflicts = set([f for f in creat if f in delet])

    out_set  = [('create', f) for f in creat if f not in conflicts]
    out_set += [('delete', f) for f in delet if f not in conflicts]
    out_set += [('modified', f) for f in mod if f not in conflicts]
    out_set += [('moved', tup) for tup in mov]

    out_set += [('modified', f) for f in conflicts]

    return out_set

def file_dict(filename):
    """This function will returns the parameters a file obj in our database needs"""
    content = hexlify(open(filename, 'rb').read())
    to_send = {'content': content,
               'path': 'batcave',
               'active': True,
               'permissions': '0600' 
              }
    return to_send


def commit_changes(out_set):
    """Commits the changes in the local directory up to our server"""

    resps = []
    for (action, file_t) in out_set:
        filename = file_t
        if action == "create":
            file_d = file_dict(filename)
            sc = API.create_file(filename, file_d) 
        elif action == "delete":
            sc = API.delete_file(filename)
        elif action == "modified":
            file_d = file_dict(filename)
            sc = API.change_file(filename, file_d)
        elif action == "moved":
            print "not implmented"
        else: 
            # Never get here
            pass



def take_snapshot():
    snapshot = DirectorySnapshot(PATH, recursive=True)
    return snapshot


def deal_with_diff(before, after):
    diff = DirectorySnapshotDiff(before, after) 
    if has_changed(diff):
        print_diff(diff)
        change_set = make_change_set(diff) 
        commit_changes(change_set)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
        PATH = os.path.realpath(path)
    API = ClientAPI(PATH, "nick")
    print "Starting to watch in %s" % PATH
    
    try:
        while True:
            before = take_snapshot()
            time.sleep(1)
            after = take_snapshot()
            deal_with_diff(before, after)
    except KeyboardInterrupt:
        print "Killing program"
        quit()





