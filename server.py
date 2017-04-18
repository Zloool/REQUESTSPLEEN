import os

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from validate_email import validate_email

from password import SQLALCHEMY_DATABASE_URI
import config


app = Flask(__name__)
app.config.from_object("config")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)


class Leak(db.Model):
    __tablename__ = 'LEAKS'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String())
    password = db.Column(db.String())
    password_hash = db.Column(db.String())
    name = db.Column(db.String())
    nickname = db.Column(db.String())
    leak_source = db.Column(db.String())

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


@app.route("/")
def homepage():
    search_query = request.args.get("srch")
    if not search_query:
        return render_template('home.html')
    else:
		if validate_email(search_query):
			res = Leak.query.filter_by(search_query=search_query).all()
			return render_template('home.html', search_query=search_query, source=res)
		else:
			res = Leak.query.filter(Leak.message.like(search_query+"%")).all()
			return render_template('home.html', search_query=search_query, source=res)

if __name__ == '__main__':
    app.run(debug=True)
