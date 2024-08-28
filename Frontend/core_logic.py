import streamlit as st
from datetime import datetime, timedelta
import secrets
import os
from streamlit_cookies_manager import EncryptedCookieManager
from file_handlers import load_documents
from question_generation import emergency_stop, transcribe_video_file, transcribe_audio_file, generate_questions_batch
import database
from database import *
from utils import create_csv, check_answer
import langchain
import pandas as pd
import numpy as np
import json
import random
import time

# Session state initialization
def init_session_state():
    if 'mode' not in st.session_state:
        st.session_state.mode = None
    if 'docs' not in st.session_state:
        st.session_state.docs = None
    if 'questions' not in st.session_state:
        st.session_state.questions = None
    if 'answers' not in st.session_state:
        st.session_state.answers = None
    if 'current_question_type' not in st.session_state:
        st.session_state.current_question_type = None
    if 'video_processed' not in st.session_state:
        st.session_state.video_processed = False
    if 'file_processed' not in st.session_state:
        st.session_state.file_processed = False
    if 'selected_questions' not in st.session_state:
        st.session_state.selected_questions = []
    if 'selected_checkboxes' not in st.session_state:
        st.session_state.selected_checkboxes = {}
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "전체"
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'room_authenticated' not in st.session_state:
        st.session_state.room_authenticated = False
    if 'file_processed' not in st.session_state:
        st.session_state.file_processed = False
    if 'show_info' not in st.session_state:
        st.session_state.show_info = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user' not in st.session_state:
        st.session_state.user = None

# Cookie manager initialization
cookies = EncryptedCookieManager(
    prefix="llm_quiz/config/",
    password=os.environ.get("COOKIES_PASSWORD", "password"),
)
if not cookies.ready():
    st.stop()

def init_cookies():
    if not cookies.ready():
        st.warning("Cookies are not ready. Please refresh the page.")
        st.stop()

def set_auth_cookie(user_id, remember_me=False):
    init_cookies()
    token = secrets.token_hex(16)
    if remember_me:
        expiry = datetime.now() + timedelta(days=30)
    else:
        expiry = datetime.now() + timedelta(hours=1)
    
    cookies['auth_token'] = f"{user_id}:{token}:{expiry.timestamp()}"
    cookies.save()

def validate_auth_cookie():
    if 'auth_token' in cookies:
        try:
            user_id, token, expiry = cookies['auth_token'].split(':')
            if float(expiry) > datetime.now().timestamp():
                return int(user_id)
        except:
            pass
    return None

def logout():
    st.session_state.clear()
    st.session_state.mode = None
    if 'auth_token' in cookies:
        del cookies['auth_token']
        cookies.save()

def check_if_admin(user_id):
    user_info = database.get_user_info(user_id)
    return user_info and user_info.get('student_id') == '1234'

def restore_user_session():
    user_id = validate_auth_cookie()
    if user_id is not None:
        st.session_state['user_id'] = user_id
        st.session_state['user'] = get_user_info(user_id)
        st.session_state.is_admin = check_if_admin(user_id)
        if st.session_state.mode is None:
            st.session_state.mode = "default"
    else:
        st.session_state['user_id'] = None
        st.session_state['user'] = None
        st.session_state['mode'] = None
        st.session_state.is_admin = False

def authenticate_user(name, password):
    return database.authenticate_user(name, password)

def register_user(name, password, email, student_id):
    return database.register_user(name, password, email, student_id)

