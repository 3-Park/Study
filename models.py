from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 只创建db实例，不初始化
db = SQLAlchemy()

def get_or_create_table(cls):
    table_name = cls.__tablename__
    if table_name in db.Model.metadata.tables:
        db.Model.metadata.remove(db.Model.metadata.tables[table_name])
    return cls

@get_or_create_table
class User(db.Model):
    __tablename__ = 't_users'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    lastlogin = db.Column(db.DateTime, default=datetime.now)

@get_or_create_table
class Course(db.Model):
    __tablename__ = 't_courses'
    __table_args__ = {'extend_existing': True}
    chapter_id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(50))
    course = db.Column(db.String(50))
    chapter = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'chapter_id': self.chapter_id,
            'language': self.language,
            'course': self.course,
            'chapter': self.chapter
        }

@get_or_create_table
class Word(db.Model):
    __tablename__ = 't_words'
    __table_args__ = {'extend_existing': True}
    chapter_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), primary_key=True)
    answerA = db.Column(db.String(200), nullable=False)
    answerB = db.Column(db.String(200), nullable=False)

@get_or_create_table
class Score(db.Model):
    __tablename__ = 't_scores'
    __table_args__ = {'extend_existing': True}
    user_id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), primary_key=True)
    streak = db.Column(db.Integer, default=0) 

@get_or_create_table
class Exams(db.Model):
    __tablename__ = 't_exams'
    __table_args__ = {'extend_existing': True}
    user_id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, primary_key=True)
    exam_date = db.Column(db.DateTime, default=datetime.now) 