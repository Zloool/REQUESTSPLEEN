import re
import time
from os import listdir
from os.path import isfile, join

import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from password import SQLALCHEMY_DATABASE_URI
import app

app = Flask(__name__)
app.config.from_object("config")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)

class Leak(db.Model):
    __tablename__ = 'LEAKS_staging'
    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String())
    password = sa.Column(sa.String())
    password_hash = sa.Column(sa.String())
    name = sa.Column(sa.String())
    nickname = sa.Column(sa.String())
    leak_source = sa.Column(sa.String())

    def __init__(self, email="", password_hash="", password="",
                 name="", nickname="", leak_source=""):
        self.email = email
        self.password = password
        self.password_hash = password_hash
        self.name = name
        self.nickname = nickname
        self.leak_source = leak_source

    def __repr__(self):
        return '<Leak %r>' % self.email


def progress_bar(cur, total):
    return "[" + "{:05.2f}".format((cur / float(total)) * 100) + "%] [" + str(cur) + " out of " + str(total) + "]"


def progress_estimate(elapsed, timeleft):
    return "[Elapsed: " + str(int(elapsed)) + "m|Left: " + str(int(timeleft)) + "m]"

def progress_total(total_elapsed):
    return "[Total elapsed: " + str(int(total_elapsed)) + "m]"

def magick_status(source, i, file_string, elapsed, timeleft, total_elapsed):
    return file_string + " " + progress_bar(i, len(source)) + " " + progress_estimate(elapsed, timeleft) + " " + progress_total(total_elapsed)

def load_fill_from_reader(source, current_file, total_files, t_start, filename):
    i = 0
    file_string = "[File \"" + filename + "\" " + str(current_file) + " out of " + str(total_files) + "]"
    records = []
    insert = sa.insert(Leak)
    database = sa.create_engine(
        SQLALCHEMY_DATABASE_URI,
        isolation_level="READ UNCOMMITTED")
    with database.begin() as connection:
        t = time.time()
        for record in source:
            records.append(record)
            i += 1
            if len(records) == 10000:
                elapsed = (time.time() - t) / 60
                timeleft = int(elapsed / i * len(source)) - elapsed
                total_elapsed = (time.time() - t_start)/60
                print magick_status(source, i, file_string, elapsed, timeleft, total_elapsed)
                connection.execute(insert, records)
                del records[:]
        if records:
            connection.execute(insert, records)
    delta_t = time.time() - t
    print "File " + file_string + " imported in " + str(int(delta_t)) + " seconds"
    return delta_t, i


if __name__ == "__main__":
    start_time = time.time()
    mypath = "/home/zlol/Documents/dumps/leaks/dumps/LinkedIn/"
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    x=0
    for ff in onlyfiles:
        x+=1
        with open(mypath+ff, "r") as f:
            print "Current file: " + ff
            source = []
            for line in f:
                try:
                    #res = re.findall(r'(?P<email>.*@.*):(?P<password>.*)', line)
                    res = re.findall(r':\s(?P<hash>.*)\s->\s(?P<email>.*@.*)', line)
                    passw = res[0][0]
                    if passw[0] == "x":
                        passw = ""
                    source.append(
                        {'email': res[0][1], 'password_hash': passw, 'leak_source': 'linkedin_raw_2'})
                except Exception as e:
                    pass
            load_fill_from_reader(source, x, len(onlyfiles), start_time, ff)