def create_questions(subject, subtopics_data):
    st.session_state.questions = {}
    st.session_state.answers = {}
    st.session_state.extra_questions = {}
    st.session_state.question_types = []

    for subtopic_name, data in subtopics_data.items():
        subtopic_file = data["file"]
        subtopic_question_types = data["question_types"]

        if subtopic_file is not None:
            file_extension = subtopic_file.name.split('.')[-1].lower()
            save_uploadedfile(subtopic_file)
            subtopic_file.name = "".join([c for c in subtopic_file.name if c.isalnum() or c in ['_', '-', '.']]).rstrip()

            if file_extension in ['mp4', 'mp3', 'wav', "m4a"]:
                if file_extension == 'mp4':
                    extracted_text = transcribe_video_file(f"tmp/{subtopic_file.name}")
                else:
                    extracted_text = transcribe_audio_file(f"tmp/{subtopic_file.name}")

                if extracted_text:
                    docs = [langchain.schema.Document(page_content=extracted_text)]
                else:
                    return f"{subtopic_name}의 파일 처리 중 오류가 발생했습니다."
            else:
                docs = load_documents(subtopic_file)

            if docs:
                try:
                    increased_question_types = {qt: int(num * 1.5) for qt, num in subtopic_question_types.items()}
                    all_questions, all_answers, additional_questions = generate_questions_batch(
                        docs=docs,
                        subtopic_question_types={subtopic_name: increased_question_types}
                    )

                    st.session_state.questions[subtopic_name] = {}
                    st.session_state.answers[subtopic_name] = {}
                    st.session_state.extra_questions[subtopic_name] = {}

                    for qt, questions in all_questions[subtopic_name].items():
                        answers = all_answers[subtopic_name][qt]
                        num_required = subtopic_question_types[qt]
                        
                        st.session_state.questions[subtopic_name][qt] = questions[:num_required]
                        st.session_state.answers[subtopic_name][qt] = answers[:num_required]
                        st.session_state.question_types.extend([qt] * num_required)
                        
                        st.session_state.extra_questions[subtopic_name][qt] = list(zip(questions[num_required:], answers[num_required:]))

                except Exception as e:
                    return f"{subtopic_name}의 문제 생성 중 오류가 발생했습니다: {str(e)}"
            else:
                return f"{subtopic_name}의 파일 처리 중 오류가 발생했습니다."
        else:
            return f"{subtopic_name}의 파일이 업로드되지 않았습니다."

    if st.session_state.questions and st.session_state.answers:
        st.session_state.questions_generated = True
        return "success"
    else:
        return "문제 생성 결과가 없습니다. 다시 시도해 주세요."

def save_questions_to_database(user_id, subject, subtopic_name):
    for qt, questions in st.session_state.questions[subtopic_name].items():
        answers = st.session_state.answers[subtopic_name][qt]
        questions_to_save = []
        for question in questions:
            if isinstance(question, tuple):
                questions_to_save.append((subtopic_name, question))
            else:
                questions_to_save.append((subtopic_name, (question, None)))

        if not save_questions_to_db(questions_to_save, answers, user_id, qt, subject, subtopic_name):
            return False
    return True

def regenerate_question(subtopic_name, question_type, index):
    if st.session_state.extra_questions[subtopic_name].get(question_type):
        new_question, new_answer = st.session_state.extra_questions[subtopic_name][question_type].pop(0)
        st.session_state.questions[subtopic_name][question_type][index] = new_question
        st.session_state.answers[subtopic_name][question_type][index] = new_answer
        return True
    return False

def delete_question(subtopic_name, question_type, index):
    st.session_state.questions[subtopic_name][question_type].pop(index)
    st.session_state.answers[subtopic_name][question_type].pop(index)
    st.session_state.question_types.pop(index)

def select_random_questions(categorized_questions, selected_subjects, selected_subtopics, total_questions):
    questions_by_type = {
        "multiple-choice": [],
        "short answer": [],
        "true/false": [],
        "fill-in-the-blank": [],
        "기타": []
    }

    for subject in selected_subjects:
        for subtopic in selected_subtopics:
            if subtopic in categorized_questions.get(subject, {}):
                for q in categorized_questions[subject][subtopic]:
                    q_type = q.get('question_type', '기타')
                    if q_type in questions_by_type:
                        questions_by_type[q_type].append(q)
                    else:
                        questions_by_type['기타'].append(q)

    selected_questions = []
    available_types = [t for t in questions_by_type if questions_by_type[t]]
    
    while len(selected_questions) < total_questions and available_types:
        q_type = random.choice(available_types)
        if questions_by_type[q_type]:
            question = random.choice(questions_by_type[q_type])
            selected_questions.append(question)
            questions_by_type[q_type].remove(question)
        if not questions_by_type[q_type]:
            available_types.remove(q_type)
    
    return selected_questions

def create_room(room_name, user_id, selected_question_ids, room_password, start_datetime, end_datetime):
    return db_create_room(room_name, user_id, selected_question_ids, room_password, start_datetime, end_datetime)

