import io
import csv
import math
import re
import requests
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from text_processing import separate_questions_and_answers  # 이 부분은 필요에 따라 경로 조정
from database import save_questions_to_db  # 필요에 따라 경로 조정
from langchain.schema import Document
import random
from typing import List, Dict

BASE_URL = "localhost:8000"
API_URL = f"http://{BASE_URL}/generate"
CVF_URL = f"http://{BASE_URL}/transcribe_video"
CAF_URL = f"http://{BASE_URL}/transcribe_audio"
EST_URL = f"http://{BASE_URL}/emergency_stop"

# FastAPI 클라이언트 요청 함수 추가

def emergency_stop():
    try:
        response = requests.post(EST_URL)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while requesting model: {e}")
        return None

def transcribe_video_file(video_file_path):
    """비디오 파일을 서버에 업로드하여 텍스트를 추출하는 함수"""
    with open(video_file_path, "rb") as video_file:
        response = requests.post(CVF_URL, files={"file": video_file})
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Error during transcription: {response.status_code} - {response.text}")

def transcribe_audio_file(audio_file_path):
    """오디오 파일을 서버에 업로드하여 텍스트를 추출하는 함수"""
    with open(audio_file_path, "rb") as audio_file:
        response = requests.post(CAF_URL, files={"file": audio_file})
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Error during transcription: {response.status_code} - {response.text}")

def generate_questions_batch(docs, subtopic_question_types, batch_size=8, max_retries=6):
    try:
        if isinstance(docs, str):
            docs = [Document(page_content=docs)]
        elif isinstance(docs, list) and all(isinstance(doc, str) for doc in docs):
            docs = [Document(page_content=doc) for doc in docs]

        EMBEDDING_MODEL = 'text2vec'
        EMBEDDING_DEVICE = "cuda"
        VECTOR_SEARCH_TOP_K = 8
        embedding_model_dict = {
            "text2vec": "Alibaba-NLP/gte-multilingual-base"
        }
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[EMBEDDING_MODEL], model_kwargs={'device': EMBEDDING_DEVICE, "trust_remote_code": True})

        all_questions = {subtopic: {qt: [] for qt in subtopic_question_types[subtopic]} for subtopic in subtopic_question_types}
        all_answers = {subtopic: {qt: [] for qt in subtopic_question_types[subtopic]} for subtopic in subtopic_question_types}
        additional_questions = {subtopic: {qt: [] for qt in subtopic_question_types[subtopic]} for subtopic in subtopic_question_types}
        try_count = 0

        # 문서를 그룹으로 나누기
        groups = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]
        random.shuffle(groups)  # 그룹의 순서만 섞기

        while try_count < max_retries:
            print(f"{try_count+1}/{max_retries}번째 시도")

            for group in groups:
                # 각 그룹에 대해 FAISS 인덱스 생성
                docsearch = FAISS.from_documents(group, embeddings)

                for subtopic, question_types in subtopic_question_types.items():
                    remaining_questions = {}
                    for qt in question_types:
                        current_count = len(all_questions[subtopic][qt])
                        remaining_questions[qt] = max(subtopic_question_types[subtopic][qt] + 5 - current_count, 0)  # 요청 수 + 5

                    # 모든 유형의 질문이 충분히 생성되었는지 확인
                    if all(remaining == 0 for remaining in remaining_questions.values()):
                        print(f"{subtopic} 모든 질문 유형에 대한 생성이 완료되었습니다.")
                        continue

                    # 현재 코드에서 사용되는 외부 함수 호출
                    query = create_enhanced_question_prompt(question_types, remaining_questions)
                    retriever = docsearch.as_retriever(search_kwargs={"k": min(VECTOR_SEARCH_TOP_K, len(group))})
                    relevant_docs = retriever.get_relevant_documents(query)
                    context = "\n".join([doc.page_content for doc in relevant_docs])

                    response = send_request_to_model_server(context, query)
                    print(f"API Response: {response}")

                    if response:
                        questions, answers = separate_questions_and_answers(response, question_types)
                        processed_questions, processed_answers = post_process_questions(questions, answers, question_types)

                        for qt in question_types:
                            if remaining_questions[qt] > 0:
                                new_questions = processed_questions[qt][:remaining_questions[qt]]
                                new_answers = processed_answers[qt][:remaining_questions[qt]]
                                all_questions[subtopic][qt].extend(new_questions)
                                all_answers[subtopic][qt].extend(new_answers)

                                # 남은 질문들을 additional_questions에 추가
                                extra_questions = processed_questions[qt][remaining_questions[qt]:]
                                extra_answers = processed_answers[qt][remaining_questions[qt]:]
                                additional_questions[subtopic][qt].extend(list(zip(extra_questions, extra_answers)))

            try_count += 1

        # 최종 결과 로깅
        for subtopic, question_types in subtopic_question_types.items():
            for qt in question_types:
                print(f"Final number of {qt} questions for {subtopic}: {len(all_questions[subtopic][qt])}")
                print(f"Number of additional {qt} questions for {subtopic} for regeneration: {len(additional_questions[subtopic][qt])}")

        return all_questions, all_answers, additional_questions

    except Exception as e:
        print(f"Error in generate_questions_batch: {str(e)}")
        raise

