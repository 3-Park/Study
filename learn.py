from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from models import db, Course, Word, User, Score, Exams  # 添加 Exams 的导入
import os
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS  # 直接导入配置常量
from datetime import datetime

def create_app():
    app = Flask(__name__)
    # 直接使用配置文件中的常量
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.secret_key = 'abcdefg'
    
    db.init_app(app)
    return app

app = create_app()

@app.route('/')
@app.route('/index')  # 添加 /index 路由
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
    try:
        data = request.get_json()
        score = data.get('score')
        user_id = data.get('user_id')
        chapter_id = data.get('chapter_id')
        exam_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"准备保存到数据库: user_id={user_id}, course_id={chapter_id}, score={score}, exam_date={exam_date}")
        
        new_exam = Exams(
            user_id=user_id,
            chapter_id=chapter_id,
            score=score,
            exam_date=exam_date
        )
        db.session.add(new_exam)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"保存分数时出错: {str(e)}")
        return jsonify({'success': False})

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
        
        if not email:
            return jsonify({
                'status': 'error',
                'message': '请输入邮箱地址'
            })

        # 查询用户是否存在
        user = User.query.filter_by(email=email).first()
        
        if user:
            # 用户存在，返回用户信息
            return jsonify({
                'status': 'success',
                'user_id': user.id,
                'username': user.username,
                'email': user.email
            })
        else:
            # 用户不存在，创建新用户
            new_user = User(email=email, username=email.split('@')[0])  # 使用邮箱前缀作为用户名
            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'user_id': new_user.id,
                'username': new_user.username,
                'email': new_user.email
            })
            
    except Exception as e:
        print("Login error:", str(e))
        return jsonify({
            'status': 'error',
            'message': '服务器错误，请重试'
        }), 500

@app.route('/update_username', methods=['POST'])
def update_username():
    user_id = request.form.get('userId')
    new_username = request.form.get('newUsername')
    print(f"更新用户信息：user_id={user_id}, new_username={new_username}")
    
    # 更新数据库
    user = User.query.filter_by(id=user_id).first()
    if user:
        user.username = new_username
        db.session.commit()
        print("数据库更新成功")
    
    return '更新成功'

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

@app.route('/get_user_scores', methods=['GET'])
def get_user_scores():
    try:
        user_id = request.args.get('user_id')
        chapter_id = request.args.get('chapter_id')
        
        if not user_id or not chapter_id:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            })

        # 查询用户在特定章节的分数记录，按streak降序排序
        scores = Score.query.filter_by(
            user_id=user_id,
            chapter_id=chapter_id
        ).order_by(Score.streak.desc()).all()
        
        score_list = [{
            'word': score.word,
            'streak': score.streak
        } for score in scores]
        
        return jsonify({
            'status': 'success',
            'scores': score_list
        })
        
    except Exception as e:
        print("Error getting scores:", str(e))
        return jsonify({
            'status': 'error',
            'message': '获取分数记录失败'
        })

@app.route('/exam', methods=['GET', 'POST'])
def exam():
    print("进入exam路由")
    print(f"请求方法: {request.method}")
    print(f"当前session内容: {session}")
    
    if request.method == 'POST':
        # 打印完整的表单数据
        print(f"完整的POST数据: {request.form}")
        
        user_id = request.form.get('userId')
        chapter_id = request.form.get('chapterId')
        
        print(f"解析后的数据: user_id={user_id}, chapter_id={chapter_id}")
        
        error_msg = []
        if not user_id:
            error_msg.append("缺少用户ID")
        if not chapter_id:
            error_msg.append("缺少章节ID")
            
        if error_msg:
            # 返回错误信息而不是重定向
            error_details = " | ".join(error_msg)
            return f"POST请求参数不完整: {error_details}", 400
        
        try:
            session.clear()
            session['user_id'] = user_id
            session['chapter_id'] = chapter_id
            session.modified = True
            
            print(f"存入session后的内容: {session}")
            return redirect('/exam')
            
        except Exception as e:
            # 返回错误信息而不是重定向
            return f"Session存储错误: {str(e)}", 500
            
    else:  # GET请求
        print("处理GET请求")
        #print(f"GET请求时的session内容: {session}")
        
        try:
            user_id = session.get('user_id')
            chapter_id = session.get('chapter_id')
            
            print(f"从session获取的数据: user_id={user_id}, chapter_id={chapter_id}")
            
            if not user_id or not chapter_id:
                # 返回错误信息而不是重定向
                return "Session中缺少必要数据", 400
                
            # 获取用户信息
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return f"未找到用户: {user_id}", 404
            
            # 获取课程信息
            chapter = Course.query.filter_by(chapter_id=chapter_id).first()
            if not chapter:
                return f"未找到章节: {chapter_id}", 404
                
            course_info = f"{chapter.language} - {chapter.course} - {chapter.chapter}"
            
            # 获取该章节的所有单词
            words = Word.query.filter_by(chapter_id=chapter_id).all()
            print(f"获取到 {len(words)} 个单词")
            
            # 获取最近3次考试记录
            recent_exams = Exams.query.filter_by(
                user_id=session.get('user_id'),
                chapter_id=session.get('chapter_id')
            ).order_by(Exams.exam_date.desc())\
                .limit(3)\
                .all()
            
            result = render_template('exam.html',
                                  user=user,
                                  user_id=user_id,
                                  chapter_id=chapter_id,
                                  course_info=course_info,
                                  words=words,
                                  recent_exams=recent_exams)
                                  
            session.clear()
            return result
            
        except Exception as e:
            # 返回错误信息而不是重定向
            return f"处理GET请求时发生错误: {str(e)}", 500
        
@app.route('/score_sheet', methods=['POST'])
def score_sheet():
    user_id = request.form.get('user_id')
    
    # 获取用户信息
    user = User.query.filter_by(id=user_id).first()
    
    # 使用子查询获取每个章节的最新考试记录
    latest_exams = db.session.query(
        Exams.chapter_id,
        db.func.max(Exams.exam_date).label('max_date')
    ).filter(
        Exams.user_id == user_id
    ).group_by(
        Exams.chapter_id
    ).subquery()
    
    # 主查询关联最新记录，按chapter_id排序
    exams = db.session.query(
        Course.language, Course.course, Course.chapter,
        Exams.score, Exams.exam_date
    ).join(
        Course, Exams.chapter_id == Course.chapter_id
    ).join(
        latest_exams, 
        db.and_(
            Exams.chapter_id == latest_exams.c.chapter_id,
            Exams.exam_date == latest_exams.c.max_date
        )
    ).filter(
        Exams.user_id == user_id
    ).order_by(
        Course.chapter_id
    ).all()
        
    return render_template('score_sheet.html', 
                         user_id=user_id, 
                         username=user.username,
                         email=user.email,
                         exams=exams)

if __name__ == '__main__':
    app.run(debug=True, port=53720)