def categorize_questions_by_type(questions):
    questions_by_type = {
        "객관식": [],
        "주관식": [],
        "참/거짓": [],
        "빈칸 채우기": [],
        "기타": []
    }
    
    type_mapping = {
        "multiple-choice": "객관식",
        "short answer": "주관식",
        "true/false": "참/거짓",
        "fill-in-the-blank": "빈칸 채우기"
    }
    
    for q in questions:
        q_type = type_mapping.get(q.get('question_type'), '기타')
        questions_by_type[q_type].append(q)
    
    return questions_by_type

def get_room_results(room_id):
    participants = get_room_participants(room_id)
    if participants:
        df = pd.DataFrame(participants)
        df['rank'] = df['score'].rank(method='min', ascending=False)
        df = df.sort_values('rank')
        
        avg_score = df['score'].mean()
        total_participants = len(participants)
        avg_correct = df['correct_answers'].mean()
        avg_total = df['total_questions'].mean()
        
        return df, avg_score, total_participants, avg_correct, avg_total
    return None, 0, 0, 0, 0

def get_question_stats(room_id):
    all_question_data = get_all_question_data(room_id)
    if all_question_data:
        for question_data in all_question_data:
            total_answers = question_data['total_answers']
            correct_answers = question_data['correct_answers']
            question_data['correct_ratio'] = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        return all_question_data
    return None

def handle_room_authentication(room_id, password):
    return authenticate_room(room_id, password)

def get_user_room_answers(user_id, room_id):
    return get_user_answers(user_id, room_id)

def save_user_room_answers(user_id, room_id, answers):
    return save_participant_answers(user_id, room_id, answers)

def calculate_user_score(user_id, room_id):
    result = get_user_answers(user_id, room_id)
    if result:
        save_score(user_id, room_id, result['percentage_score'], result['total_questions'], result['score'])
    return result

def get_previous_learning_records(user_id, start_date, end_date, subject, subtopic):
    data = get_user_questions(user_id, start_date, end_date, subject, subtopic)
    #st.write(data)
    return data

def solve_previous_question(question_id, user_answer):
    question = get_question_by_id(question_id)
    if question is None:
        return False, "문제를 찾을 수 없습니다.", "문제를 찾을 수 없습니다."
    
    is_correct = check_answer(user_answer, question['answer_text'], question['question_type'])
    update_personal_study_answer(question_id, user_answer, is_correct)
    return is_correct, question['answer_text'], question['explanation']

def create_personal_questions(user_id, subject, subtopics_data):
    st.session_state.personal_questions = {}
    st.session_state.personal_answers = {}
    st.session_state.personal_extra_questions = {}
    st.session_state.personal_question_types = []
    st.session_state.extracted_text = {}

    for subtopic_name, data in subtopics_data.items():
        subtopic_file = data["file"]
        subtopic_question_types = data["question_types"]
        st.session_state.personal_questions[subtopic_name] = {}

        if subtopic_file is not None:
            file_extension = subtopic_file.name.split('.')[-1].lower()
            save_uploadedfile(subtopic_file)
            subtopic_file.name = "".join([c for c in subtopic_file.name if c.isalnum() or c in ['_', '-', '.']]).rstrip()

            if file_extension in ['mp4', 'mp3', 'wav', "m4a"]:
                if file_extension == 'mp4':
                    extracted_text = transcribe_video_file(f"tmp/{subtopic_file.name}")
                else:
                    extracted_text = transcribe_audio_file(f"tmp/{subtopic_file.name}")

                if extracted_text:
                    st.session_state.extracted_text[subtopic_name] = extracted_text
                    docs = [langchain.schema.Document(page_content=extracted_text)]
                else:
                    return f"{subtopic_name}의 파일 처리 중 오류가 발생했습니다."
            else:
                docs = load_documents(subtopic_file)

            if docs:
                try:
                    increased_question_types = {qt: int(num * 1.5) for qt, num in subtopic_question_types.items()}
                    all_questions, all_answers, additional_questions = generate_questions_batch(
                        docs=docs,
                        subtopic_question_types={subtopic_name: increased_question_types}
                    )

                    st.session_state.personal_questions[subtopic_name] = {}
                    st.session_state.personal_answers[subtopic_name] = {}
                    st.session_state.personal_extra_questions[subtopic_name] = {}

                    for qt, questions in all_questions[subtopic_name].items():
                        answers = all_answers[subtopic_name][qt]
                        num_required = subtopic_question_types[qt]
                        
                        st.session_state.personal_questions[subtopic_name][qt] = []
                        st.session_state.personal_answers[subtopic_name][qt] = []

                        for q, a in zip(questions[:num_required], answers[:num_required]):
                            question_data = {
                                'user_id': user_id,
                                'question_text': q[0] if isinstance(q, tuple) else q,
                                'choices': q[1] if isinstance(q, tuple) and len(q) > 1 else None,
                                'answer_text': a.split('\n')[0].replace('정답: ', '').strip(),
                                'explanation': a.split('\n', 1)[1].replace('해설: ', '').strip() if '\n' in a else '',
                                'question_type': qt,
                                'subject': subject,
                                'subtopic': subtopic_name,
                                'user_answer': None,
                                'is_correct': None
                            }
                            question_id = save_personal_study_question(question_data)
                            if question_id:
                                question_data['id'] = question_id
                                st.session_state.personal_questions[subtopic_name][qt].append(question_data)
                                st.session_state.personal_answers[subtopic_name][qt].append(a)

                        st.session_state.personal_question_types.extend([qt] * num_required)                        
                        st.session_state.personal_extra_questions[subtopic_name][qt] = list(zip(questions[num_required:], answers[num_required:]))

                except Exception as e:
                    return f"{subtopic_name}의 문제 생성 중 오류가 발생했습니다: {str(e)}"
            else:
                return f"{subtopic_name}의 파일 처리 중 오류가 발생했습니다."
        else:
            return f"{subtopic_name}의 파일이 업로드되지 않았습니다."

    if st.session_state.personal_questions and st.session_state.personal_answers:
        st.session_state.questions_generated = True 
        return True
    return False


