from flask import Flask, render_template, request, redirect, url_for
import random
import os
import json

app = Flask(__name__)

# 全局变量
Files = {}
data = {}
Score = {}
submit_count = 0
current_account = 'Elong'
current_key = None
current_value = None
result = None
consecutive_correct = {}
current_course = None

def load_data_from_file(file_name):
    """从文件加载数据"""
    data = {}
    try:
        with open(file_name, 'r', encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        key, value = line.strip().split('=')
                        data[key.strip()] = value.strip()
                    except ValueError:
                        print(f"Invalid line format: {line}")
    except FileNotFoundError:
        if 'score_' in file_name:
            write_dict_to_file({}, file_name)
    except Exception as e:
        print(f"Error reading {file_name}: {e}")
    return data

def write_dict_to_file(dict_data, file_name):
    """将字典数据写入文件"""
    try:
        # 确保目录存在
        directory = os.path.dirname(file_name)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # 写入文件
        with open(file_name, 'w', encoding="utf-8") as f:
            for key, value in dict_data.items():
                f.write(f"{key}={value}\n")
        print(f"Successfully wrote to file: {file_name}")  # 调试输出
    except Exception as e:
        print(f"Error writing to file {file_name}: {e}")

def get_score_file(account, course_type, chapter):
    """获取分数文件路径"""
    try:
        # 确保基础目录存在
        base_dir = "./scores"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        # 确保账号目录存在
        account_dir = os.path.join(base_dir, account)
        if not os.path.exists(account_dir):
            os.makedirs(account_dir)
        
        # 确保课程类型目录存在
        course_dir = os.path.join(account_dir, course_type)
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)
        
        # 返回完整的文件路径
        return os.path.join(course_dir, f"score_{chapter}.txt")
    except Exception as e:
        print(f"Error in get_score_file: {e}")
        # 确保返回一个有效的文件路径
        return os.path.join("./scores", f"score_{account}_{course_type}_{chapter}.txt")

def get_current_course_type():
    """获取当前课程类型"""
    if not data:
        return 'standard'
    
    # 遍历 Files 字典，找到当前加载的文件对应的键
    for key, file_path in Files.items():
        if file_path in [Files[k] for k in data.keys()]:
            return 'standard' if key.startswith('Ch') else 'dlg'
    return 'standard'

def get_current_chapter():
    """获取当前章节号"""
    if not data:
        return '0'
    
    # 遍历 Files 字典，找到当前加载的文件对应的键
    for key, file_path in Files.items():
        if file_path in [Files[k] for k in data.keys()]:
            return ''.join(filter(str.isdigit, key))
    return '0'

def format_chapter_name(file_key):
    """格式化章节名称"""
    if file_key.startswith('Ch') or file_key.startswith('DLG'):
        chapter_num = ''.join(filter(str.isdigit, file_key))
        return f"第{chapter_num}章"
    return file_key

def init_app():
    """初始化应用"""
    global Files, data, Score, current_course, consecutive_correct
    
    # 加载文件列表
    Files = load_data_from_file("./data/Files.txt")
    
    # 如果文件列表为空，使用默认值
    if not Files:
        Files = {
            "Ch_0": "./data/Ch_0.txt",
            "Ch_1": "./data/Ch_1.txt",
            "Ch_2": "./data/Ch_2.txt",
            "Ch_3": "./data/Ch_3.txt",
            "Ch_4": "./data/Ch_4.txt",
            "DLG_1": "./data/DLG_1.txt",
            "DLG_2": "./data/DLG_2.txt",
            "DLG_3": "./data/DLG_3.txt"
        }
        write_dict_to_file(Files, "./data/Files.txt")
    
    # 默认加载 DLG_1
    if "DLG_1" in Files:
        current_course = "DLG_1"
        data = load_data_from_file(Files["DLG_1"])
        score_file = get_score_file(current_account, 'dlg', '1')
        Score = load_data_from_file(score_file)
        if Score:
            Score = dict(sorted(Score.items(), key=lambda item: int(item[1]), reverse=True))
            # 根据 Score 初始化 consecutive_correct
            consecutive_correct = {key: int(value) for key, value in Score.items()}
        else:
            consecutive_correct = {}
    else:
        # 如果找不到 DLG_1，加载第一个可用的文件
        if Files:
            first_key = list(Files.keys())[0]
            current_course = first_key  # 设置当前课程
            data = load_data_from_file(Files[first_key])
            
            course_type = 'standard' if first_key.startswith('Ch') else 'dlg'
            chapter = ''.join(filter(str.isdigit, first_key))
            score_file = get_score_file(current_account, course_type, chapter)
            Score = load_data_from_file(score_file)

