import re
import string
import sys
import time
from os import listdir
from os.path import isfile, join

import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from password import SQLALCHEMY_DATABASE_URI

monster_regexp = r'((?P<email>(?:[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")(|\.+)@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-zA-Z0-9-]*[a-zA-Z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\]))(.)(?P<password>.*))|((?P<password2>.*)(.)(?P<email2>(?:[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")(|\.+)@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-zA-Z0-9-]*[a-zA-Z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])))'

class LeaksIterator:
    """
    Iterator, that gets file with leaks, and spits out 10000 db entrys on each call
    """
    def __init__(self, filename):
        # I just want to know the filesize
        self.leak_file = open(filename, "rU")
        self.size = sum(1 for line in self.leak_file)
        self.leak_file = open(filename, "rU")
        self.cache = []

    def __iter__(self):
        return self

    def __len__(self):
        return self.size

    def next(self):
        """
        Function, where all magick happens. 
        """
        if self.leak_file.closed:
            raise StopIteration
        leaks = []
        printable = set(string.printable)
        while len(leaks) < 10000:
            line_raw = self.leak_file.readline()
            line = filter(lambda x: x in printable, line_raw)
            if not line:
                self.leak_file.close()
                raise StopIteration
            try:
                #res = re.findall(r'.*\:(?P<email>.*@.*)\:.*\:(?P<pass>.*)', line)
                res = re.match(monster_regexp, line).groupdict()
                if res['email'] != None:
                    email = res['email'].replace(' \t\r\n\0\\', '')
                    password = res['password'].replace(' \t\r\n\0\\', '')
                if res['email2'] != None:
                    email = res['email2'].replace(' \t\r\n\0\\', '')
                    password = res['password2'].replace(' \t\r\n\0\\', '')
                emai = email.lower()
                leaks.append(
                    {'email': email, 'password_hash': password, 'leak_source': 'exploit_in'})
            except Exception as e:
                pass
                # Write all lines, that dont go in database, so we can work with them later
                #print line,
                #with open("error.log", "w") as error_file:
                #    error_file.write(line)
        return leaks


# Need this shit to make connector work
app = Flask(__name__)
app.config.from_object("config")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)


class Leak(db.Model):
    """
    Do not change this class, because this will breack the DB connection
    """
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


def multifile_progress(file_string, current_file_index, file_count):
    return "[File: " + file_string + " | " + str(current_file_index+1) + "/" + str(file_count) + "]"


def magick_status(source, i, file_string, elapsed, timeleft, total_elapsed, current_file_index, file_count):
    return multifile_progress(file_string, current_file_index, file_count) + " " + progress_bar(i, len(source)) + " " + progress_estimate(elapsed, timeleft) + " " + progress_total(total_elapsed)


def load_fill_from_reader(source, t_start, file_string, current_file_index, file_count):
    i = 0
    database = sa.create_engine(
        SQLALCHEMY_DATABASE_URI,
        isolation_level="READ UNCOMMITTED")
    with database.begin() as connection:
        t_import_start = time.time()
        for records in source:
            # Progress tracking
            i += 1 * 10000
            elapsed = (time.time() - t_import_start) / 60
            timeleft = int(elapsed / i * len(source)) - elapsed
            total_elapsed = (time.time() - t_start) / 60
            status = magick_status(source, i, file_string, elapsed,
                                   timeleft, total_elapsed, current_file_index, file_count)
            # Same line printing
            sys.stdout.write(status)
            sys.stdout.flush()
            sys.stdout.write("\b" * (len(status)))
            # Actually db insertion
            connection.execute(sa.insert(Leak), records)
    delta_t = time.time() - t_import_start
    print "\nFile " + file_string + " imported in " + str(int(delta_t)) + " seconds"


if __name__ == "__main__":
    start_time = time.time()
    #mypath = "c:/Users/Zlooo/Documents/Exploit.in/"
    mypath = "/mnt/c/Users/Zlooo/Documents/Exploit.in/"
    #mypath = "/home/ubuntu/exploet/"
    leak_files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    leak_files = sorted(leak_files)
    for index, leak_file in enumerate(leak_files):
        load_fill_from_reader(LeaksIterator(
            mypath + leak_file), start_time, leak_file, index, len(leak_files))