def regenerate_personal_question(subtopic_name, question_type, index):
    # 이 함수는 regenerate_question과 유사하지만 'personal_questions'를 사용합니다.

    if subtopic_name in st.session_state.personal_questions and question_type in st.session_state.personal_questions[subtopic_name]:
        new_question, new_answer = st.session_state.personal_extra_questions[subtopic_name][question_type].pop(0)
        st.session_state.personal_questions[subtopic_name][question_type][index] = new_question
        st.session_state.personal_answers[subtopic_name][question_type][index] = new_answer
        return True
    return False

def grade_personal_questions(user_id, user_answers):
    
    correct_count = 0
    total_questions = 0
    results = []

    for subtopic_name, question_types in st.session_state.personal_questions.items():
        for qt, questions in question_types.items():
            for i, question in enumerate(questions):
                total_questions += 1
                correct_answer = st.session_state.personal_answers[subtopic_name][qt][i].split('\n')[0].split(':')[1].strip()
                user_answer = user_answers.get(total_questions)

                is_correct = check_answer(user_answer, correct_answer, qt)
                if is_correct:
                    correct_count += 1

                question_id = question['id'] if isinstance(question, dict) else question[2] if isinstance(question, tuple) and len(question) > 2 else None
                
                # question_id 추출 로직 수정
                if isinstance(question, dict):
                    question_id = question.get('id')
                elif isinstance(question, tuple) and len(question) > 2:
                    question_id = question[2]
                else:
                    question_id = None
                
                if question_id:
                    try:
                        result = update_personal_study_answer(question_id, user_answer, is_correct)
                    except Exception as e:
                        st.warning(f"디버그: DB update error: {str(e)}")
                else:
                    st.warning(f"디버그: question_id가 None입니다. DB 업데이트를 건너뜁니다.")

                results.append({
                    'question_number': total_questions,
                    'question': question[0] if isinstance(question, tuple) else question,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct,
                    'explanation': st.session_state.personal_answers[subtopic_name][qt][i].split('\n', 1)[1] if '\n' in st.session_state.personal_answers[subtopic_name][qt][i] else ''
                })
    return correct_count, total_questions, results

def save_uploadedfile(uploadedfile):
    # 'tmp' 디렉토리가 없으면 생성
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    
    # 파일 이름에서 공백과 특수 문자 제거
    safe_filename = "".join([c for c in uploadedfile.name if c.isalnum() or c in ['_', '-', '.']]).rstrip()
    
    file_path = os.path.join("tmp", safe_filename)
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
    
    return file_path  # 저장된 파일의 경로를 반환

