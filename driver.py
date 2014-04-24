#!/usr/bin/python
import argparse
import os   

import daemon

from client import observer

args = None

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='OneDir Command Line Interface')

    parser.add_argument('-n', '--nosync', help='Turns off client syncing', action='store_true') 
    parser.add_argument('-d', '--daemonize', help='Daemonize the process', action='store_true')

    parser.add_argument('--user', '-u', metavar='user', default='', help='Username') 
    parser.add_argument('--password', '-p', metavar='pw', default='', help='User\'s password') 

    parser.add_argument('--path', metavar='PATH', default='~/OneDir', help='Directory to watch defaults to: %(default)s') 
    parser.add_argument('hostname', metavar='host:port', help='Hostname of server to connect to') 

    args = parser.parse_args()


    fixed_path = os.path.realpath(os.path.expanduser(args.path))

    print "Starting OneDir Client..."

    kwargs = {'path': fixed_path,
              'user': args.user,
              'password': args.password,
              'nosync': args.nosync,
              'hostname': args.hostname}

    if args.daemonize:
        print "...in the background..."
        with daemon.DaemonContext():
            observer.run(**kwargs)
    else:
        observer.run(**kwargs)

