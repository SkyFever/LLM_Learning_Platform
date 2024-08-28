from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse
import torch
import os
from pydantic import BaseModel
from moviepy.editor import VideoFileClip
from tempfile import NamedTemporaryFile
import whisper
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import aiofiles
import asyncio

# FastAPI 인스턴스 생성
app = FastAPI()

# 디바이스 설정
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Whisper 모델 로드
print("Whisper 모델 로딩 중...")
whisper_model = whisper.load_model("small").to(device)
print("Whisper 모델 로딩 완료")

# GPT 모델과 토크나이저 초기화
model, tokenizer = None, None
model_id = "Qwen/Qwen2-7B-Instruct"
#model_id = "Qwen/Qwen2-57B-A14B-Instruct"

def load_gpt_model_and_tokenizer():
    global model, tokenizer
    if model is None or tokenizer is None:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,  # 4bit 양자화 활성화
            llm_int8_enable_fp32_cpu_offload=False,  # CPU 오프로딩 비활성화 (GPU만 사용)
            bnb_4bit_compute_dtype=torch.bfloat16,  # 4080 GPU에서 bfloat16을 사용하여 계산 최적화
            bnb_4bit_quant_type="nf4",  # NF4 양자화 유형 사용 (FP4보다 높은 정확도와 안정성)
            llm_int8_has_fp16_weight=True  # LLM.int8()과 함께 16-bit 가중치 사용 (백워드 패스 최적화)
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            torch_dtype="bfloat16",
            device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id)
    return model, tokenizer

model, tokenizer = load_gpt_model_and_tokenizer()

async def extract_audio_from_mp4(mp4_file_path, output_audio_path="extracted_audio.wav"):
    """MP4 파일에서 오디오를 추출하여 WAV 파일로 저장"""
    loop = asyncio.get_event_loop()
    video = await loop.run_in_executor(None, VideoFileClip, mp4_file_path)
    audio = video.audio
    await loop.run_in_executor(None, audio.write_audiofile, output_audio_path, codec='pcm_s16le')
    return output_audio_path

async def transcribe_audio_file(audio_file_path):
    """WAV, M4A, MP3 등 파일을 텍스트로 변환"""
    loop = asyncio.get_event_loop()
    audio = await loop.run_in_executor(None, whisper.load_audio, audio_file_path)
    result = await loop.run_in_executor(None, whisper_model.transcribe, audio, False)
    return result['text']

@app.post("/transcribe_video/")
async def transcribe_video(file: UploadFile = File(...)):
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_mp4:
            content = await file.read()
            await temp_mp4.write(content)
            temp_mp4_path = temp_mp4.name

        # 오디오 추출
        temp_audio_path = "extracted_audio.wav"
        audio_file_path = await extract_audio_from_mp4(temp_mp4_path, temp_audio_path)

        # 오디오 파일을 텍스트로 변환
        transcription = await transcribe_audio_file(audio_file_path)

        # 임시 파일 삭제
        os.remove(temp_mp4_path)
        os.remove(temp_audio_path)

        # 플레인 텍스트로 반환
        return PlainTextResponse(content=transcription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe_audio/")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            await temp_audio.write(content)
            temp_audio_path = temp_audio.name

        # 오디오 파일을 텍스트로 변환
        transcription = await transcribe_audio_file(temp_audio_path)

        # 임시 파일 삭제
        os.remove(temp_audio_path)

        # 플레인 텍스트로 반환
        return PlainTextResponse(content=transcription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PromptRequest(BaseModel):
    prompt: str
    context: str

@app.post("/generate")
async def generate_response(request: PromptRequest):
    try:
        messages = [
            {"role": "system", "content": request.prompt},
            {"role": "user", "content": request.context}
        ]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True).to(device)
        generated_ids = model.generate(
            model_inputs.input_ids,
            max_new_tokens=16384,
            top_k=50,
            top_p=0.7,
            temperature=0.3
        )
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# FastAPI 서버를 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
