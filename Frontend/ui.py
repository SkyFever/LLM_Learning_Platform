import streamlit as st
import core_logic as cl
from datetime import datetime, timedelta
import json
import re
import altair as alt
from st_clickable_images import clickable_images
import pybase64
    
# 기본 페이지 설정
st.set_page_config(
    page_title="AI 학습 플랫폼",  # 기본 제목
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto"  # 기본 사이드바 상태
)

def main():
    cl.init_session_state()
    cl.init_cookies()  # 쿠키 초기화 추가
    
    if cl.get_session_state('user_id') is None or cl.get_session_state('mode') is None:
        cl.set_session_state('mode', None)
        login_signup()
    
    else:
        if st.session_state.user is not None:
            st.sidebar.title(f"환영합니다, {st.session_state.user['name']}님!")
        else:
            st.sidebar.title("환영합니다!")
        
        if st.sidebar.button("로그아웃"):
            cl.logout()
            st.rerun()

        if cl.get_session_state('mode') == "default":
            if st.session_state.is_admin:
                mode_select()
            else:
                cl.set_session_state('mode', "student")

        if cl.get_session_state('mode') == "admin":
            show_admin_menu()
        
        if cl.get_session_state('mode') == "student":
            show_student_menu()

def login_signup():
    if 'show_signup_form' not in st.session_state:
        st.session_state.show_signup_form = False

    if st.session_state.show_signup_form:
        show_signup_form()
    else:
        show_login_form()

def show_login_form():
    st.markdown("<h1 style='text-align: center;'>로그인</h1>", unsafe_allow_html=True)
    with st.columns(3)[1]:
        with st.container(border=True):
            name = st.text_input("이름", key="login_name")
            password = st.text_input("비밀번호", type='password', key="login_password")
            stay_logged_in = st.checkbox("로그인 상태 유지", key="stay_logged_in")
            if st.button("로그인", use_container_width=True):
                user = cl.authenticate_user(name, password)
                if user:
                    st.success(f"{name}님, 환영합니다!")
                    cl.set_session_state('user', user)
                    cl.set_auth_cookie(user["id"], remember_me=stay_logged_in)
                    cl.set_session_state('user_id', user["id"])
                    cl.set_session_state('is_admin', cl.check_if_admin(user["id"]))
                    cl.set_session_state('mode', "default")
                    st.rerun()
                else:
                    st.error("이름 또는 비밀번호가 잘못되었습니다.")

    st.markdown("""
    <style>
    div.stButton {text-align:center}
    </style>""", unsafe_allow_html=True)
    if st.button("회원가입"):
        st.session_state.show_signup_form = True
        st.rerun()

def show_signup_form():
    st.markdown("<h1 style='text-align: center;'>회원가입</h1>", unsafe_allow_html=True)
    with st.columns(3)[1]:
        with st.container(border=True):
            new_name = st.text_input("이름")
            new_password = st.text_input("비밀번호", type='password')
            new_email = st.text_input("이메일")
            new_student_id = st.text_input("학번 (선택사항)")
            
            if st.button("가입하기", use_container_width=True):
                if new_name and new_password and new_email:
                    user_id = cl.register_user(new_name, new_password, new_email, new_student_id)
                    if user_id:
                        st.success(f"계정이 생성되었습니다. User ID: {user_id}")
                        st.info("이제 로그인해주세요.")
                        st.session_state.show_signup_form = False
                        st.rerun()
                    else:
                        st.error("회원가입 중 오류가 발생했습니다. 다시 시도해주세요.")
                else:
                    st.error("이름, 비밀번호, 이메일은 필수 입력 항목입니다.")
    
    st.markdown("""
    <style>
    div.stButton {text-align:center}
    </style>""", unsafe_allow_html=True)
    if st.button("로그인 화면으로 돌아가기"):
        st.session_state.show_signup_form = False
        st.rerun()

# 이미지를 base64로 인코딩하여 변환
def get_image_as_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = pybase64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded_string}"

