#!/usr/bin/python
import time
import sqlite3 as lite

DB_NAME = 'app.db'

def get_connection():
	con = lite.connect(DB_NAME)
	return con

def send_file(f):
	db = get_connection()
	cur.execute("INSERT INTO files VALUES(?, ?)", f, "test contents")
	print f, " sent to DB"