# database.py
import pymysql
import json
from datetime import datetime
import uuid
from collections import Counter
from utils import check_answer
import streamlit as st

# 데이터베이스 연결 설정
DB_CONFIG = {
    'host': 'localhost',
    'user': 'streamlit',
    'password': 'streamlit',
    'database': 'st_quiz',
    'port': 3306
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def create_database_and_tables():
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        port=DB_CONFIG['port']
    )
    cursor = conn.cursor()
    
    try:
        # 데이터베이스 생성
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # users 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                student_id VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # rooms 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                room_name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                start_time DATETIME,
                status ENUM('open', 'closed') DEFAULT 'open',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # questions 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                question_text TEXT NOT NULL,
                choices JSON,
                answer_text TEXT NOT NULL,
                explanation TEXT,
                question_type VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                subject VARCHAR(512),
                subtopic VARCHAR(512),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # room_questions 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_id INT,
                question_id INT,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)

        # participant_answers 테이블 생성 (수정됨)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participant_answers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                room_id INT,
                question_id INT,
                answer TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)

        # participant_scores 테이블 생성 (수정됨)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participant_scores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                room_id INT,
                score FLOAT,
                total_questions INT NOT NULL DEFAULT 0,
                correct_answers INT NOT NULL DEFAULT 0,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (room_id) REFERENCES rooms(id)
            )
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_study_questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                question_text TEXT NOT NULL,
                choices JSON,
                answer_text TEXT NOT NULL,
                explanation TEXT,
                question_type VARCHAR(50),
                subject VARCHAR(255),
                subtopic VARCHAR(255),
                user_answer TEXT,
                is_correct BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        print("Database and tables created successfully.")
    
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    except pymysql.MySQLError as e:
        print(f"Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def authenticate_user(name, password):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE name = %s AND password = %s",
            (name, password)
        )
        user = cursor.fetchone()
        return user
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def register_user(name, password, email, student_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if not student_id:
            student_id = str(uuid.uuid4())[:8]  # 8자리 고유 ID 생성
        cursor.execute(
            "INSERT INTO users (name, password, email, student_id) VALUES (%s, %s, %s, %s)",
            (name, password, email, student_id)
        )
        conn.commit()
        return cursor.lastrowid  # 생성된 user_id 반환
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def has_submitted(user_id, room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT * FROM participant_scores 
            WHERE user_id = %s AND room_id = %s
        """, (user_id, room_id))
        result = cursor.fetchone()
        return result is not None
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# 유저 평가 업데이트 함수
def update_user_response_in_db(user_id, question_number, user_answer=None, user_rating=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 필요한 필드만 업데이트
        if user_answer is not None:
            cursor.execute('''
            UPDATE question_data 
            SET user_answer = %s, updated_at = %s 
            WHERE user_id = %s AND question_number = %s
            ''', (user_answer, datetime.now(), user_id, question_number))

        if user_rating is not None:
            cursor.execute('''
            UPDATE question_data 
            SET user_rating = %s, updated_at = %s 
            WHERE user_id = %s AND question_number = %s
            ''', (user_rating, datetime.now(), user_id, question_number))

        conn.commit()
    except Exception as e:
        st.error(f"사용자 응답을 업데이트하는 중 오류가 발생했습니다: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def save_questions_to_db(questions, answers, user_id, question_type, subject, subtopic):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for q, a in zip(questions, answers):
            # 문제 텍스트와 보기 분리
            queston_text = ""
            if question_type == 'multiple-choice':
                if isinstance(q, tuple) and len(q) > 1:
                    subtopic, question_content = q
                    if isinstance(question_content, tuple) and len(question_content) > 1:
                        question_text, choices_list = question_content
                        choices = json.dumps(choices_list)
                    else:
                        question_text = question_content
                        choices = None
                else:
                    question_text = str(q)
                    choices = None
            else:
                if isinstance(q, tuple) and len(q) > 1:
                    subtopic, question_content = q
                    if isinstance(question_content, tuple) and len(question_content) > 1:
                        question_text, choices_list = question_content
                        choices = None

            # 답변 처리
            if isinstance(a, str):
                answer_parts = a.split('\n', 1)
                answer_text = answer_parts[0].replace('정답: ', '').strip()
                explanation = answer_parts[1].replace('해설: ', '').strip() if len(answer_parts) > 1 else ''
            elif isinstance(a, tuple) and len(a) > 1:
                answer_text = a[0].replace('정답: ', '').strip()
                explanation = a[1].replace('해설: ', '').strip()
            else:
                answer_text = str(a)
                explanation = None

            # 데이터베이스에 삽입
            cursor.execute(
                """
                INSERT INTO questions 
                (user_id, question_text, choices, answer_text, explanation, question_type, subject, subtopic) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, question_text, choices, answer_text, explanation, question_type, subject, str(subtopic))
            )
            
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"오류 발생: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_all_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT r.id, r.room_name, u.name as creator_name,
                   r.start_time, r.end_time, r.status,
                   (SELECT COUNT(DISTINCT user_id) 
                    FROM participant_answers 
                    WHERE room_id = r.id) as participant_count
            FROM rooms r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
        """)
        rooms = cursor.fetchall()
        return rooms
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_room_info(room_id, include_questions=True):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # 시험 정보 가져오기 (start_time 추가)
        cursor.execute("""
            SELECT r.id, r.room_name, r.created_at, r.start_time, r.end_time, r.status
            FROM rooms r
            WHERE r.id = %s
        """, (room_id,))
        room = cursor.fetchone()

        if not room:
            return None

        if include_questions:
            # 시험에 연결된 질문들 가져오기
            cursor.execute("""
                SELECT q.id, q.question_text, q.choices, q.answer_text, q.explanation, q.question_type
                FROM questions q
                JOIN room_questions rq ON q.id = rq.question_id
                WHERE rq.room_id = %s
            """, (room_id,))
            questions = cursor.fetchall()
            room['questions'] = questions

        return room
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_room_questions(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT q.id, q.question_text, q.choices, q.answer_text, q.explanation, q.question_type
            FROM questions q
            JOIN room_questions rq ON q.id = rq.question_id
            WHERE rq.room_id = %s
        """, (room_id,))
        questions = cursor.fetchall()
        
        # choices가 JSON 문자열로 저장되어 있다면 Python 객체로 변환
        for q in questions:
            if q['choices'] and isinstance(q['choices'], str):
                q['choices'] = json.loads(q['choices'])
        
        return questions
    except pymysql.MySQLError as e:
        print(f"An error occurred while fetching room questions: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def update_question(question_id, question_text, answer_text, choices=None, explanation=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    print(question_id, question_text, answer_text, choices, explanation)
    try:
        if choices is not None:
            choices_json = json.dumps(choices)
        else:
            choices_json = None

        cursor.execute("""
            UPDATE questions
            SET question_text = %s, answer_text = %s, choices = %s, explanation = %s
            WHERE id = %s
        """, (question_text, answer_text, choices_json, explanation, question_id))
        
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred while updating the question: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def check_room_edit_permission(user_id, room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT user_id FROM rooms
            WHERE id = %s
        """, (room_id,))
        room = cursor.fetchone()
        return room and room['user_id'] == user_id
    except pymysql.MySQLError as e:
        print(f"An error occurred while checking room edit permission: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def save_participant_answers(user_id, room_id, answers):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for question_id, answer in answers.items():
            cursor.execute("""
                INSERT INTO participant_answers (user_id, room_id, question_id, answer)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE answer = VALUES(answer)
            """, (user_id, room_id, question_id, answer))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        print(f"An error occurred while saving answers: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_rooms(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT 
                r.id, 
                r.room_name, 
                r.start_time, 
                r.end_time, 
                r.status, 
                COUNT(DISTINCT pa.user_id) as Participants
            FROM 
                rooms r
            LEFT JOIN 
                participant_answers pa ON r.id = pa.room_id
            WHERE 
                r.user_id = %s 
            GROUP BY 
                r.id
            ORDER BY 
                r.created_at DESC
        """, (user_id,))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_question_by_id(question_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT * FROM personal_study_questions
            WHERE id = %s
        """, (question_id,))
        return cursor.fetchone()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_questions_by_subject_and_subtopic(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)


    try:
        cursor.execute("""
            SELECT id, question_text, choices, answer_text, explanation, question_type, subject, subtopic
            FROM questions
            ORDER BY subject, subtopic
        """)
        questions = cursor.fetchall()
        
        # 과목과 소주제별로 문제 분류
        categorized_questions = {}
        for q in questions:
            subject = q['subject'] or '미분류'  # 과목이 없는 경우 '미분류'로 처리
            subtopic = q['subtopic'] or '미분류'  # 소주제가 없는 경우 '미분류'로 처리
            
            if subject not in categorized_questions:
                categorized_questions[subject] = {}
            if subtopic not in categorized_questions[subject]:
                categorized_questions[subject][subtopic] = []
            
            categorized_questions[subject][subtopic].append(q)
        
        return categorized_questions
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

def db_create_room(room_name, user_id, question_ids, password, start_time=None, end_time=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO rooms (user_id, room_name, password, start_time, end_time) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, room_name, password, start_time, end_time)
        )
        room_id = cursor.lastrowid

        for question_id in question_ids:
            cursor.execute(
                "INSERT INTO room_questions (room_id, question_id) VALUES (%s, %s)",
                (room_id, question_id)
            )

        conn.commit()
        return room_id
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def authenticate_room(room_id, password):
    """
    주어진 room_id와 password를 사용하여 시험실 인증을 수행합니다.
    
    :param room_id: 인증할 시험실의 ID
    :param password: 시험실 비밀번호
    :return: 인증 성공 시 True, 실패 시 False
    """
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            "SELECT * FROM rooms WHERE id = %s AND password = %s",
            (room_id, password)
        )
        room = cursor.fetchone()
        if room:
            print(f"Room {room_id} authenticated successfully.")
            return True
        else:
            print(f"Authentication failed for room {room_id}.")
            return False
    except pymysql.MySQLError as e:
        print(f"An error occurred during room authentication: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def close_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 현재 시간을 종료 시간으로 설정
        end_time = datetime.now()
        
        # 시험의 상태를 'closed'로 업데이트하고, 종료 시간을 설정
        cursor.execute(
            "UPDATE rooms SET status = 'closed', end_time = %s WHERE id = %s",
            (end_time, room_id)
        )
        
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_answers(user_id, room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT pa.*, q.*
            FROM participant_answers pa
            join questions q 
            WHERE pa.room_id = %s
            AND pa.user_id = %s
            AND pa.question_id = q.id;
        """, (room_id, user_id))
        answers = cursor.fetchall()
        
        total_questions = len(answers)
        correct_answers = sum(1 for answer in answers if check_answer(answer['answer'], answer['answer_text'], answer['question_type']))
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        return {
            'answers': {str(answer['question_id']): answer['answer'] for answer in answers},
            'score': correct_answers,
            'total_questions': total_questions,
            'percentage_score': score
        }
    except pymysql.MySQLError as e:
        print(f"An error occurred while fetching user answers: {e}")
        return {'answers': {}, 'score': 0, 'total_questions': 0, 'percentage_score': 0}
    finally:
        cursor.close()
        conn.close()

def reopen_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 시험의 상태를 'open'으로 업데이트하고, 종료 시간을 NULL로 설정
        cursor.execute(
            "UPDATE rooms SET status = 'open', end_time = NULL WHERE id = %s",
            (room_id,)
        )
        
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def delete_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 트랜잭션 시작
        cursor.execute("START TRANSACTION")

        # participant_answers 테이블에서 관련 레코드 삭제
        cursor.execute("DELETE FROM participant_answers WHERE room_id = %s", (room_id,))

        # participant_scores 테이블에서 관련 레코드 삭제
        cursor.execute("DELETE FROM participant_scores WHERE room_id = %s", (room_id,))

        # room_questions 테이블에서 관련 레코드 삭제
        cursor.execute("DELETE FROM room_questions WHERE room_id = %s", (room_id,))

        # rooms 테이블에서 시험 삭제
        cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))

        # 트랜잭션 커밋
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        # 오류 발생 시 롤백
        conn.rollback()
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_all_questions(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT id, question_text, choices, answer_text, explanation, question_type
            FROM questions
        """)
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_correct_answers(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT q.id, q.answer_text
            FROM questions q
            JOIN room_questions rq ON q.id = rq.question_id
            WHERE rq.room_id = %s
        """, (room_id,))
        return {row['id']: row['answer_text'] for row in cursor.fetchall()}
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