def mode_select():
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 30px;'>AI 학습 플랫폼</h1>
    """, unsafe_allow_html=True)

    # 적당한 이미지 URL 또는 로컬 이미지 경로
    admin_image_path = r"image/admin_image.png"
    student_image_path = r"image/student_image.png"

    admin_image = get_image_as_base64(admin_image_path)
    student_image = get_image_as_base64(student_image_path)


    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            clicked_stu = clickable_images(
                [student_image],
                img_style={"width": "100%", "height": "auto"}  # 이미지 크기 유동 조절
            )
            stu_btn = st.button("📝 시험 응시 및 개인 학습", help="시험에 참여하거나 개인 학습을 진행합니다", use_container_width=True)
            if clicked_stu != -1 or stu_btn:
                cl.set_session_state('mode', "student")
                st.rerun()

    with col2:
        with st.container(border=True):
            if st.session_state.is_admin:
                clicked_adm = clickable_images(
                    [admin_image],
                    img_style={"width": "100%", "height": "auto"}  # 이미지 크기 유동 조절
                )
                adm_btn = st.button("🎓 시험 출제 및 관리", help="새로운 시험을 출제하고 관리합니다", use_container_width=True)
                if clicked_adm != -1 or adm_btn:
                    cl.get_session_state('mode') == "admin"
                    st.rerun()
            else:
                st.warning("시험 출제 모드는 관리자만 접근 가능합니다.")

def show_admin_menu():
    st.sidebar.header("관리자 메뉴")
    if st.sidebar.button("메인으로"):
        cl.set_session_state('mode', "default")
        st.rerun()
    menu = st.sidebar.radio("선택하세요", ["시험 문제 생성", "시험 출제", "시험 포털"])

    if menu == "시험 문제 생성":
        create_questions()
    elif menu == "시험 출제":
        create_room()
    elif menu == "시험 포털":
        show_user_rooms()

def show_student_menu():
    st.sidebar.header("학생 메뉴")
    if st.session_state.is_admin:
        if st.sidebar.button("메인으로"):
            cl.set_session_state('mode', "default")
            st.rerun()
    menu = st.sidebar.radio("선택하세요", ["시험 포털", "개인 학습", "이전 학습 기록", "이전 문제 풀기"])

    if menu == "시험 포털":
        show_room_list()
    elif menu == "개인 학습":
        create_personal_questions()
    elif menu == "이전 학습 기록":
        show_previous_learning_records()
    elif menu == "이전 문제 풀기":
        solve_previous_questions()

def create_questions():
    st.header("시험 문제 생성")

    question_types_dict = {
        "객관식": "multiple-choice",
        "단답형": "short answer",
        "참/거짓": "true/false",
        "빈칸 채우기": "fill-in-the-blank"
    }

    subjects, subtopics = cl.get_general_subjects_and_subtopics()
    subject = st.selectbox("과목명을 선택하세요", [""] + subjects, format_func=lambda x: '새 과목 추가' if x == "" else x)
    
    if subject == "":
        subject = st.text_input("새 과목명을 입력하세요")
    
    if subject:
        st.subheader("소주제 및 파일 입력")
        num_subtopics = st.number_input("소과목 수를 입력하세요", min_value=1, value=1)

        subtopics_data = {}
        for i in range(num_subtopics):
            subtopic_name_key = f"subtopic_name_{i}"
            if subtopic_name_key not in st.session_state:
                st.session_state[subtopic_name_key] = ""

            expander_title = st.session_state[subtopic_name_key] if st.session_state[subtopic_name_key] else f"소주제 {i+1} 설정"
            with st.expander(expander_title, expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    # 주어진 subtopics 데이터 구조에 맞게 선택 가능한 소주제를 구성
                    subtopic_name = st.selectbox(
                        "소주제를 선택하세요", 
                        [""] + subtopics.get(subject, []),  # 선택된 subject에 맞는 소주제만 표시
                        key=subtopic_name_key,
                        format_func=lambda x: '새 소과목 추가' if x == "" else x
                    )
                    if subtopic_name == "":
                        subtopic_name = st.text_input(f"소주제 {i+1} 이름", key=f"subtopic_{i}")
                with col2:
                    subtopic_file = st.file_uploader(f"소주제 {i+1}의 파일", key=f"file_{i}", type=["mp4", "mp3", "wav", "m4a", "pdf", "txt", "docx", "hwp"])

                if subtopic_name and subtopic_file:
                    question_types = {}
                    cols = st.columns(len(question_types_dict))
                    for j, (qt_kr, qt_en) in enumerate(question_types_dict.items()):
                        with cols[j]:
                            num = st.number_input(f"{qt_kr} 문제 수", min_value=0, max_value=20, value=5, key=f"{subtopic_name}_{qt_en}_num")
                            if num > 0:
                                question_types[qt_en] = num

                    subtopics_data[subtopic_name] = {
                        "file": subtopic_file,
                        "question_types": question_types
                    }

    if st.button("문제 생성", use_container_width=True):
        if subject and subtopics_data:
            st.button("생성 중단", use_container_width=True, on_click=cl.stop_generate)
            with st.spinner("문제를 생성하는 중입니다..."):
                result = cl.create_questions(subject, subtopics_data)
                if result == "success":
                    st.success("문제 생성이 완료되었습니다!")
                    st.session_state.questions_generated = True
                    st.rerun()
                else:
                    st.error(result)
        else:
            st.error("과목명과 최소 하나의 소주제 및 파일을 입력해주세요.")

    if st.session_state.get('questions_generated', False):
        show_generated_questions(subject)

def show_generated_questions(subject):
    st.header("생성된 문제")
    if 'questions' in st.session_state and st.session_state.questions:
        for subtopic_name, question_types in st.session_state.questions.items():
            with st.expander(f"{subtopic_name}", expanded=True):
                question_index = 1
                for qt, questions in question_types.items():
                    for i, question in enumerate(questions):
                        answer = st.session_state.answers[subtopic_name][qt][i]
                        with st.container(border=True):
                            col1, col2, col3, col4 = st.columns([7, 1, 1, 1], vertical_alignment="center")
                            with col1:
                                edit_mode_key = f"edit_mode_{subject}_{subtopic_name}_{question_index}"
                                if edit_mode_key not in st.session_state:
                                    st.session_state[edit_mode_key] = False

                                if st.session_state[edit_mode_key]:
                                    # 문제 수정 모드
                                    new_question_text = st.text_area("문제 텍스트를 수정하세요:", question[0] if isinstance(question, (tuple, list)) else question, key=f"edit_q_{subject}_{subtopic_name}_{question_index}")

                                    # 선택지 수정
                                    new_choices = []
                                    if isinstance(question, (tuple, dict)) and len(question) > 1:
                                        choices = question[1] if isinstance(question, tuple) else question.get('choices')
                                        if choices:
                                            for idx, choice in enumerate(choices):
                                                new_choice = st.text_input(f"선택지 {idx + 1} 수정:", value=choice, key=f"edit_choice_{subject}_{subtopic_name}_{question_index}_{idx}")
                                                new_choices.append(new_choice)

                                    # 정답 수정
                                    correct_answer = answer.split('\n')[0].split(':')[1].strip() if ':' in answer else answer.strip()
                                    new_correct_answer = st.text_input("정답을 수정하세요:", correct_answer, key=f"edit_a_{subject}_{subtopic_name}_{question_index}")

                                    # 해설 수정
                                    explanation = ' '.join(answer.split('\n')[1:]) if len(answer.split('\n')) > 1 else "해설 없음"
                                    new_explanation = st.text_area("해설을 수정하세요:", explanation, key=f"edit_explanation_{subject}_{subtopic_name}_{question_index}")

                                    if st.button("저장", key=f"save_{subject}_{subtopic_name}_{question_index}"):
                                        # 수정된 문제와 정답을 업데이트
                                        if isinstance(question, dict):
                                            question['question_text'] = new_question_text
                                            if new_choices:
                                                question['choices'] = new_choices
                                        elif isinstance(question, tuple):
                                            question = (new_question_text, new_choices) if new_choices else (new_question_text,)
                                        else:
                                            question = new_question_text

                                        st.session_state.questions[subtopic_name][qt][i] = question
                                        st.session_state.answers[subtopic_name][qt][i] = f"정답: {new_correct_answer}\n{new_explanation}"
                                        st.session_state[edit_mode_key] = False
                                        st.success("문제가 성공적으로 수정되었습니다.")
                                        st.rerun()

                                else:
                                    st.markdown(f"**문제 {question_index}.**")
                                    cl.display_question(question, qt)
                                    cl.display_answer(answer)

                            with col2:
                                if st.button(f"재생성", key=f"regenerate_{subject}_{subtopic_name}_{question_index}"):
                                    if cl.regenerate_question(subtopic_name, qt, i):
                                        st.success("문제가 재생성되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("재생성할 문제가 없습니다.")

                            with col3:
                                if st.button(f"수정", key=f"update_{subject}_{subtopic_name}_{question_index}"):
                                    st.session_state[edit_mode_key] = True
                                    st.rerun()

                            with col4:
                                if st.button(f"삭제", key=f"delete_{subject}_{subtopic_name}_{question_index}"):
                                    cl.delete_question(subtopic_name, qt, i)
                                    st.success("문제가 삭제되었습니다.")
                                    st.rerun()

                        question_index += 1

        if st.button("DB에 저장", use_container_width=True):
            if cl.save_questions_to_database(st.session_state.user_id, subject, subtopic_name):
                st.success("모든 문제가 성공적으로 DB에 저장되었습니다!")
            else:
                st.error("문제 저장 중 오류가 발생했습니다.")

        if st.button("문제와 답변 다운로드 (CSV)", use_container_width=True):
            csv_data = cl.generate_csv_for_questions(st.session_state.questions, st.session_state.answers, {})
            st.download_button(
                label="CSV 파일 다운로드",
                data=csv_data,
                file_name="questions_and_answers.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("아직 생성된 문제가 없습니다. '문제 생성' 버튼을 클릭하여 문제를 생성해주세요.")
        
def create_room():
    st.header("시험 출제")
    
    col1, col2 = st.columns(2, vertical_alignment="top")
    room_name = col1.text_input("시험 제목을 입력하세요")
    room_password = col2.text_input("비밀번호를 입력하세요", type='password')

    col1, col2, col3 = st.columns(3, vertical_alignment="top")
    start_datetime = col1.date_input("시험 시작 날짜")
    start_time = col2.time_input("시험 시작 시간")
    start_datetime = datetime.combine(start_datetime, start_time)
    
    duration = col3.number_input("시험 시간 (분)", min_value=1, value=60)
    end_datetime = start_datetime + timedelta(minutes=duration)
    
    st.write(f"시험 종료 시간: {end_datetime}")
    
    categorized_questions = cl.get_categorized_questions(cl.get_session_state('user_id'))
    
    subjects = list(categorized_questions.keys())
    selected_subjects = st.multiselect("과목 선택 (여러 개 선택 가능)", subjects)
    
    all_subtopics = [subtopic for subject in selected_subjects for subtopic in categorized_questions[subject].keys()]
    selected_subtopics = st.multiselect("소주제 선택 (여러 개 선택 가능)", list(set(all_subtopics)))

    # 선택된 과목과 소주제에 해당하는 모든 질문 가져오기
    all_questions = [q for subject in selected_subjects 
                     for subtopic in categorized_questions[subject] 
                     if subtopic in selected_subtopics
                     for q in categorized_questions[subject][subtopic]]
    
    q_types = {
        "multiple-choice": "객관식",
        "short answer": "주관식",
        "true/false": "참/거짓",
        "fill-in-the-blank": "빈칸 채우기"
    }
    
    col1, col2 = st.columns(2, vertical_alignment="bottom")
    selected_category = col1.selectbox("질문 유형 선택", ["전체"] + list(q_types.values()))
    cl.set_session_state('selected_category', selected_category)

    # 선택된 카테고리에 따라 질문 필터링
    if selected_category != "전체":
        selected_type = next(k for k, v in q_types.items() if v == selected_category)
        filtered_questions = [q for q in all_questions if q['question_type'] == selected_type]
    else:
        filtered_questions = all_questions

    total_questions = col2.number_input("총 문제 개수", min_value=0, max_value=len(filtered_questions))

    # 랜덤 선택 적용
    if total_questions > 0:
        questions_to_show = random.sample(filtered_questions, min(total_questions, len(filtered_questions)))
    else:
        questions_to_show = filtered_questions

    cl.set_session_state('questions_to_show', questions_to_show)

    # 전체 선택/선택 해제 버튼 추가
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("전체 선택", use_container_width=True):
            for q in questions_to_show:
                cl.set_session_state(f'global_selected_questions_{q["id"]}', True)
            st.success(f"현재 표시된 모든 문제({len(questions_to_show)}개)가 선택되었습니다.")
            st.rerun()
    with col3:
        if st.button("선택 해제", use_container_width=True):
            for q in questions_to_show:
                cl.set_session_state(f'global_selected_questions_{q["id"]}', False)
            st.success(f"현재 표시된 모든 문제({len(questions_to_show)}개)의 선택이 해제되었습니다.")
            st.rerun()

    # 질문 목록 표시
    questions_per_row = 3
    with st.container(height=700):
        rows = [st.columns(questions_per_row) for _ in range((len(questions_to_show) + questions_per_row - 1) // questions_per_row)]

        for i, q in enumerate(questions_to_show):
            col = rows[i // questions_per_row][i % questions_per_row]
            with col:
                with st.container(border=True):
                    checkbox_key = f"checkbox_{q['id']}"
                    is_checked = st.checkbox("", key=checkbox_key,
                                             value=cl.get_session_state(f'global_selected_questions_{q["id"]}', False))
                    cl.set_session_state(f'global_selected_questions_{q["id"]}', is_checked)

                    st.write(f"**문제**: {q['question_text']}")
                    if q.get('choices'):
                        st.write("**선택지**:")
                        choices = q['choices']
                        if isinstance(choices, list):
                            for choice in choices:
                                st.write(choice)
                        elif isinstance(choices, str):
                            choice_list = eval(choices)
                            for choice in choice_list:
                                st.write(choice)
                    st.write(f"**유형**: {q_types.get(q.get('question_type', ''), '기타')}")

    st.write("")
    col1, col2 = st.columns(2)
    with col2:
        apply = st.button("적용", use_container_width=True)
    with col1:
        if st.button("초기화", use_container_width=True):
            for q in all_questions:
                cl.set_session_state(f'global_selected_questions_{q["id"]}', False)
            cl.set_session_state('selected_questions', [])
            st.success("선택된 문제가 초기화되었습니다.")
            st.rerun()

    # 선택된 문제 저장
    if apply:
        selected_questions = [q for q in questions_to_show if cl.get_session_state(f'global_selected_questions_{q["id"]}', False)]
        cl.set_session_state('selected_questions', selected_questions)
        st.success(f"선택된 문제가 적용되었습니다. 총 {len(selected_questions)}개의 문제가 선택되었습니다.")

    if cl.get_session_state('selected_questions'):
        st.subheader("선택된 문제 목록")
        
        cols = st.columns(2)
        
        for i, selected_question in enumerate(cl.get_session_state('selected_questions')):
            with cols[i % 2]:
                with st.expander(f"**문제 {i+1}: {selected_question['question_text'][:30]}...**", expanded=False):
                    st.markdown(f"**문제 {i+1}: {selected_question['question_text']}**")
                    
                    if selected_question.get('choices'):
                        choices = selected_question['choices']
                        if isinstance(choices, list) and len(choices) > 0:
                            if isinstance(choices[0], str) and choices[0].startswith(('a)', 'b)', 'c)', 'd)')):
                                for choice in choices:
                                    st.markdown(choice)
                            else:
                                for j, choice in enumerate(choices):
                                    st.markdown(f"{chr(97 + j)}) {choice}")
                        elif isinstance(choices, str):
                            choice_list = eval(choices)
                            for choice in choice_list:
                                st.markdown("&emsp;" + choice)
                    
                    st.markdown(f"**정답:** {selected_question['answer_text']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**과목:** {selected_question['subject']}")
                    with col2:
                        st.markdown(f"**소주제:** {selected_question['subtopic']}")
       
        # 총 선택된 문제 수와 초기화 버튼은 컬럼 밖에 배치
        st.markdown(f"**총 선택된 문제 수:** {len(cl.get_session_state('selected_questions'))}")

    if st.button("시험 만들기", use_container_width=True):
        if room_name and room_password and cl.get_session_state('selected_questions'):
            room_id = cl.create_room(room_name, cl.get_session_state('user_id'), 
                                     [q['id'] for q in cl.get_session_state('selected_questions')], 
                                     room_password, start_datetime, end_datetime)
            if room_id:
                st.success(f"시험이 생성되었습니다. 시험 ID: {room_id}")
            else:
                st.error("시험 생성 중 오류가 발생했습니다.")
        else:
            st.error("모든 필드를 채워주세요.")
            
def show_user_rooms():
    st.header("시험 목록")
    if st.button("↺ 새로고침", key="refresh_rooms", use_container_width=True):
        st.rerun()

    rooms = cl.get_user_rooms_info(cl.get_session_state('user_id'))
    
    if not rooms:
        st.info("현재 활성화된 시험이 없습니다.")
    else:
        cols = st.columns(3)
        for i, room in enumerate(rooms):
            with cols[i % 3]:
                with st.expander(f"{'🟢' if room['status'] == 'open' else '🔴'} {room['room_name']}", expanded=False):
                    st.markdown(f"### {room['room_name']}")
                    st.markdown(f"**시험 ID:** {room['id']}")
                    st.markdown(f"**응시 인원:** {room['Participants']}명")
                    st.markdown(f"**응시 기간:** {cl.format_time_range(room['start_time'], room['end_time'])}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if room['status'] == 'open':
                            if st.button("🔒 닫기", key=f"close_{room['id']}", use_container_width=True):
                                if cl.close_open_room(room['id'], 'close'):
                                    st.success("시험이 닫혔습니다.")
                                    st.rerun()
                        else:
                            if st.button("🔓 열기", key=f"open_{room['id']}", use_container_width=True):
                                if cl.close_open_room(room['id'], 'open'):
                                    st.success("시험이 다시 열렸습니다.")
                                    st.rerun()
                    with col2:
                        if st.button("🗑️ 삭제", key=f"delete_{room['id']}", use_container_width=True):
                            if cl.delete_room_by_id(room['id']):
                                st.success("시험이 삭제되었습니다.")
                                st.rerun()
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        if st.button("📝 문제 보기", key=f"view_{room['id']}", use_container_width=True):
                            cl.set_session_state('view_questions', room['id'])
                            st.rerun()
                    with col4:
                        if st.button("📊 결과 보기", key=f"results_{room['id']}", use_container_width=True):
                            cl.set_session_state('view_results', room['id'])
                            st.rerun()

    if cl.get_session_state('view_questions'):
        show_room_questions(cl.get_session_state('view_questions'))
    
    if cl.get_session_state('view_results'):
        show_room_results(cl.get_session_state('view_results'))

def show_room_questions(room_id):
    st.header("문제 보기 및 수정")
    if st.button("❌ 닫기", key=f"close_questions_{room_id}", use_container_width=True):
        cl.clear_session_state('view_questions')
        st.rerun()

    questions = cl.get_room_questions_and_answers(room_id)
    if not questions:
        st.warning("이 시험에는 할당된 문제가 없습니다.")
        return

    for i, question in enumerate(questions, 1):
        edit_mode = cl.get_session_state(f"edit_mode_{question['id']}", False)
        with st.expander(f"문제 {i}", expanded=edit_mode):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"##### {question['question_text']}")
                st.markdown(f"**유형:** {cl.get_question_type_kr(question['question_type'])}")
                if question['question_type'] == "multiple-choice":
                    choices = json.loads(question['choices'])
                    for choice in choices:
                        st.markdown(f"- {choice}")
                st.markdown(f"**정답:** {question['answer_text']}")
                st.markdown(f"**해설:** {question['explanation']}")
            with col2:
                if st.button("수정", key=f"edit_{question['id']}", use_container_width=True):
                    cl.set_session_state(f"edit_mode_{question['id']}", True)
                    st.rerun()

            if edit_mode:
                new_question_text = st.text_area("문제", value=question['question_text'])
                new_answer_text = st.text_area("정답", value=question['answer_text'])
                new_explanation = st.text_area("해설", value=question['explanation'])

                if question['question_type'] == "multiple-choice":
                    choices = json.loads(question['choices'])
                    new_choices = []
                    for idx, choice in enumerate(choices):
                        new_choice = st.text_input(f"선택지 {idx + 1}", value=choice, key=f"choice_{question['id']}_{idx}")
                        new_choices.append(new_choice)

                col3, col4 = st.columns(2)
                with col3:
                    if st.button("저장", key=f"save_{question['id']}", use_container_width=True):
                        updated_data = {
                            'question_text': new_question_text,
                            'answer_text': new_answer_text,
                            'explanation': new_explanation,
                        }
                        if question['question_type'] == "multiple-choice":
                            updated_data['choices'] = new_choices
                        if cl.update_question(question['id'], updated_data):
                            st.success("문제가 업데이트되었습니다.")
                            cl.clear_session_state(f"edit_mode_{question['id']}")
                            st.rerun()
                        else:
                            st.error("문제 업데이트 중 오류가 발생했습니다.")
                with col4:
                    if st.button("취소", key=f"cancel_{question['id']}", use_container_width=True):
                        cl.clear_session_state(f"edit_mode_{question['id']}")
                        st.rerun()

def show_room_results(room_id):
    col1, col2 = st.columns([9, 1], vertical_alignment="bottom")
    with col1:
        st.header(f"시험 결과", divider='rainbow')
    with col2:
        if st.button("❌ 닫기", key=f"close_results_{room_id}"):
            cl.clear_session_state('view_results')
            st.rerun()

    df, avg_score, total_participants, avg_correct, avg_total = cl.get_room_results(room_id)
    
    if df is not None:
        st.subheader("🏆 참여 학생 순위")
        
        st.dataframe(
            df.rename(columns={
                'rank': '순위', 
                'name': '이름', 
                'student_id': '학번', 
                'score': '점수', 
                'correct_answers': '정답 수', 
                'total_questions': '총 질문'
            })[['순위', '이름', '학번', '점수', '정답 수', '총 질문']],
            use_container_width=True,
            hide_index=True
        )
        col1, col2 = st.columns([2, 1])
                
        with col1:
            st.subheader("📊 점수 분포")
            hist_df = cl.create_score_distribution_chart(df['score'])
            # Altair를 사용해 막대 그래프 생성
            chart = alt.Chart(hist_df).mark_bar().encode(
                x=alt.X('점수 구간', sort=None),  # x축 정렬 (sort=None으로 기본 정렬)
                y='참가자 수'
            ).properties(
                width=600,  # 그래프 너비
                height=400  # 그래프 높이
            ).configure_axis(
                labelAngle=0  # x축 레이블의 각도를 0도로 설정하여 가로 정렬
            )

            st.altair_chart(chart, use_container_width=True)

        with col2:
            st.subheader("📈 통계")
            st.metric("평균 점수", f"{avg_score:.1f}점")
            st.metric("총 참가자 수", f"{total_participants}명")
            st.metric("평균 정답 수", f"{avg_correct:.1f}개")
            st.metric("문제 수", f"{avg_total:.0f}개")
        
        st.divider()

        # 정렬 순서를 전환하는 함수
        def toggle_sort_order():
            current_order = cl.get_session_state('sort_order', 'default')
            new_order = 'lowest' if current_order == 'default' else 'default'
            cl.set_session_state('sort_order', new_order)
            st.rerun()

        # 정렬 버튼 표시 및 정렬 순서 전환
        sort_order = cl.get_session_state('sort_order', 'default')
        sort_button_text = '정답률 낮은 문제순으로 정렬' if sort_order == 'default' else '기본순으로 정렬'

        col1, col2 = st.columns([5, 1.2])
        with col1:
            st.subheader("🎯 문제별 정보 확인")
        with col2:
            if st.button(sort_button_text, key='sort_button'):
                toggle_sort_order()

        question_stats = cl.get_question_stats(room_id)
        if question_stats:
            cols = st.columns(2)
            if sort_order == 'lowest':
                question_stats.sort(key=lambda x: x['correct_ratio'])
            for i, stat in enumerate(question_stats):
                with cols[i % 2]:
                    with st.expander(f"문제: {cl.truncate_text(stat['question_text'], 50)}"):
                        st.progress(float(stat['correct_ratio']) / 100)
                        st.write(f"**정답:** {stat['answer_text']}")
                        st.write(f"**가장 많이 입력한 오답:** {stat['most_frequent_incorrect_answer'] or '없음'}")
                        st.write(f"**정답률:** {stat['correct_ratio']:.2f}% ({stat['correct_answers']}/{stat['total_answers']})")
        else:
            st.info("문제 통계 정보가 없습니다.")
    else:
        st.info("이 시험에는 아직 참가자가 없습니다.")

def show_room_list():
    st.header("시험 목록")
    if st.button("↺ 새로고침", key="refresh_rooms", use_container_width=True):
        st.rerun()

    rooms = cl.get_all_available_rooms()

    if not rooms:
        st.info("현재 활성화된 시험이 없습니다.")
    else:
        cols = st.columns(3)
        for i, room in enumerate(rooms):
            with cols[i % 3]:
                status_emoji = "🟢" if room['status'] == 'open' else "🔴"
                
                with st.expander(f"**{status_emoji} {room['room_name']}**", expanded=False):
                    st.markdown(f"### {room['room_name']}")
                    st.markdown(f"**시험 ID:** {room['id']}")
                    st.markdown(f"**출제자:** {room['creator_name']}")
                    st.markdown(f"**참여자:** {room['participant_count']}명")
                    st.markdown(f"**시간:** {cl.format_time_range(room['start_time'], room['end_time'])}")
                    
                    if st.button("입장", key=f"enter_room_{room['id']}", use_container_width=True):
                        cl.set_session_state('selected_room_id', room['id'])
                        cl.set_session_state('submit_stage', 0)
                        st.rerun()

    if cl.get_session_state('selected_room_id'):
        handle_specific_room(cl.get_session_state('selected_room_id'))

def handle_specific_room(room_id):
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    cl.set_session_state('result', None)
    cl.set_session_state('submitted', False)
    cl.set_session_state('confirm_submission', False)
    cl.set_session_state('show_explanations', False)
    
    if f'room_authenticated_{room_id}' not in st.session_state:
        st.session_state[f'room_authenticated_{room_id}'] = False

    room_info = cl.get_room_info(room_id, include_questions=False)
    
    if room_info is None:
        cl.clear_session_state('selected_room_id')
        cl.clear_session_state(f'room_authenticated_{room_id}')
        return
    
    show_room_info(room_info)

    if not cl.get_session_state(f'room_authenticated_{room_id}', False):
        authenticate_room_form(room_id)
    else:
        user_id = cl.get_session_state('user_id')
        
        if cl.check_submission_status(user_id, room_id):
            show_submitted_results(user_id, room_id)
        else:
            current_time = datetime.now()
            start_time, end_time, status = cl.get_room_time_info(room_id)
            
            if start_time and start_time > current_time:
                time_to_start = (start_time - current_time).total_seconds()
                placeholder = st.empty()
                cl.run_timer(int(time_to_start), lambda remaining: placeholder.warning(f"시험 시작까지 남은 시간: {str(timedelta(seconds=remaining))}"))
                st.success("시험이 시작되었습니다! 문제를 확인하세요.")
                st.rerun()
            elif status == 'closed':
                st.error("이 시험은 이미 닫혔습니다.")
                return
            elif end_time and end_time < current_time:
                st.error("이 시험의 종료 시간이 지났습니다.")
                return
            else:
                show_questions(cl.get_room_info(room_id))
                
def show_room_info(room_info):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header(f"시험 정보: {room_info['room_name']}")
    
    with col2:
        if st.button("시험 나가기", key=f"exit_room_info_{room_info['id']}", use_container_width=True):
            cl.clear_session_state('selected_room_id')
            cl.clear_session_state(f'room_authenticated_{room_info["id"]}')
            cl.set_session_state('submit_stage', 0)
            st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        st.write(f"시험 ID: {room_info['id']}")
        st.write(f"생성 시간: {room_info['created_at']}")
    with col4:
        st.write(f"시작 시간: {room_info['start_time']}")
        if room_info['end_time']:
            st.write(f"종료 시간: {room_info['end_time']}")
        st.write(f"상태: {room_info['status']}")

def authenticate_room_form(room_id):
    st.header("시험 입장")
    password = st.text_input("시험 비밀번호를 입력하세요", type='password')

    if st.button("입장", key="authenticate_room_button", use_container_width=True):
        if cl.handle_room_authentication(room_id, password):
            cl.set_session_state(f'room_authenticated_{room_id}', True)
            st.success("인증되었습니다. 시험에 입장합니다.")
            st.rerun()
        else:
            st.error("잘못된 비밀번호입니다.")

def show_submitted_results(user_id, room_id):
    st.success("이미 이 시험에서 문제를 제출했습니다.")
    result = cl.get_user_room_answers(user_id, room_id)
    if result:
        st.success(f"당신의 점수: {result['score']}/{result['total_questions']} ({result['percentage_score']:.2f}%)")

        if st.button("문제 해설 보기", use_container_width=True):
            cl.set_session_state('show_explanations', True)

        if cl.get_session_state('show_explanations', False):
            show_questions(cl.get_room_info(room_id), disabled=True)
    else:
        st.error("결과를 불러오는 데 실패했습니다.")

def show_questions(room_info, disabled=False):
    full_room_info = cl.get_room_info(room_info['id'])
    questions = full_room_info['questions']

    st.header(f"문제 목록")
    st.write(f"참가자: {cl.get_session_state('user')['name']} (학번: {cl.get_session_state('user').get('student_id', 'N/A')})")

    st.markdown(
            """
        <style>
            div[role=radiogroup] label:first-of-type {
                visibility: hidden;
                height: 0px;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )

    user_answers = cl.get_session_state('user_answers', {})

    for i, question in enumerate(questions, 1):
        with st.container(border=True):
            st.markdown(f"**문제 {i}.**")
            st.markdown(question['question_text'])

            question_type = question['question_type']
            user_answer = user_answers.get(str(question['id']), '')

            if question_type == "multiple-choice" and question['choices']:
                try:
                    choices = question['choices']
                    if not isinstance(choices, str):
                        choices = str(choices)
                    
                    choices = eval(choices)
                    if isinstance(choices, list):
                        choices = ' '.join(choices)
                    
                    choices = re.findall(r'[a-d]\)\s.*?(?=\s*[a-d]\)|$)', choices)
                    a_choices = ["선택하지 않음"] + choices
                    current_index = a_choices.index(user_answer) if user_answer in a_choices else 0
                    
                    user_answer = st.radio("정답을 선택하세요:", a_choices, key=f"answer_{room_info['id']}_{i}",
                                        index=current_index, disabled=disabled)
                    user_answer = user_answer if user_answer != "선택하지 않음" else None
                except Exception as e:
                    st.error(f"선택지 처리 중 오류 발생: {str(e)}")
                    st.write(f"원본 선택지: {question['choices']}")
                    user_answer = st.text_input("정답을 입력하세요:", key=f"answer_{room_info['id']}_{i}", 
                                                value=user_answer, disabled=disabled)

            elif question_type == "true/false":
                options = ["선택하지 않음", "참", "거짓"]
                current_index = options.index(user_answer) if user_answer in options else 0
                user_answer = st.radio("정답을 선택하세요:", options, key=f"answer_{room_info['id']}_{i}",
                                    index=current_index, disabled=disabled)
                user_answer = user_answer if user_answer != "선택하지 않음" else None

            elif question_type in ["short answer", "fill-in-the-blank"]:
                user_answer = st.text_input("답변을 입력하세요:", key=f"answer_{room_info['id']}_{i}", 
                                            value=user_answer, disabled=disabled)

            user_answers[str(question['id'])] = user_answer

            if disabled:
                st.markdown(f"**정답:** {question['answer_text']}")
                st.markdown(f"**해설:** {question['explanation']}")

    cl.set_session_state('user_answers', user_answers)

    if not disabled and not cl.get_session_state('submitted', False):
        if cl.get_session_state('submit_stage', 0) == 0:
            if st.button("제출", key=f"submit_{room_info['id']}", use_container_width=True):
                cl.set_session_state('submit_stage', 1)
                st.rerun()
        elif cl.get_session_state('submit_stage') == 1:
            st.warning("정말로 제출하시겠습니까? 제출 후에는 수정할 수 없습니다.")
            if st.button("최종 제출", key=f"final_submit_{room_info['id']}", use_container_width=True):
                submit_answers(cl.get_session_state('user_id'), room_info['id'], user_answers)
        
    if room_info['end_time']:
        time_remaining = cl.calculate_time_remaining(room_info['end_time'])
        if time_remaining > 0:
            timer_placeholder = st.empty()
            cl.run_timer(int(time_remaining), lambda remaining: timer_placeholder.warning(f"남은 시간: {str(timedelta(seconds=remaining))}"))
            if not cl.get_session_state('submitted', False):
                auto_submit(cl.get_session_state('user_id'), room_info['id'], user_answers)
        else:
            st.error("이 시험의 종료 시간이 지났습니다.")
            return

    if cl.get_session_state('submitted', False):
        result = cl.get_session_state('result')
        st.success(f"당신의 점수: {result['score']}/{result['total_questions']} ({result['percentage_score']:.2f}%)")