# 初始化应用
init_app()

def check_all_words_mastered():
    """检查是否所有单词都已掌握（连续答对10次）"""
    if not data:
        return False
    
    for key in data.keys():
        if key not in consecutive_correct or consecutive_correct[key] < 10:
            return False
    return True

def get_unmastered_word():
    """获取一个未掌握的单词（未连续答对10次的单词）"""
    if not data:
        return None, None
    
    # 过滤出未掌握的单词
    unmastered_words = {k: v for k, v in data.items() 
                       if k not in consecutive_correct or consecutive_correct[k] < 10}
    
    # 如果还有未掌握的单词，随机选择一个
    if unmastered_words:
        random_item = random.choice(list(unmastered_words.items()))
        return random_item[0], random_item[1]
    
    # 如果所有单词都已掌握，返回 None
    return None, None

def get_word_file(account, course_type, chapter):
    """获取单词文件路径"""
    base_dir = 'data'
    return os.path.join(base_dir, account, course_type, f'Ch{chapter}.json')

@app.route('/', methods=['GET', 'POST'])
def index():
    global Score, data, current_key, current_value, result, submit_count, consecutive_correct
    
    if current_key is None and data:
        current_key, current_value = get_unmastered_word()
        if current_key is None:
            mastered = True
        
    mastered = check_all_words_mastered() if data else False

    if request.method == 'POST':
        input_value = request.form.get('input_value')
        
        if input_value == current_value:
            result = "Correct!"
            if current_key in Score:
                Score[current_key] = str(int(Score[current_key]) + 1)
            else:
                Score[current_key] = "1"
            
            if current_key in consecutive_correct:
                consecutive_correct[current_key] += 1
            else:
                consecutive_correct[current_key] = 1
                
            submit_count += 1
            
            # 选择新的未掌握单词
            current_key, current_value = get_unmastered_word()
        else:
            result = f"你输入的：{input_value}，正确的 {current_key} 的值是：{current_value}"
            consecutive_correct[current_key] = 0
            Score[current_key] = "0"  # 答错时重置分数为0
        
        # 每次提交后对分数进行排序
        Score = dict(sorted(Score.items(), key=lambda item: int(item[1]), reverse=True))

        # 每5次保存一次分数
        if submit_count >= 5:
            try:
                if current_course:
                    course_type = 'standard' if current_course.startswith('Ch') else 'dlg'
                    chapter = ''.join(filter(str.isdigit, current_course))
                    score_file = get_score_file(current_account, course_type, chapter)
                    print(f"Saving scores to: {score_file}")
                    write_dict_to_file(Score, score_file)
                submit_count = 0
            except Exception as e:
                print(f"Error saving scores: {e}")
                submit_count = 0

    return render_template('index.html', 
                         current_key=current_key,
                         current_value=current_value,
                         Score=Score,
                         data=data,
                         result=result,
                         Files=Files,
                         format_chapter=format_chapter_name,
                         current_account=current_account,
                         mastered=mastered,
                         submit_count=submit_count,
                         current_course=current_course,
                         input_value=request.form.get('input_value') if request.method == 'POST' else None)

@app.route('/switch_account', methods=['POST'])
def switch_account():
    """处理账号切换"""
    global current_account, Score
    try:
        current_account = request.form.get('account', 'Elong')
        
        # 获取当前课程类型和章节
        course_type = 'standard'
        chapter = '0'
        
        # 如果有当前数据，从当前数据确定课程类型和章节
        if data:
            for key in Files:
                if key in data:
                    course_type = 'standard' if key.startswith('Ch') else 'dlg'
                    chapter = ''.join(filter(str.isdigit, key))
                    break
        
        # 加载对应的分数文件
        score_file = get_score_file(current_account, course_type, chapter)
        Score = load_data_from_file(score_file)
        
        # 如果有分数数据，进行排序
        if Score:
            Score = dict(sorted(Score.items(), key=lambda item: int(item[1]), reverse=True))
        else:
            Score = {}
            
        print(f"Switched to account: {current_account}, loading scores from: {score_file}")  # 调试输出
        
    except Exception as e:
        print(f"Error in switch_account: {e}")  # 调试输出
        Score = {}
    
    return redirect(url_for('index'))

