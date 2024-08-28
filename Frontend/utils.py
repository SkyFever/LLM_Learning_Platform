# utils.py
import io
import csv
import requests
from difflib import SequenceMatcher

BASE_URL = "localhost:8000"
SMT_URL = f"http://{BASE_URL}/similarity"

def check_answer(user_answer, correct_answer, question_type):
    try:
        prompt = (
            f"You are an intelligent assistant that evaluates the similarity between two answers based on their meaning. "
            f"Given a user's answer and the correct answer for a {question_type} question, determine if the user's answer is correct. "
            f"If the user's answer is not exist, None or blank, please reply with 'False'.\n\n"
            f"Please reply with 'True' if the user's answer is correct or really simillar to correct answer, otherwise reply with 'False'."
        )
        context = (
            f"Correct answer: {correct_answer}\n"
            f"User's answer: {user_answer}\n"
        )
        response = requests.post(SMT_URL, json={'prompt': prompt, 'context': context})
        response_data = response.json()
        
        if "response" not in response_data:
            raise ValueError("Expected 'response' key in the API response.")

        result = response_data["response"].strip().lower()
        if result in ["true", "참", "정답"]:
            return True
        else:
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while requesting model: {e}")
        return None
    except ValueError as ve:
        print(f"Error in response structure: {ve}")
        return None

def create_csv(questions, answers, user_ratings):
    """
    문제, 답변, 사용자 평가를 CSV 파일로 만드는 함수
    :param questions: 문제 리스트
    :param answers: 답변 리스트
    :param user_ratings: 사용자 평가 딕셔너리
    :return: CSV 형식의 바이트 문자열
    """
    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel
    writer = csv.writer(output, dialect='excel')
    writer.writerow(['문제 번호', '문제', '정답', '해설', '사용자 평가'])

    for i, (question, answer) in enumerate(zip(questions, answers), 1):
        question_text = question[0] if isinstance(question, tuple) else question
        question_text = question_text.split('\n')[0].replace(f"문제 {i}. ", "")
        
        answer_parts = answer.split('\n')
        answer_text = answer_parts[0].replace("정답: ", "") if answer_parts else ""
        explanation = ' '.join(answer_parts[1:]).replace("해설: ", "") if len(answer_parts) > 1 else ""
        
        user_rating = user_ratings.get(i, "평가 없음")
        
        writer.writerow([i, question_text, answer_text, explanation, user_rating])

    return output.getvalue().encode('utf-8-sig')
