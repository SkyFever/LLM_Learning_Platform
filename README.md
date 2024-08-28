# LLM_Learning_Platform

## 주요 기능

- 사용자 인증 (로그인/회원가입)
- 관리자 모드와 학생 모드 구분
- 다양한 유형의 문제 생성 및 관리
- 시험 출제 및 관리
- 개인 맞춤형 문제 생성
- 이전 학습 기록 조회 및 문제 풀이
- 실시간 채점 및 결과 분석
- 다양한 파일 형식 지원 (mp4, mp3, wav, m4a, pdf, txt, docx, hwp)

## 기술 스택

- Frontend: Streamlit
- Backend: FastAPI
- Database: MySQL
- Additional Libraries: Langchain, Transformers, MoviePy, Whisper

## 설치 및 실행 방법

### 사전 요구사항

- MySQL
- Python 3.10
- FFMPEG 코덱 (필요시 설치)

### 설치 단계

1. 저장소를 클론합니다:
   ```
   git clone https://github.com/SkyFever/LLM_Learning_Platform.git
   cd LLM_Learning_Platform
   ```

2. requirements.txt에 명시된 패키지를 설치합니다:
   ```
   pip install -r requirements.txt
   ```

3. 데이터베이스를 구축합니다:
   ```
   python database.py
   ```

### 실행 방법

1. 백엔드 서버를 실행합니다:
   ```
   python backend.py
   ```

2. 프론트엔드 애플리케이션을 실행합니다:
   ```
   streamlit run ui.py
   ```

3. 웹 브라우저에서 `http://localhost:8501`로 접속하여 앱을 사용합니다.

## 프로젝트 구조

- `ui.py`: 애플리케이션 실행 스크립트 (UI 컴포넌트 및 레이아웃)
- `core_logic.py`: 핵심 클라이언트 로직
- `backend.py`: FastAPI 백엔드 서버
- `database.py`: 데이터베이스 연결 및 쿼리 처리
- `text_processing.py`: 텍스트 처리 유틸리티

## 라이선스 및 법적 고지

이 프로젝트는 여러 오픈 소스 라이선스의 적용을 받습니다. 주요 라이선스는 Apache License 2.0입니다. 자세한 라이선스 정보는 LICENSE 파일을 참조하세요.
이 프로젝트에서 사용된 서드파티 라이브러리의 라이선스 정보는 NOTICE 파일에서 확인할 수 있습니다.

## 연락처

프로젝트 관리자 - [ktp4401@gmail.com](mailto:ktp4401@gmail.com)

프로젝트 링크: [https://github.com/SkyFever/LLM_Learning_Platform](https://github.com/SkyFever/LLM_Learning_Platform)