def submit_answers(user_id, room_id, user_answers):
    if cl.save_user_room_answers(user_id, room_id, user_answers):
        result = cl.calculate_user_score(user_id, room_id)
        if result:
            cl.set_session_state('result', result)
            cl.set_session_state('submitted', True)
            st.success(f"모든 답변이 성공적으로 제출되었습니다.")
            st.success(f"당신의 점수: {result['score']}/{result['total_questions']} ({result['percentage_score']:.2f}%)")
            st.rerun()
        else:
            st.error("채점 중 오류가 발생했습니다.")
    else:
        st.error("답변 저장 중 오류가 발생했습니다. 다시 시도해주세요.")

def auto_submit(user_id, room_id, user_answers):
    result = cl.auto_submit_answers(user_id, room_id, user_answers)
    if result:
        st.warning("시간이 다 되었습니다. 답안이 자동으로 제출되었습니다.")
        st.success(f"당신의 점수: {result['score']}/{result['total_questions']} ({result['percentage_score']:.2f}%)")
        st.rerun()
    else:
        st.error("자동 제출 중 오류가 발생했습니다.")

def create_personal_questions():
    st.header("개인 맞춤형 문제 생성")

    question_types_dict = {
        "객관식": "multiple-choice",
        "단답형": "short answer",
        "참/거짓": "true/false",
        "빈칸 채우기": "fill-in-the-blank"
    }

    subjects, subtopics = cl.get_subjects_and_subtopics()
    subject = st.selectbox("과목명을 선택하세요", [""] + subjects, format_func=lambda x: '새 과목 추가' if x == "" else x)

    if subject == "":
        subject = st.text_input("새 과목명을 입력하세요")
    
    if subject:
        st.subheader("소주제 및 파일 입력")
        num_subtopics = st.number_input("소과목 수를 입력하세요", min_value=1, value=1)

        subtopics_data = {}
        for i in range(num_subtopics):
            subtopic_name_key = f"subtopic_name_{i}"
            if subtopic_name_key not in st.session_state:
                st.session_state[subtopic_name_key] = ""

            expander_title = st.session_state[subtopic_name_key] if st.session_state[subtopic_name_key] else f"소주제 {i+1} 설정"
            with st.expander(expander_title):
                col1, col2 = st.columns(2)
                with col1:
                    # 주어진 subtopics 데이터 구조에 맞게 선택 가능한 소주제를 구성
                    subtopic_name = st.selectbox(
                        "소주제를 선택하세요", 
                        [""] + subtopics.get(subject, []),  # 선택된 subject에 맞는 소주제만 표시
                        key=subtopic_name_key,
                        format_func=lambda x: '새 소과목 추가' if x == "" else x
                    )
                    if subtopic_name == "":
                        subtopic_name = st.text_input(f"소주제 {i+1} 이름", key=f"subtopic_{i}")
                with col2:
                    subtopic_file = st.file_uploader(f"소주제 {i+1}의 파일", key=f"file_{i}", type=["mp4", "mp3", "wav", "m4a", "pdf", "txt", "docx", "hwp"])

                if subtopic_name and subtopic_file:
                    question_types = {}
                    cols = st.columns(len(question_types_dict))
                    for j, (qt_kr, qt_en) in enumerate(question_types_dict.items()):
                        with cols[j]:
                            num = st.number_input(f"{qt_kr} 문제 수", min_value=0, max_value=20, value=5, key=f"{subtopic_name}_{qt_en}_num")
                            if num > 0:
                                question_types[qt_en] = num

                    subtopics_data[subtopic_name] = {
                        "file": subtopic_file,
                        "question_types": question_types
                    }

    if st.button("문제 생성", use_container_width=True):
        if subject and subtopics_data:
            with st.spinner("문제를 생성하는 중입니다..."):
                result = cl.create_personal_questions(cl.get_session_state('user_id'), subject, subtopics_data)
                if result:
                    st.success("문제 생성이 완료되었습니다!")
                    cl.set_session_state('personal_questions_generated', True)
                    #st.rerun()
                else:
                    st.error("문제 생성 중 오류가 발생했습니다.")
        else:
            st.error("과목명과 최소 하나의 소주제 및 파일을 입력해주세요.")

    if st.session_state.get('personal_questions_generated', False):
        if cl.get_session_state('extracted_text') is not None:
            for subtopic_name, text in cl.get_session_state('extracted_text').items():
                st.download_button("", text, f"{subtopic_name}_extracted_text.txt")
            
        show_personal_questions()

