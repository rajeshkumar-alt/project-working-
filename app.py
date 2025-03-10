from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Create admin user if not exists
    with app.app_context():
        db.create_all()
        create_admin_user()
    
    return app

def create_admin_user():
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            email='admin@quizmaster.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# Import models after db initialization
from models import User, Subject, Chapter, Quiz, Question, QuizAttempt

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Main Routes
@app.route('/')
def index():
    return render_template('main/index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        subjects = Subject.query.all()
        return render_template('admin/dashboard.html', subjects=subjects)
    else:
        quizzes = Quiz.query.all()
        return render_template('user/dashboard.html', quizzes=quizzes)

# Admin Routes
@app.route('/admin/subjects', methods=['GET', 'POST'])
@login_required
def manage_subjects():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        subject = Subject(name=request.form['name'])
        db.session.add(subject)
        db.session.commit()
        return redirect(url_for('manage_subjects'))
    
    subjects = Subject.query.all()
    return render_template('admin/manage_subjects.html', subjects=subjects)

@app.route('/admin/chapters/<int:subject_id>', methods=['POST'])
@login_required
def add_chapter(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    subject = Subject.query.get_or_404(subject_id)
    chapter = Chapter(name=request.form['name'], subject=subject)
    db.session.add(chapter)
    db.session.commit()
    return redirect(url_for('manage_subjects'))

@app.route('/admin/quizzes', methods=['GET', 'POST'])
@login_required
def manage_quizzes():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        quiz = Quiz(
            title=request.form['title'],
            duration=int(request.form['duration']),
            chapter_id=int(request.form['chapter_id'])
        )
        db.session.add(quiz)
        db.session.commit()
        return redirect(url_for('manage_quizzes'))
    
    quizzes = Quiz.query.all()
    chapters = Chapter.query.all()
    return render_template('admin/manage_quizzes.html', quizzes=quizzes, chapters=chapters)

# Quiz API
@app.route('/api/quiz/<int:quiz_id>')
def get_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return jsonify({
        'id': quiz.id,
        'title': quiz.title,
        'duration': quiz.duration,
        'questions': [{
            'text': q.text,
            'options': [q.option1, q.option2, q.option3, q.option4],
            'correct': q.correct_option
        } for q in quiz.questions]
    })

# Quiz Attempts
@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        score = calculate_score(request.form, quiz.questions)
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            score=score
        )
        db.session.add(attempt)
        db.session.commit()
        return redirect(url_for('quiz_results', attempt_id=attempt.id))
    
    return render_template('main/quiz.html', quiz=quiz)

def calculate_score(answers, questions):
    correct = 0
    for i, question in enumerate(questions, 1):
        if str(question.correct_option) == answers.get(f'question_{i}'):
            correct += 1
    return int((correct / len(questions)) * 100)

if __name__ == '__main__':
    app.run(debug=True)

    