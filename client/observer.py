import os, sys, shutil
import time
from datetime import datetime, timedelta
from binascii import hexlify

from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

from interact import ClientAPI

API = None


def print_diff(diff):
    out = """
Time: {time}
Files created:\n {diff.files_created}
Files modified:\n {diff.files_modified}
Files moved: \n {diff.files_moved}
Files deleted: \n {diff.files_deleted}
Dirs created: \n {diff.dirs_created}
Dirs moved: \n {diff.dirs_moved}
Dirs deleted: \n {diff.dirs_deleted}
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

    # file reports if it has been created and deleted
    conflicts = set([f for f in creat if f in delet])

    out_set  = [('create', f) for f in creat if f not in conflicts]
    out_set += [('delete', f) for f in delet if f not in conflicts]
    out_set += [('modified', f) for f in mod if f not in conflicts]
    out_set += [('moved', tup) for tup in mov if len(d_mov) ==0]

    out_set += [('modified', f) for f in conflicts]

    out_set += [('create_dir', f) for f in d_creat]

    out_set += [('delete_dir', f) for f in d_delet]

    out_set += [('moved_dir', tup) for tup in d_mov]

    return out_set

def file_dict(path):
    """This function will returns the parameters a file obj in our database needs"""
    f = open(path, 'rb')
    content = hexlify(f.read())
    f.close()
    size = os.path.getsize(path)
    to_send = {'content': content,
               'permissions': '0600',
               'size': size
              }
    return to_send


def commit_changes(out_set):
    """Commits the changes in the local directory up to our server"""
    resps = []
    for (action, file_t) in out_set:
        # these variables are overloaded
        file_path = file_t
        dir = file_path
        if action == "create":
            file_d = file_dict(file_path)
            sc = API.create_file(file_path, file_d) 
        elif action == "delete":
            sc = API.delete_file(file_path)
        elif action == "modified":
            file_d = file_dict(file_path)
            sc = API.change_file(file_path, file_d)
        elif action == "moved":
            from_file, to_file = file_t
            sc = API.move_file(from_file, to_file)
        elif action == "create_dir":
            dir = file_path
            sc = API.create_dir(dir)
        elif action == "delete_dir":
            dir = file_path
            sc = API.delete_dir(dir)
        elif action == "moved_dir":
            from_dir, to_dir = file_t
            sc = API.move_dir(from_dir, to_dir)
        else:
            # Never get here
            print "THIS IS BAD"
            pass


def take_snapshot(path):
    snapshot = DirectorySnapshot(path, recursive=True)
    return snapshot


def deal_with_diff(before, after):
    diff = DirectorySnapshotDiff(before, after) 
    if has_changed(diff):
        print_diff(diff)
        change_set = make_change_set(diff) 
        commit_changes(change_set)

def latest_change(path):
    """The directories will report modified if anything within them changes"""
    stat = os.stat(path)
    latest = datetime.fromtimestamp(stat.st_mtime)
    for root, dirs, files in os.walk(path):
        stat = os.stat(root)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        if mtime > latest:
            latest = mtime
        for filename in files:
            fpath = os.path.join(os.path.join(path, root), filename)
            f = open(fpath)
            fstat = os.fstat(f.fileno())
            f.close()
            td = datetime.fromtimestamp(fstat.st_mtime)
            if td > latest:
                latest = td
    return latest

def delete_everything(root, everything):
    # tiny little hack to change the system modified time
    tmpp = os.path.join(root, '.onedir')
    tmpf = open(tmpp, 'w')
    tmpf.write('hehehe')
    tmpf.close()
    os.remove(tmpp)
    # huzzah

    top = next(os.walk(root))
    files = [os.path.join(root, path) for path in top[2]]
    dirs = [os.path.join(root, path) for path in top[1]]
    for i in range(len(everything)):
        path = everything[i]
        if path.startswith('/'):
            path = path[1:]
        path = os.path.join(root, path)
        everything[i] = path
    for fpath in files:
        if fpath in everything:
            os.remove(fpath)
    for dir_p in dirs:
        if dir_p in everything:
            shutil.rmtree(dir_p)

def create_everything(path, api):
    (dirs, files) = api.get_everything()
    dirs.sort(key=lambda s: len(s))
    for dir in dirs:
        try:
            os.mkdir(os.path.join(path, dir))
        except OSError as e:
            if not e.errno == 17:
                raise e 
    for file in files:
        file_path = file['file_path']
        if file_path.startswith('/') == 1:
            file_path = file_path[1:]
        fp = os.path.join(path, file_path)
        f = open(fp, 'w')
        f.write(file['content']) 
        f.close()

def run(path='.', 
        hostname='localhost:5000', 
        nosync=False,
        user='anonymous',
        password='lolcats'):
    """Main observer function"""
    global API
    path = os.path.realpath(path)
    API = ClientAPI(path, user, host=hostname, password=password) 
    print "Watching in: ", path
    create_everything(path, API)
    try:
        while True:
            before = take_snapshot(path)
            wait = 1
            time.sleep(wait)
            after = take_snapshot(path)

            last_modified = latest_change(path)
            upstream_changes = False
            upstream_latest = API.get_latest()
            # if the changes on the server are newer we must deal
            if upstream_latest > last_modified:
                upstream_changes = True
                # delete everything, then download everything from the server
                print "Upstream reports later changes"
                everything = API.list_everything()
                delete_everything(path, everything)
                create_everything(path, API)
                print "Changes synced"
            if not nosync and not upstream_changes: # sync files...
                deal_with_diff(before, after)
    except KeyboardInterrupt:
        print "Killing Program"
        sys.exit()


if __name__ == '__main__':
    path = '../playground'
    if len(sys.argv) > 1:
        path = sys.argv[1]

    print "Starting to watch in %s" % path
    run(path, 'localhost:5000', False, 'admin')