def show_personal_questions():
    st.header("생성된 개인 문제")
    st.markdown(
        """
    <style>
        div[role=radiogroup] label:first-of-type {
            visibility: hidden;
            height: 0px;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    if 'personal_user_answers' not in st.session_state:
        st.session_state.personal_user_answers = {}

    question_index = 1
    for subtopic_name, question_types in st.session_state.personal_questions.items():
        with st.expander(f"{subtopic_name}", expanded=True):
            for qt, questions in question_types.items():
                for i, question in enumerate(questions):
                    answer = st.session_state.personal_answers[subtopic_name][qt][i]
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([8, 1, 1], vertical_alignment="center")
                        with col1:
                            st.markdown(f"**문제 {question_index}.**")
                            
                            # 질문 데이터 처리
                            if isinstance(question, tuple):
                                question_text = question[0]
                                choices = question[1] if len(question) > 1 else None
                            elif isinstance(question, dict):
                                question_text = question.get('question_text', '')
                                choices = question.get('choices')
                            else:
                                question_text = str(question)
                                choices = None

                            st.markdown(question_text)
                            
                            # 사용자 답변 입력
                            if qt == "multiple-choice":
                                if isinstance(choices, str):
                                    choices = json.loads(choices)
                                choices = ["선택하지 않음"] + (choices or [])
                                user_answer = st.radio("정답을 선택하세요:", choices, key=f"personal_q{question_index}_options", index=0)
                                user_answer = user_answer if user_answer != "선택하지 않음" else None
                            elif qt == "true/false":
                                choices = ["선택하지 않음", "참", "거짓"]
                                user_answer = st.radio("정답을 선택하세요:", choices, key=f"personal_q{question_index}_tf", index=0)
                                user_answer = user_answer if user_answer != "선택하지 않음" else None
                            elif qt == "fill-in-the-blank":
                                user_answer = st.text_input("빈칸에 들어갈 답을 입력하세요:", key=f"personal_q{question_index}_blank")
                            else:  # 단답형
                                user_answer = st.text_input("답변을 입력하세요 (1-3단어):", key=f"personal_q{question_index}_input")

                            # 답변을 session state에 저장
                            st.session_state.personal_user_answers[question_index] = user_answer

                        with col2:
                            if st.button(f"재생성", key=f"personal_regenerate_{subtopic_name}_{question_index}"):
                                if cl.regenerate_personal_question(subtopic_name, qt, i):
                                    st.success("문제가 재생성되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("재생성할 문제가 없습니다.")

                        with col3:
                            if st.button(f"삭제", key=f"personal_delete_{subtopic_name}_{question_index}"):
                                cl.delete_personal_question(subtopic_name, qt, i)
                                st.success("문제가 삭제되었습니다.")
                                st.rerun()

                    question_index += 1

    # 채점 버튼
    if st.button("채점하기", use_container_width=True):
        user_id = cl.get_session_state('user_id')
        correct_count, total_questions, results = cl.grade_personal_questions(user_id, st.session_state.personal_user_answers)
        cl.set_session_state('personal_grading_results', results)
        cl.set_session_state('personal_grading_done', True)
        st.success(f"채점이 완료되었습니다. 점수: {correct_count}/{total_questions}")
        
        st.rerun()

    # 채점 결과 표시
    if cl.get_session_state('personal_grading_done', False):
        cl.show_personal_grading_results()

def show_previous_learning_records():
    st.header("이전 학습 기록")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 날짜", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("종료 날짜", value=datetime.now())

    subjects, all_subtopics = cl.get_subjects_and_subtopics()
    col3, col4 = st.columns(2)
    with col3:
        selected_subject = st.selectbox("과목 선택", ["전체"] + subjects)
    with col4:
        if selected_subject != "전체":
            subtopics = ["전체"] + all_subtopics.get(selected_subject, [])
            selected_subtopic = st.selectbox("소주제 선택", subtopics)
        else:
            selected_subtopic = "전체"

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    user_questions = cl.get_previous_learning_records(
        cl.get_session_state('user_id'),
        start_date=start_datetime,
        end_date=end_datetime,
        subject=selected_subject if selected_subject != "전체" else None,
        subtopic=selected_subtopic if selected_subtopic != "전체" else None
    )

    if user_questions:
        for question in user_questions:
            with st.expander(f"문제: {cl.truncate_text(question['question_text'], 50)}...", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"##### 문제: {question['question_text']}")
                    st.markdown(f"###### 과목: {question['subject']}")
                    st.markdown(f"###### 소과목: {question['subtopic']}")
                with col2:
                    st.markdown(f"###### 문제 유형: {cl.get_question_type_kr(question['question_type'])}")
                    st.markdown(f"###### 생성 날짜: {question['created_at']}")
                
                if question['question_type'] == 'multiple-choice' and question['choices']:
                    choices = json.loads(question['choices'])
                    st.markdown("**보기:**")
                    for choice in choices:
                        st.markdown(f"- {choice}")

                st.markdown(f"**정답:** {question['answer_text']}")
                st.markdown(f"**해설:** {question['explanation']}")
                st.markdown(f"**사용자 답변:** {question['user_answer']}")
                st.markdown(f"**정답 여부:** {'⭕' if question['is_correct'] else '❌'}")

                if st.button(f"삭제", key=f"delete_{question['id']}", use_container_width=True):
                    if cl.delete_personal_study_question(question['id']):
                        st.success("문제가 삭제되었습니다.")
                        st.rerun()
                    else:
                        st.error("문제 삭제 중 오류가 발생했습니다.")
    else:
        st.info("선택한 조건에 맞는 학습 기록이 없습니다.")

def solve_previous_questions():
    st.header("이전 문제 풀기")
    if 'solving_session' not in st.session_state:
        show_question_selection()
    elif 'show_results' in st.session_state and st.session_state.show_results:
        show_solving_results()
    else:
        show_question_solving_session()

def show_question_selection():
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 날짜", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("종료 날짜", value=datetime.now())

    subjects, all_subtopics = cl.get_subjects_and_subtopics()
    col3, col4 = st.columns(2)
    with col3:
        selected_subject = st.selectbox("과목 선택", ["전체"] + subjects)
    with col4:
        if selected_subject != "전체":
            subtopics = ["전체"] + all_subtopics.get(selected_subject, [])
            selected_subtopic = st.selectbox("소주제 선택", subtopics)
        else:
            selected_subtopic = "전체"

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    user_questions = cl.get_previous_learning_records(
        cl.get_session_state('user_id'),
        start_date=start_datetime,
        end_date=end_datetime,
        subject=selected_subject if selected_subject != "전체" else None,
        subtopic=selected_subtopic if selected_subtopic != "전체" else None
    )

    if user_questions:
        st.subheader("풀고 싶은 문제를 선택하세요")

        selected_questions = []
        cols = st.columns(3)
        for i, q in enumerate(user_questions):
            with cols[i % 3]:
                with st.expander(f"**문제: {cl.truncate_text(q['question_text'], 50)}...**", expanded=False):
                    st.write(f"**문제 전문:** {q['question_text']}")
                    if q['question_type'] == 'multiple-choice' and q['choices']:
                        choices = json.loads(q['choices']) if isinstance(q['choices'], str) else q['choices']
                        for choice in choices:
                            st.write(f"- {choice}")
                    st.write(f"**이전 정답 여부:** {'정답 ⭕' if q['is_correct'] else '오답 ❌'}")
                    st.write(f"과목: {q['subject']} - {q['subtopic']}")
                    st.write(f"**유형:** {cl.get_question_type_kr(q['question_type'])}")
                    
                    is_selected = st.checkbox("문제 선택", key=f"select_{q['id']}")
                    if is_selected:
                        selected_questions.append(q)

        if selected_questions:
            if st.button("선택한 문제 풀기", use_container_width=True):
                cl.set_session_state('solving_session', {
                    'questions': selected_questions,
                    'user_answers': {}
                })
                cl.set_session_state('show_results', False)
                st.rerun()

    else:
        st.info("선택한 조건에 맞는 문제가 없습니다.")

def show_question_solving_session():
    session = cl.get_session_state('solving_session')
    st.subheader("선택한 문제 풀기")
    
    cols = st.columns(2)
    for i, question in enumerate(session['questions']):
        with cols[i % 2]:
            with st.container(border=True):
                st.write(f"**문제 {i+1}:** {question['question_text']}")
                
                if question['question_type'] == 'multiple-choice':
                    choices = json.loads(question['choices']) if isinstance(question['choices'], str) else question['choices']
                    user_answer = st.radio(f"답을 선택하세요 (문제 {i+1}):", choices, key=f"q_{i}")
                elif question['question_type'] == 'true/false':
                    user_answer = st.radio(f"답을 선택하세요 (문제 {i+1}):", ["참", "거짓"], key=f"q_{i}")
                else:
                    user_answer = st.text_input(f"답을 입력하세요 (문제 {i+1}):", key=f"q_{i}")
                
                session['user_answers'][i] = user_answer

    if st.button("제출", use_container_width=True):
        cl.set_session_state('show_results', True)
        st.rerun()

def show_solving_results():
    session = cl.get_session_state('solving_session')
    st.subheader("결과")
    correct_count = 0
    cols = st.columns(2)
    for i, question in enumerate(session['questions']):
        with cols[i % 2]:
            with st.expander(f"문제 {i+1}", expanded=False):
                user_answer = session['user_answers'].get(i, "답변 없음")
                is_correct, correct_answer, explanation = cl.solve_previous_question(question['id'], user_answer)

                st.write(f"**문제:** {question['question_text']}")
                
                if question['question_type'] == 'multiple-choice' and question['choices']: 
                    choices = json.loads(question['choices']) if isinstance(question['choices'], str) else question['choices']
                    for choice in choices:
                        st.markdown(f"- {choice}")
                
                st.write(f"**제출한 답변:** {user_answer}")
                st.write(f"**정답:** {correct_answer}")
                st.write(f"**해설:** {explanation}")
                
                if is_correct:
                    st.success("정답입니다!")
                    correct_count += 1
                else:
                    st.error("오답입니다.")

    total_questions = len(session['questions'])
    st.subheader(f"최종 점수: {correct_count}/{total_questions}")

    if st.button("다시 문제 선택하기", use_container_width=True):
        cl.clear_session_state('solving_session')
        cl.clear_session_state('show_results')
        st.rerun()

if __name__ == "__main__":
  
    # CSS for desktop optimization
    st.markdown("""
    <style>
    .reportview-container .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    main()