def create_enhanced_question_prompt(question_types, num_questions):
    prompt = f"""
Generate questions and answers in Korean based on the given text for multiple question types.
Adhere strictly to the following guidelines:

1. Create EXACTLY the following number of questions for each type:
{' '.join([f'- {qt}: {num_questions[qt]}' for qt in question_types])}

2. Each question must be directly and solely based on the provided text content.
3. Do not invent, assume, or infer any additional information or context that is not explicitly present in the provided text.
4. Ensure that all questions are unique and non-repetitive across all types.
5. Do not include any question numbering or 'Question:', '[Question]' prefix.
6. If the given text contains content related to programming languages, include coding-related questions where appropriate.
7. Use clear and concise language.
8. Ensure all text is in Korean, including code comments.
9. Every questions and answers should separated never combine questions or answers.

10. **STRICTLY** use the following format for each question type:

{''.join([f'''
[{qt.upper()}]
{get_question_format(qt)}
''' for qt in question_types])}

11. Label each question clearly with its type (e.g., [MULTIPLE-CHOICE], [SHORT ANSWER], [TRUE/FALSE], [FILL-IN-THE-BLANK]).

**IMPORTANT:** It is **CRUCIAL** to generate **EXACTLY** the specified number of questions for **EACH** type. Double-check your output before returning it.
"""

    f = "prompt_log"
    with open(f, "w", encoding="utf-8") as file:
        file.write(prompt)
        file.write("\n")
        file.write("\n")
    return prompt

def send_request_to_model_server(context, query):
    try:
        response = requests.post(API_URL, json={"prompt": query, "context": context})
        response.raise_for_status()
        return response.json().get("response")
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while requesting model: {e}")
        return None


def get_question_format(question_type):
    formats = {
"multiple-choice": """
For multiple-choice questions:
    - Provide exactly 4 options (a, b, c, d).
    - Place each option on a new line.
    - Do not repeat the options in the question text.
    - Use the following format:

문제 {0}. [Question]
a) [Option 1]
b) [Option 2]
c) [Option 3]
d) [Option 4]

정답: [Correct option]
해설: [Simple commentary]
""",
"short answer": """
For short answer questions:
    - Ensure that the answers length should be 1-5 words long.
    - Use the following format:

문제 {0}. [Question]

정답: [Correct answer]
해설: [Simple commentary]
""",
"true/false": """
For true/false questions:
    - The answer should be either '참' or '거짓'.
    - Use the following format:

문제 {0}. [Question]

정답: [Correct answer]
해설: [Simple commentary]
""",
"fill-in-the-blank": """
For fill-in-the-blank questions:
    - **Do not include the answer within the brackets in the question text.**
    - **Replace a key term or concept with '[     ]' or '_____' in each question.**
    - **Ensure that the blank is for a single word or short phrase.**
    - Generate questions that have exactly one blank to be filled in.
    - Do not use any other symbols such as '()', '{}', '<>', or '[]' to represent blanks.
    - Do not generate short answer questions in this format.
    - Use the following format:

문제 {0}. [Question]

정답: [Correct answer]
해설: [Simple commentary]
"""
    }
    return formats.get(question_type, "")

def normalize_question_format(question):
    return re.sub(r'(\s*)(?=[a-d]\))', r'\n', question)

