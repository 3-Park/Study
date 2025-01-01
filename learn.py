from flask import Flask, render_template, jsonify, request, session
from models import db, Course, Word, User, Score
import os
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS  # 直接导入配置常量

def create_app():
    app = Flask(__name__)
    # 直接使用配置文件中的常量
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.secret_key = 'your-secret-key-here'
    
    db.init_app(app)
    return app

app = create_app()

@app.route('/')
def index():
    try:
        # 从数据库获取所有课程信息并转换为字典
        courses = [course.to_dict() for course in Course.query.all()]
        print("Courses from database:", courses)
        return render_template('index.html', courses=courses)
    except Exception as e:
        print("Error fetching courses:", str(e))
        return render_template('index.html', courses=[])

@app.route('/switch_account', methods=['POST'])
def switch_account():
    data = request.get_json()
    session['current_account'] = data['account']
    return jsonify({"status": "success"})

@app.route('/get_words/<int:chapter_id>')
def get_words(chapter_id):
    try:
        # 直接通过 chapter_id 查询 t_words 表
        words = Word.query.filter_by(chapter_id=chapter_id).all()
        
        # 将查询结果转换为字典列表作为单词库
        word_list = [{
            'word': word.word,
            'answerA': word.answerA,
            'answerB': word.answerB
        } for word in words]
        
        return jsonify(word_list)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.get_json()
    # 这里应该保存分数到数据库
    return jsonify({"status": "success"})

@app.route('/api/get_courses/<language>')
def get_courses_by_language(language):
    courses = db.session.query(Course.course).filter_by(language=language).distinct().all()
    courses = [course[0] for course in courses]
    return jsonify(courses)

@app.route('/api/get_chapters/<language>/<course>')
def get_chapters_by_course(language, course):
    chapters = Course.query.filter_by(language=language, course=course).all()
    chapter_list = [{
        'id': chapter.chapter_id,
        'chapter': chapter.chapter
    } for chapter in chapters]
    return jsonify(chapter_list)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        
        # 查找用户
        user = User.query.filter_by(email=email).first()
        
        if user:
            # 用户存在，直接登录
            session['user_id'] = user.id
            session['email'] = user.email
            session['username'] = user.username
            return jsonify({
                'status': 'success',
                'message': '登录成功',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username
                }
            })
        else:
            # 用户不存在，创建新用户
            new_user = User(
                email=email,
                username='Newbee'
            )
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['email'] = new_user.email
            session['username'] = new_user.username
            
            return jsonify({
                'status': 'success',
                'message': '新用户创建成功',
                'user': {
                    'id': new_user.id,
                    'email': new_user.email,
                    'username': new_user.username
                }
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/update_username', methods=['POST'])
def update_username():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_username = data.get('new_username')
        
        user = User.query.get(user_id)
        if user:
            user.username = new_username
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': '用户名更新成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/record_answer', methods=['POST'])
def record_answer():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        chapter_id = data.get('chapter_id')
        word = data.get('word')
        is_correct = data.get('is_correct')
        
        # 查找或创建记录
        score = Score.query.filter_by(
            user_id=user_id,
            chapter_id=chapter_id,
            word=word
        ).first()
        
        if score:
            # 更新现有记录
            if is_correct:
                score.streak += 1
            else:
                score.streak = 0
        else:
            # 创建新记录
            score = Score(
                user_id=user_id,
                chapter_id=chapter_id,
                word=word,
                streak=1 if is_correct else 0
            )
            db.session.add(score)
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'streak': score.streak
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_word_scores/<int:chapter_id>/<int:user_id>')
def get_word_scores(chapter_id, user_id):
    try:
        # 获取每个单词的正确答题总次数
        scores = db.session.query(
            Score.word,
            db.func.sum(db.case(
                [(Score.streak > 0, 1)],
                else_=0
            )).label('correct_count')
        ).filter(
            Score.chapter_id == chapter_id,
            Score.user_id == user_id
        ).group_by(Score.word).all()
        
        # 转换为字典格式
        score_dict = {score.word: score.correct_count for score in scores}
        
        return jsonify({
            'status': 'success',
            'scores': score_dict
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=53720)