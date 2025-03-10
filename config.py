import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secure-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QUIZES_PER_PAGE = 9