def get_general_subjects_and_subtopics():
    subjects = database.get_general_subjects()
    subtopics = {subject: database.get_general_subtopics(subject) for subject in subjects}
    return subjects, subtopics

def get_subjects_and_subtopics():
    subjects = get_subjects()
    subtopics = {subject: get_subtopics(subject) for subject in subjects}
    return subjects, subtopics

def get_categorized_questions(user_id):
    return get_questions_by_subject_and_subtopic(user_id)

def update_question(question_id, question_data):
    # 'choices' 키가 없는 경우 빈 리스트를 기본값으로 설정
    if 'choices' not in question_data:
        question_data['choices'] = []
    return edit_question_answer_to_db(question_id, question_data)

def close_open_room(room_id, action):
    if action == 'close':
        return close_room(room_id)
    elif action == 'open':
        return reopen_room(room_id)
    return False

def delete_room_by_id(room_id):
    return delete_room(room_id)

def get_room_questions_and_answers(room_id):
    room_info = get_room_info(room_id)
    if room_info:
        return room_info['questions']
    return None

def check_submission_status(user_id, room_id):
    return has_submitted(user_id, room_id)

def get_room_time_info(room_id):
    room_info = get_room_info(room_id, include_questions=False)
    if room_info:
        return room_info['start_time'], room_info['end_time'], room_info['status']
    return None, None, None

def run_timer(seconds, callback):
    start_time = time.time()
    while time.time() - start_time < seconds:
        remaining = int(seconds - (time.time() - start_time))
        callback(remaining)
        time.sleep(1)

def auto_submit_answers(user_id, room_id, user_answers):
    if save_user_room_answers(user_id, room_id, user_answers):
        result = calculate_user_score(user_id, room_id)
        if result:
            set_session_state('result', result)
            set_session_state('submitted', True)
            return result
    return None

def generate_csv_for_questions(questions, answers, user_answers):
    return create_csv(questions, answers, user_answers)

def delete_personal_study_question(question_id):
    return delete_user_questions(question_id)

def delete_personal_question(subtopic_name, question_type, index):
    if subtopic_name in st.session_state.personal_questions and question_type in st.session_state.personal_questions[subtopic_name]:
        if 0 <= index < len(st.session_state.personal_questions[subtopic_name][question_type]):
            # 세션 상태에서 문제 제거
            deleted_question = st.session_state.personal_questions[subtopic_name][question_type].pop(index)
            st.session_state.personal_answers[subtopic_name][question_type].pop(index)
            
            # 데이터베이스에서 문제 삭제
            if 'id' in deleted_question:
                delete_personal_study_question(deleted_question['id'])
            
            return True
    return False

def get_user_rooms_info(user_id):
    return get_user_rooms(user_id)

def get_all_available_rooms():
    return get_all_rooms()

# 추가적인 유틸리티 함수들
def format_time_range(start_time, end_time):
    if start_time and end_time:
        return f"{start_time.strftime('%m/%d %H:%M')} ~ {end_time.strftime('%H:%M')}"
    elif start_time:
        return f"{start_time.strftime('%m/%d %H:%M')} ~"
    return "시간 미정"

def calculate_time_remaining(end_time):
    if end_time:
        return max((end_time - datetime.now()).total_seconds(), 0)
    return 0

def format_question_for_display(question, question_type):
    if isinstance(question, tuple):
        question_text, choices = question
    elif isinstance(question, dict):
        question_text = question['question_text']
        choices = question.get('choices')
    else:
        question_text = question
        choices = None

    if choices and question_type == "multiple-choice":
        question_text = question_text.split('a)')[0].strip()
        formatted_choices = [f"- {choice}" for choice in choices]
        return question_text, formatted_choices
    return question_text, None

def parse_answer(answer):
    answer_parts = answer.split('\n')
    correct_answer = answer_parts[0].split(':')[1].strip() if ':' in answer_parts[0] else answer_parts[0].strip()
    explanation = ' '.join(answer_parts[1:]) if len(answer_parts) > 1 else "해설 없음"
    return correct_answer, explanation

def is_valid_email(email):
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_student_id():
    return ''.join([str(random.randint(0, 9)) for _ in range(8)])

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    # 최소 8자, 최대 20자, 최소 하나의 대문자, 소문자, 숫자, 특수문자 포함
    import re
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$'
    return re.match(pattern, password) is not None

# 세션 관리 함수
def set_session_state(key, value):
    st.session_state[key] = value

