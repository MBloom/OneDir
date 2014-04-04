#!/usr/bin/python
import sys
import sqlite3 as lite

DB_NAME = 'app.db'

def get_connection():
	con = lite.connect(DB_NAME)
	return con

def create_table():
	cur = get_connection().cursor()
	cur.execute("DROP TABLE IF EXISTS files")
	cur.execute("CREATE TABLE files (filename text, content text, owner text)")
	cur.execute("DROP TABLE IF EXISTS users")
	cur.execute("CREATE TABLE users (username text, password text, type text)")

def add_file(f):
	cur = get_connection().cursor()
	cur.execute("INSERT INTO files VALUES(?, ?)", (f, "test contents"))
	#print f, " sent to DB"

def add_user(un, pw, t):
	cur = get_connection().cursor()
	cur.execute("INSERT INTO users VALUES(?, ?, ?)", (un, pw, t)
