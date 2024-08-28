# text_processing.py
import re
from langchain.text_splitter import TextSplitter

# 문장 구분 패턴 정의
SENT_SEP_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[가-힣])')

class KoreanTextSplitter(TextSplitter):
    """한국어 텍스트를 청크로 나누는 클래스"""
    
    def __init__(self, pdf=False, chunk_size=4000, chunk_overlap=200, **kwargs):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)
        self.pdf = pdf
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text):
        if self.pdf:
            text = self._preprocess_pdf_text(text)
        sent_list = SENT_SEP_PATTERN.split(text)
        return self._create_chunks(sent_list)

    def _preprocess_pdf_text(self, text):
        """PDF 텍스트 전처리"""
        text = re.sub(r"\n{3,}", "\n\n", text)
        return re.sub(r'\s+', ' ', text)

    def _create_chunks(self, sent_list):
        """문장 리스트를 청크로 나누기"""
        chunks = []
        current_chunk = ""
        
        for sent in sent_list:
            if len(current_chunk) + len(sent) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sent
            else:
                current_chunk += " " + sent if current_chunk else sent
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

def separate_questions_and_answers(response, question_types):
    questions = {qt: [] for qt in question_types}
    answers = {qt: [] for qt in question_types}
    
    # 각 문제 유형 블록을 분리
    blocks = re.split(r'\[([A-Z-/ ]+)\]', response)[1:]
    
    for i in range(0, len(blocks), 2):
        q_type = blocks[i].lower().strip().replace(' ', '-').replace('/', '-')
        content = blocks[i+1].strip()
        
        # 질문 유형 매핑
        if q_type == 'multiple-choice':
            q_type = 'multiple-choice'
        elif q_type in ['short-answer', 'short answer']:
            q_type = 'short answer'
        elif q_type in ['true-false', 'true/false']:
            q_type = 'true/false'
        elif q_type == 'fill-in-the-blank':
            q_type = 'fill-in-the-blank'
        
        if q_type in question_types:
            # 각 문제를 분리
            individual_questions = re.split(r'문제\s*\d+\.\s*', content)
            for question in individual_questions[1:]:  # 첫 번째 요소는 빈 문자열일 수 있으므로 건너뜁니다
                parts = re.split(r'정답:\s*', question, maxsplit=1)
                if len(parts) == 2:
                    q, a = parts
                    q = q.strip()
                    a = '정답: ' + a.strip()
                    questions[q_type].append(q)
                    answers[q_type].append(a)
                else:
                    print(f"Warning: Could not separate question and answer in '{q_type}' question.")
        else:
            print(f"Warning: Unknown question type '{q_type}' detected.")
    
    return questions, answers