@app.route('/load_file', methods=['POST'])
def load_file():
    global data, Score, consecutive_correct, current_course, current_key, current_value
    selected_file = request.form.get('Ch')
    print(f"Switching to course: {selected_file}")
    
    if selected_file in Files:
        current_course = selected_file
        print(f"Current course set to: {current_course}")
        
        # 加载新课程的数据
        data = load_data_from_file(Files[selected_file])
        
        # 重置当前题目
        if data:
            random_item = random.choice(list(data.items()))
            current_key = random_item[0]
            current_value = random_item[1]
        else:
            current_key = None
            current_value = None
        
        # 加载对应的分数文件
        course_type = 'standard' if selected_file.startswith('Ch') else 'dlg'
        chapter = ''.join(filter(str.isdigit, selected_file))
        score_file = get_score_file(current_account, course_type, chapter)
        Score = load_data_from_file(score_file)
        if Score:
            Score = dict(sorted(Score.items(), key=lambda item: int(item[1]), reverse=True))
            # 根据 Score 初始化 consecutive_correct
            consecutive_correct = {key: int(value) for key, value in Score.items()}
        else:
            Score = {}
            consecutive_correct = {}
            
        print(f"New question loaded: {current_key} = {current_value}")
    
    return redirect(url_for('index'))

@app.route('/exam')
def exam():
    """考试页面"""
    global current_account, current_course, Files
    
    # 确保 Files 已初始化
    if not Files:
        Files = get_files()
    
    # 确保有当前账号和课程
    if not current_account or not current_course:
        return redirect(url_for('index'))
        
    # 获取当前课程的单词数据
    course_type = 'standard' if current_course.startswith('Ch') else 'dlg'
    chapter = ''.join(filter(str.isdigit, current_course))
    word_file = get_word_file(current_account, course_type, chapter)
    
    try:
        with open(word_file, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
    except:
        exam_data = {}
        
    return render_template('exam.html', 
                         data=exam_data,
                         current_account=current_account,
                         current_course=current_course,
                         Files=Files,
                         format_chapter=format_chapter_name)

@app.route('/start_exam', methods=['POST'])
def start_exam():
    chapter = request.form.get('exam_ch')
    if not chapter or chapter not in Files:
        return redirect(url_for('exam'))
    
    questions = {}
    try:
        file_path = Files[chapter]
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                if line.strip():
                    try:
                        question, answer = line.strip().split('=')
                        questions[str(idx)] = {
                            'question': question.strip(),
                            'answer': answer.strip()
                        }
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error loading exam questions: {e}")
        return redirect(url_for('exam'))
    
    return render_template('exam.html',
                         current_account=current_account,
                         Files=Files,
                         questions=questions,
                         current_chapter=chapter)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    current_chapter = request.form.get('chapter')
    if not current_chapter:
        return redirect(url_for('exam'))
    
    submitted_answers = {}
    wrong_answers = set()
    correct_count = 0
    questions = {}
    
    try:
        file_path = Files[current_chapter]
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                if line.strip():
                    try:
                        question, answer = line.strip().split('=')
                        questions[str(idx)] = {
                            'question': question.strip(),
                            'answer': answer.strip()
                        }
                        
                        # 检查答案
                        user_answer = request.form.get(f'answer_{idx}', '').strip()
                        submitted_answers[str(idx)] = user_answer
                        if user_answer != answer.strip():
                            wrong_answers.add(str(idx))
                        else:
                            correct_count += 1
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error checking exam answers: {e}")
        return redirect(url_for('exam'))
    
    return render_template('exam.html',
                         current_account=current_account,
                         Files=Files,
                         questions=questions,
                         results=True,
                         submitted_answers=submitted_answers,
                         wrong_answers=wrong_answers,
                         correct_count=correct_count,
                         total_questions=len(questions),
                         current_chapter=current_chapter)

@app.route('/switch_course', methods=['POST'])
def switch_course():
    global data, Score, consecutive_correct, current_course
    selected_course = request.form.get('course')
    
    if selected_course in Files:
        # 更新当前课程
        current_course = selected_course
        
        # 加载课程数据
        data = load_data_from_file(Files[selected_course])
        
        # 确定课程类型和章节
        course_type = 'standard' if selected_course.startswith('Ch') else 'dlg'
        chapter = ''.join(filter(str.isdigit, selected_course))
        
        # 加载对应的分数文件
        score_file = get_score_file(current_account, course_type, chapter)
        Score = load_data_from_file(score_file)
        if Score:
            Score = dict(sorted(Score.items(), key=lambda item: int(item[1]), reverse=True))
        else:
            Score = {}
            
        # 重置连续答对记录
        consecutive_correct = {}
    
    return redirect(url_for('index'))

@app.route('/test')
def test():
    """考试页面"""
    return render_template('test.html')

@app.route('/review')
def review():
    """复习错题页面"""
    return render_template('review.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)