def post_process_questions(questions, answers, question_types):
    processed_questions = {qt: [] for qt in question_types}
    processed_answers = {qt: [] for qt in question_types}

    for qt in question_types:
        for question, answer in zip(questions.get(qt, []), answers.get(qt, [])):
            try:
                if qt == 'multiple-choice':
                    options = re.findall(r'[a-d]\).*', question)
                    if len(options) == 4:
                        question_without_options = re.sub(r'[a-d]\).*', '', question).strip()
                        processed_questions[qt].append((question_without_options, options))
                        processed_answers[qt].append(answer)
                    else:
                        print(f"Warning: Multiple choice question does not have exactly 4 options: {question}")
                elif qt == 'fill-in-the-blank':
                    if question.count('_') >= 2:
                        processed_questions[qt].append(question)
                        processed_answers[qt].append(answer)
                    else:
                        print(f"Warning: Fill-in-the-blank question does not contain blank: {question}")
                elif qt in ['short answer', 'true/false']:
                    processed_questions[qt].append(question)
                    processed_answers[qt].append(answer)
                else:
                    print(f"Warning: Unknown question type '{qt}': {question}")
            except Exception as e:
                print(f"Error processing {qt} question: {str(e)}")

    return processed_questions, processed_answers

# 비동기 처리를 위한 함수
async def generate_questions_async(docs, question_types, num_questions):
    import asyncio
    tasks = []
    for qt, num in question_types.items():
        task = asyncio.create_task(generate_questions_batch(docs, qt, num))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return results

def extract_code_example(question):
    code_example = ""
    if "[예시 코드]" in question:
        code_parts = question.split("[예시 코드]")
        if len(code_parts) > 1:
            code_end_parts = code_parts[1].split("[^예시 코드]")
            code_example = code_end_parts[0].strip() if len(code_end_parts) > 1 else code_parts[1].strip()
    return re.sub(r'^\^\^\^|^\s*\^\^\^\s*|\^\^\^$|\s*\^\^\^\s*$', '', code_example).strip()

def clean_question_text(question, question_type):
    question_text = question.split("[^예시 코드]")[-1].strip() if "[^예시 코드]" in question else question
    question_text = re.sub(r'^(Question:\s*|\[Question\]\s*|문제\s*\d+\.?\s*)', '', question_text)
    question_text = re.sub(r'\s+', ' ', question_text).strip()
    if question_type == "multiple-choice":
        question_text = normalize_question_format(question_text)
    return question_text

def validate_question_format(question_text, question_type):
    if question_type == "multiple-choice":
        options = re.findall(r'[a-d]\)\s.*?(?=\s*[a-d]\)|$)', question_text)
        return len(options) == 4
    elif question_type == "fill-in-the-blank":
        return '[     ]' in question_text or '[ ]' in question_text or '______' in question_text
    elif question_type == "true/false":
        return question_text.endswith('.')
    elif question_type == "short answer":
        return question_text.endswith('?')
    return True

def format_question(question_text, code_example, question_type):
    if question_type == "multiple-choice":
        options = re.findall(r'[a-d]\)\s.*?(?=\s*[a-d]\)|$)', question_text)
        main_question = re.sub(r'\s*[a-d]\)\s.*?(?=\s*[a-d]\)|$)', '', question_text).strip()
        return (f"{code_example}\n\n{main_question}" if code_example else main_question, options)
    else:
        return f"{code_example}\n\n{question_text}" if code_example else question_text

def process_answer(answer, question_type, processed_question):
    answer_parts = answer.split('해설:', 1)
    answer_text = answer_parts[0].replace('정답:', '').strip()
    commentary = answer_parts[1].strip() if len(answer_parts) > 1 else ""

    if not answer_text:
        print(f"답변이 없는 질문을 건너뛰었습니다.")
        return None

    if question_type == "multiple-choice" and isinstance(processed_question, tuple):
        correct_option = next((option for option in processed_question[1] if answer_text in option), None)
        if correct_option:
            return f"정답: {correct_option}\n해설: {commentary}"
        else:
            print(f"정답을 찾을 수 없습니다: {answer_text}")
            return None
    else:
        return f"정답: {answer_text}\n해설: {commentary}"