def get_session_state(key, default=None):
    return st.session_state.get(key, default)

def clear_session_state(key):
    if key in st.session_state:
        del st.session_state[key]

# 에러 처리 함수
def handle_error(error_message):
    st.error(error_message)
    # 여기에 로깅 로직을 추가할 수 있습니다.

# 데이터 변환 함수
def questions_to_dataframe(questions):
    data = []
    for q in questions:
        data.append({
            'id': q['id'],
            'question_text': q['question_text'],
            'question_type': q['question_type'],
            'subject': q['subject'],
            'subtopic': q['subtopic']
        })
    return pd.DataFrame(data)

# 차트 생성 함수
def create_score_distribution_chart(scores):
    hist_values, bin_edges = np.histogram(scores, bins=10)
    bin_labels = [f'{int(bin_edges[i])}~{int(bin_edges[i+1])}' for i in range(len(bin_edges) - 1)]
    hist_df = pd.DataFrame({
        '점수 구간': bin_labels,
        '참가자 수': hist_values
    })
    return hist_df

# 기타 유틸리티 함수들
def get_question_type_kr(question_type):
    question_type_kr = {
        'multiple-choice': '객관식',
        'short answer': '단답형',
        'true/false': '참/거짓',
        'fill-in-the-blank': '빈칸 채우기'
    }
    return question_type_kr.get(question_type, question_type)

def truncate_text(text, max_length=50):
    return text[:max_length] + '...' if len(text) > max_length else text

def display_question(question, question_type):
    if isinstance(question, tuple):
        question_text, choices = question
    elif isinstance(question, dict):
        question_text = question['question_text']
        choices = question.get('choices')
    else:
        question_text = question
        choices = None

    # 선택지를 제외한 질문 텍스트만 표시
    if choices:
        question_text = question_text.split('a)')[0].strip()
    
    st.markdown(question_text)
    
    if question_type == "multiple-choice" and choices:
        st.markdown("**선택지:**")
        for choice in choices:
            st.markdown(f"- {choice}")

def display_personal_question(question, question_type):
    if isinstance(question, tuple):
        question_text, choices = question
    elif isinstance(question, dict):
        question_text = question['question_text']
        choices = question.get('choices')
    else:
        question_text = question
        choices = None

    # 선택지를 제외한 질문 텍스트만 표시
    if choices:
        question_text = question_text.split('a)')[0].strip()
    
    st.markdown(question_text)

def display_answer(answer):
    answer_parts = answer.split('\n')
    correct_answer = answer_parts[0].split(':')[1].strip() if ':' in answer_parts[0] else answer_parts[0].strip()
    explanation = ' '.join(answer_parts[1:]) if len(answer_parts) > 1 else "해설 없음"
    
    st.markdown(f"**정답:** {correct_answer}")
    st.markdown(f"**해설:** {explanation}")

def show_personal_grading_results():
    st.subheader("채점 결과")
    results = get_session_state('personal_grading_results', [])
    if not results:
        st.warning("채점 결과가 없습니다.")
        return

    for subtopic_name, question_types in st.session_state.personal_questions.items():
        with st.expander(f"{subtopic_name}", expanded=True):
            for result in results:
                explanation = result.get('explanation', '').strip()

                # "해설: "이 포함되어 있는지 확인하고 제거
                if explanation.startswith("해설: "):
                    explanation = explanation[len("해설: "):]  # "해설: " 이후의 문자열만 추출
                with st.container(border=True):
                    st.markdown(f"**문제 {result.get('question_number')}:** {result.get('question').get('question_text')}")
                    st.markdown(f"**제출한 답변:** {result.get('user_answer') if result.get('user_answer') is not None else '답변 없음'}")
                    st.markdown(f"**정답:** {result.get('correct_answer')}")
                    st.markdown(f"**결과:** {'정답 ✅' if result.get('is_correct') else '오답 ❌'}")
                    st.markdown(f"**해설:** {explanation}")

    correct_count = sum(1 for result in results if result.get('is_correct'))
    total_questions = len(results)
    if total_questions > 0:
        st.success(f"최종 점수: {correct_count}/{total_questions} ({correct_count/total_questions*100:.2f}%)")
    else:
        st.warning("채점할 문제가 없습니다.")

def stop_generate():
    print(emergency_stop())