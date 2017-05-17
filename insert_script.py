import re
import time
from os import listdir
from os.path import isfile, join

import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from password import SQLALCHEMY_DATABASE_URI


class LeaksIterator:
    def __init__(self, filename):
        self.leak_file = open(filename, "rU")
        self.size = sum(1 for line in self.leak_file)
        self.leak_file = open(filename, "rU")
        self.cache = []

    def __iter__(self):
        return self

    def __len__(self):
        return self.size

    def next(self):
        if self.leak_file.closed:
            raise StopIteration
        leaks = []
        x = 0
        # print "begin loop"
        while x < 10000:
            line = self.leak_file.readline().decode("utf-8", "ignore")
            if not line:
                self.leak_file.close()
                raise StopIteration
            try:
                #res = re.findall(r'.*\:(?P<email>.*@.*)\:.*\:(?P<pass>.*)', line)
                res = re.findall(r'(?P<email>.*@.*)(\:|;)(?P<pass>.*)', line)
                email = res[0][0].replace(' \t\r\n\0\\', '')
                password = res[0][1].replace(' \t\r\n\0\\', '')
                leaks.append(
                    {'email': email, 'password_hash': password, 'leak_source': 'exploit_in'})
                x += 1
            except Exception as e:
                print line,
                print e
        # print "end loop"
        return leaks


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


def load_fill_from_reader(source, t_start, file_string):
    i = 0
    #file_string = "[File \"" + filename + "\" " + str(current_file) + " out of " + str(total_files) + "]"
    insert = sa.insert(Leak)
    database = sa.create_engine(
        SQLALCHEMY_DATABASE_URI,
        isolation_level="READ UNCOMMITTED")
    with database.begin() as connection:
        t = time.time()
        for records in source:
            i += 1 * 10000
            elapsed = (time.time() - t) / 60
            timeleft = int(elapsed / i * len(source)) - elapsed
            total_elapsed = (time.time() - t_start) / 60
            print magick_status(source, i, file_string, elapsed, timeleft, total_elapsed)
            # print "begin insert"
            connection.execute(insert, records)
            # print "end insert"
    delta_t = time.time() - t
    print "File " + file_string + " imported in " + str(int(delta_t)) + " seconds"
    return delta_t, i


if __name__ == "__main__":
    start_time = time.time()
    mypath = "/mnt/c/Users/Zlooo/Documents/Exploit.in/"
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    x = 0
    for leak_file in onlyfiles:
        load_fill_from_reader(LeaksIterator(
            mypath + leak_file), start_time, leak_file)