def get_participant(room_id, name, email, student_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            "SELECT * FROM participants WHERE room_id = %s AND name = %s AND email = %s AND student_id = %s",
            (room_id, name, email, student_id)
        )
        return cursor.fetchone()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_participant_answers(user_id, room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT pa.question_id, pa.answer, q.question_text, q.answer_text, q.explanation, q.question_type
            FROM participant_answers pa
            JOIN room_questions rq ON pa.question_id = rq.question_id
            JOIN questions q ON rq.question_id = q.id
            WHERE pa.user_id = %s AND rq.room_id = %s
        """, (user_id, room_id))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def save_score(user_id, room_id, score, total_questions, correct_answers):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO participant_scores 
            (user_id, room_id, score, total_questions, correct_answers) 
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            score = VALUES(score), 
            total_questions = VALUES(total_questions), 
            correct_answers = VALUES(correct_answers)""",
            (user_id, room_id, score, total_questions, correct_answers)
        )
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_room_participants(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.student_id, ps.score, ps.correct_answers, ps.total_questions
            FROM participant_scores ps
            JOIN users u ON ps.user_id = u.id
            WHERE ps.room_id = %s
            ORDER BY ps.score DESC
        """, (room_id,))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_question_stats(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT 
                q.id, 
                q.question_text,
                q.answer_text,
                COUNT(pa.id) as total_answers,
                SUM(CASE WHEN pa.answer = q.answer_text THEN 1 ELSE 0 END) as correct_answers
            FROM questions q
            JOIN room_questions rq ON q.id = rq.question_id
            LEFT JOIN participant_answers pa ON q.id = pa.question_id
            WHERE rq.room_id = %s
            GROUP BY q.id
        """, (room_id,))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_general_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT subject
            FROM questions
            WHERE subject IS NOT NULL AND subject != ''
            ORDER BY subject
        """)
        subjects = [row[0] for row in cursor.fetchall()]
        return subjects
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_general_subtopics(subject):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT subtopic
            FROM questions
            WHERE subject = %s AND subtopic IS NOT NULL AND subtopic != ''
            ORDER BY subtopic
        """, (subject,))
        subtopics = [row[0] for row in cursor.fetchall()]
        return subtopics
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT subject
            FROM personal_study_questions
            WHERE subject IS NOT NULL AND subject != ''
            ORDER BY subject
        """)
        subjects = [row[0] for row in cursor.fetchall()]
        return subjects
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_subtopics(subject):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT subtopic
            FROM personal_study_questions
            WHERE subject = %s AND subtopic IS NOT NULL AND subtopic != ''
            ORDER BY subtopic
        """, (subject,))
        subtopics = [row[0] for row in cursor.fetchall()]
        return subtopics
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def save_personal_study_question(question_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # choices를 JSON 문자열로 변환
        choices = json.dumps(question_data['choices']) if question_data['choices'] is not None else None
        
        # is_correct가 None이면 NULL로 설정 (BOOLEAN 타입은 NULL을 허용함)
        is_correct = question_data['is_correct']
        
        cursor.execute("""
            INSERT INTO personal_study_questions 
            (user_id, question_text, choices, answer_text, explanation, question_type, subject, subtopic, user_answer, is_correct)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            question_data['user_id'],
            question_data['question_text'],
            choices,
            question_data['answer_text'],
            question_data['explanation'],
            question_data['question_type'],
            question_data['subject'],
            question_data['subtopic'],
            question_data['user_answer'],
            is_correct
        ))
        conn.commit()
        return cursor.lastrowid
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def update_personal_study_answer(question_id, user_answer, is_correct):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE personal_study_questions
            SET user_answer = %s, is_correct = %s
            WHERE id = %s
        """, (user_answer, is_correct, question_id))
        affected_rows = cursor.rowcount
        conn.commit()
        return affected_rows > 0
    except pymysql.MySQLError as e:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_personal_study_questions(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT id, question_text, answer_text, explanation, user_answer, is_correct, question_type
            FROM personal_study_questions
            WHERE user_id = %s
        """, (user_id,))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def delete_user_questions(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM personal_study_questions WHERE id = %s", (id,))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        print(f"An error occurred while deleting question: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_questions(user_id, start_date=None, end_date=None, subject=None, subtopic=None):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        query = """
            SELECT id, question_text, choices, answer_text, explanation, question_type, 
                   subject, subtopic, user_answer, is_correct, created_at
            FROM personal_study_questions
            WHERE user_id = %s
        """
        params = [user_id]

        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)
        if subject:
            query += " AND subject = %s"
            params.append(subject)
        if subtopic:
            query += " AND subtopic = %s"
            params.append(subtopic)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def edit_question_answer_to_db(question_id, question):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        new_question_text = question['question_text']
        new_choices_json = question.get('choices')
        new_answer_text = question['answer_text']
        new_explanation = question['explanation']

        # choice 값이 있는 경우에만 JSON으로 변환
        if new_choices_json is not None:
            new_choices_json = json.dumps(new_choices_json, ensure_ascii=False)
        
        # 기존 question 업데이트
        cursor.execute(
            """
            UPDATE st_quiz.questions 
            SET question_text = %s, choices = %s, answer_text = %s, explanation = %s 
            WHERE id = %s
            """,
            (new_question_text, new_choices_json, new_answer_text, new_explanation, question_id)
        )

        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# 사용자가 가장 많이 입력한 오답 확인
def get_question_ids_by_room(room_id):
    """
    주어진 room_id에 해당하는 모든 question_id를 가져옵니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT question_id
            FROM room_questions
            WHERE room_id = %s
            ORDER BY id ASC
        """, (room_id,))
        question_ids = cursor.fetchall()
        return [q['question_id'] for q in question_ids]

    except pymysql.MySQLError as e:
        print(f"오류 발생: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_question_info_and_stats(room_id, question_id):
    """
    주어진 room_id와 question_id에 대한 문제 정보와 통계 데이터를 가져옵니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT question_text, answer_text, question_type
            FROM questions
            WHERE id = %s
        """, (question_id,))
        question_info = cursor.fetchone()

        cursor.execute("""
            SELECT answer
            FROM participant_answers
            WHERE room_id = %s AND question_id = %s
        """, (room_id, question_id))
        answers = cursor.fetchall()

        total_answers = len(answers)
        correct_answers = sum(1 for answer in answers if check_answer(answer['answer'], question_info['answer_text'], question_info['question_type']))

        return {
            'question_text': question_info['question_text'],
            'answer_text': question_info['answer_text'],
            'question_type': question_info['question_type'],
            'total_answers': total_answers,
            'correct_answers': correct_answers
        }

    except pymysql.MySQLError as e:
        print(f"오류 발생: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_most_frequent_incorrect_answer(room_id, question_id):
    """
    주어진 room_id와 question_id에 대한 가장 많이 입력된 오답을 계산합니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT answer, question_type, answer_text
            FROM participant_answers pa
            JOIN questions q ON pa.question_id = q.id
            WHERE pa.room_id = %s AND pa.question_id = %s
        """, (room_id, question_id))
        answers = cursor.fetchall()

        if not answers:
            return "없다"

        correct_answer = answers[0]['answer_text']
        question_type = answers[0]['question_type']

        # 정답이 아닌 응답 필터링
        incorrect_answers = [a['answer'] for a in answers if not check_answer(a['answer'], correct_answer, question_type)]

        if not incorrect_answers:
            return "없다"  # 모든 답안이 정답인 경우

        # 오답들의 빈도를 계산
        answer_counts = Counter(incorrect_answers)

        # 최대 빈도 계산
        max_count = max(answer_counts.values())

        # 최대 빈도의 오답들을 모두 추출
        most_frequent_incorrect = [answer for answer, count in answer_counts.items() if count == max_count]

        # a, b, c, d 순서로 정렬
        def sort_key(answer):
            stripped_answer = answer.strip()
            if stripped_answer:
                first_char = stripped_answer[0].lower()
            else:
                return 4
            predefined_order = {'a': 0, 'b': 1, 'c': 2, 'd': 3}
            return predefined_order.get(first_char, 4)

        most_frequent_incorrect.sort(key=sort_key)

        return ', '.join(most_frequent_incorrect)

    except pymysql.MySQLError as e:
        print(f"오류 발생: {e}")
        return "없다"
    finally:
        cursor.close()
        conn.close()

def get_all_question_data(room_id):
    """
    주어진 room_id에 대한 모든 문제의 정보와 통계, 가장 많이 입력된 오답을 가져옵니다.
    """
    question_ids = get_question_ids_by_room(room_id)
    all_question_data = []

    for question_id in question_ids:
        question_info_and_stats = get_question_info_and_stats(room_id, question_id)
        if question_info_and_stats:
            most_frequent_incorrect_answer = get_most_frequent_incorrect_answer(room_id, question_id)
            question_info_and_stats['most_frequent_incorrect_answer'] = most_frequent_incorrect_answer
            all_question_data.append(question_info_and_stats)

    return all_question_data

def get_user_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT id, name, email, student_id, created_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return user
    except pymysql.MySQLError as e:
        print(f"An error occurred while fetching user information: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# 데이터베이스 초기화 함수
def initialize_database():
    create_database_and_tables()

# 이 파일이 직접 실행될 때만 데이터베이스 초기화를 수행
if __name__ == "__main__":
    initialize_database()