<![CDATA[# -*- coding: utf-8 -*-
"""
RunPod Serverless Handler - audio processing via ML models.
Performs transcription, diarization, and summary generation.
"""

import json
import logging
import os
import re
import tempfile

import httpx
import runpod
import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RUNPOD_CALLBACK_HEADER = "x-runpod-callback-token"
LLM_MODEL_NAME = "meta-llama/Meta-Llama-3.1-8B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("Using device: %s", DEVICE)


logger.info("Loading Whisper...")
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
whisper_model = WhisperModel(
    "large-v3",
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
    download_root="/models/whisper",
)
logger.info("Whisper loaded")

logger.info("Loading Pyannote...")
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=HF_TOKEN,
    cache_dir="/models/pyannote",
)
diarization_pipeline.to(torch.device(DEVICE))
logger.info("Pyannote loaded")

logger.info("Loading Llama 3.1...")
llm = LLM(
    model=LLM_MODEL_NAME,
    download_dir="/models/llama",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.85,
    max_model_len=8192,
)
tokenizer = AutoTokenizer.from_pretrained(
    LLM_MODEL_NAME,
    cache_dir="/models/llama",
    token=HF_TOKEN,
)
logger.info("Llama 3.1 8B loaded")
logger.info("All models ready")


# NOTE: The system prompt is intentionally in Russian because the application
# processes Russian-language meetings and the LLM must respond in Russian.
# If you need multi-language support, make this configurable via environment variables.
SYSTEM_PROMPT = """Ты — AI-ассистент для анализа бизнес-встреч и звонков.

Твоя задача — структурировать транскрипцию в JSON формате с двумя основными разделами:

1. "discussed" - что обсуждалось на встрече (краткое саммари)
2. "tasks" - конкретные поручения с ответственными и сроками

Каждый раздел содержит 3 блока:
- "commerce" - вопросы ставок, продаж, привлечения клиентов/провайдеров
- "operations" - текущие проблемы, балансировка трафика/ликвидности, оперативные вопросы
- "technical" - интеграции, релизы, L2 поддержка

ВАЖНО:
- Для "discussed": краткие абзацы (2-4 предложения на блок)
- Для "tasks": массив объектов с полями:
  - "task": описание задачи
  - "responsible": кто ответственный (ФИО или должность)
  - "deadline": срок выполнения (если упомянут)
  - "priority": приоритет (high/medium/low) - определи сам исходя из контекста

Если в каком-то блоке ничего не обсуждалось - пиши null.
Если срок не указан - пиши "не указан".
Если ответственный не назван - пиши "не указан".

Формат ответа СТРОГО JSON без дополнительного текста:
{
  "discussed": {
    "commerce": "текст саммари или null",
    "operations": "текст саммари или null",
    "technical": "текст саммари или null"
  },
  "tasks": {
    "commerce": [
      {
        "task": "описание",
        "responsible": "ФИО",
        "deadline": "дата",
        "priority": "high"
      }
    ],
    "operations": [],
    "technical": []
  }
}
"""


def align_speakers_with_words(diarization, words):
    """Aligns words with speakers from diarization output."""
    dialogue = []

    for word in words:
        word_start = word["start"]
        word_end = word["end"]
        word_mid = (word_start + word_end) / 2

        speaker_found = None
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if turn.start <= word_mid <= turn.end:
                speaker_found = speaker
                break

        dialogue.append(
            {
                "speaker": speaker_found or "UNKNOWN",
                "text": word["text"],
                "start": word_start,
                "end": word_end,
            }
        )

    return dialogue


def format_dialogue_for_llm(dialogue):
    """Formats dialogue for LLM input."""
    if not dialogue:
        return ""

    grouped = []
    current_speaker = None
    current_text = []
    current_start = None

    for item in dialogue:
        if item["speaker"] != current_speaker:
            if current_speaker is not None:
                grouped.append(
                    {
                        "speaker": current_speaker,
                        "text": " ".join(current_text),
                        "start": current_start,
                    }
                )
            current_speaker = item["speaker"]
            current_text = [item["text"]]
            current_start = item["start"]
        else:
            current_text.append(item["text"])

    if current_speaker is not None:
        grouped.append(
            {
                "speaker": current_speaker,
                "text": " ".join(current_text),
                "start": current_start,
            }
        )

    lines = []
    for item in grouped:
        minutes = int(item["start"] // 60)
        seconds = int(item["start"] % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        lines.append(f"[{item['speaker']}, {timestamp}]: {item['text']}")

    return "\n\n".join(lines)


def build_summary_prompt(dialogue_text: str) -> str:
    # NOTE: User message is in Russian to match the system prompt language.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Транскрипция встречи:\n\n{dialogue_text}\n\nВерни только JSON.",
        },
    ]

    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception as exc:
        logger.warning("Failed to apply chat template, using fallback prompt: %s", exc)
        return f"{SYSTEM_PROMPT}\n\nТранскрипция встречи:\n\n{dialogue_text}\n\nJSON:"


def build_callback_headers(callback_token: str | None) -> dict:
    headers = {}
    if callback_token:
        headers[RUNPOD_CALLBACK_HEADER] = callback_token
    return headers


def send_progress_update(
    callback_url: str,
    callback_token: str,
    job_id: str,
    chat_id: str,
    progress: int,
    message: str,
):
    """Sends an intermediate progress update to the callback URL."""
    if not callback_url or not chat_id:
        return

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                callback_url,
                json={
                    "job_id": job_id,
                    "chat_id": chat_id,
                    "status": "PROGRESS",
                    "progress": progress,
                    "message": message,
                },
                headers=build_callback_headers(callback_token),
            )
        logger.info("Progress update sent: %s%% - %s", progress, message)
    except Exception as exc:
        logger.warning("Failed to send progress update: %s", exc)


def handler(job):
    """
    Main job handler function.
    Called by RunPod serverless when a task is received.
    """
    job_input = job["input"]

    if job_input.get("test"):
        return {
            "status": "ok",
            "device": DEVICE,
            "cuda_available": torch.cuda.is_available(),
        }

    job_id = job_input["job_id"]
    chat_id = job_input.get("chat_id")
    callback_url = job_input.get("callback_url")
    callback_token = job_input.get("callback_token")

    audio_download_url = job_input.get("audio_download_url")
    result_upload_url = job_input.get("result_upload_url")
    result_key = job_input.get("result_key")

    logger.info("Starting job processing: %s", job_id)

    audio_path = None

    try:
        send_progress_update(
            callback_url,
            callback_token,
            job_id,
            chat_id,
            10,
            "📥 Downloading audio...",
        )

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_audio:
            audio_path = tmp_audio.name

        if not audio_download_url:
            raise ValueError(
                "audio_download_url is missing. Legacy AWS credentials are no longer supported in RunPod."
            )

        logger.info("Downloading audio via presigned URL...")
        with httpx.Client(timeout=300.0) as client:
            response = client.get(audio_download_url)
            response.raise_for_status()
            with open(audio_path, "wb") as file_handle:
                file_handle.write(response.content)
        logger.info("Audio downloaded via presigned URL")

        send_progress_update(
            callback_url,
            callback_token,
            job_id,
            chat_id,
            20,
            "🎙 Transcribing speech...",
        )
        logger.info("Step 1/3: Transcription...")

        segments, info = whisper_model.transcribe(
            audio_path,
            language="ru",
            word_timestamps=True,
        )

        all_words = []
        for seg in segments:
            if hasattr(seg, "words") and seg.words:
                for word in seg.words:
                    all_words.append(
                        {
                            "text": word.word,
                            "start": word.start,
                            "end": word.end,
                        }
                    )

        logger.info("Transcribed %s words", len(all_words))

        send_progress_update(
            callback_url,
            callback_token,
            job_id,
            chat_id,
            50,
            "👥 Identifying speakers...",
        )
        logger.info("Step 2/3: Speaker identification...")

        diarization = diarization_pipeline(audio_path)

        speakers = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.add(speaker)

        logger.info("Speakers found: %s", len(speakers))
        logger.info("Step 2.5/3: Aligning speakers with words...")

        dialogue = align_speakers_with_words(diarization, all_words)
        dialogue_text = format_dialogue_for_llm(dialogue)

        logger.info("Dialogue formed, length: %s characters", len(dialogue_text))

        send_progress_update(
            callback_url,
            callback_token,
            job_id,
            chat_id,
            70,
            "🤖 Generating summary...",
        )
        logger.info("Step 3/3: Summary generation...")

        summary = None
        llm_error = None

        try:
            prompt = build_summary_prompt(dialogue_text)
            sampling_params = SamplingParams(
                temperature=0.3,
                top_p=0.9,
                max_tokens=3000,
            )

            outputs = llm.generate([prompt], sampling_params)
            summary_text = outputs[0].outputs[0].text

            try:
                json_match = re.search(r"\{.*\}", summary_text, re.DOTALL)
                if json_match:
                    summary = json.loads(json_match.group())
                    logger.info("Summary created successfully")
                else:
                    summary = json.loads(summary_text)
                    logger.info("Summary created via fallback parsing")
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse JSON from LLM: %s", exc)
                logger.debug("LLM response: %s", summary_text[:500])
                llm_error = f"JSON parsing failed: {exc}"
                summary = None
        except Exception as exc:
            logger.error("LLM summary generation error: %s", exc, exc_info=True)
            llm_error = f"LLM generation failed: {exc}"
            summary = None

        result = {
            "job_id": job_id,
            "status": "completed",
            "full_transcript": dialogue_text,
            "discussed": summary.get("discussed") if summary else None,
            "tasks": summary.get("tasks") if summary else None,
            "metadata": {
                "duration": info.duration if hasattr(info, "duration") else None,
                "language": info.language if hasattr(info, "language") else "ru",
                "num_speakers": len(speakers),
                "num_words": len(all_words),
                "llm_error": llm_error,
            },
        }

        if llm_error:
            result["warning"] = "Summary generation failed, but transcript is available"
            logger.warning("Job %s completed with warning: LLM failed", job_id)

        if not result_upload_url or not result_key:
            raise ValueError(
                "result_upload_url is missing. Legacy AWS credentials are no longer supported in RunPod."
            )

        logger.info("Uploading result via presigned URL...")
        with httpx.Client(timeout=60.0) as client:
            response = client.put(
                result_upload_url,
                data=json.dumps(result).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        logger.info("Result uploaded via presigned URL")

        if callback_url and chat_id:
            try:
                logger.info("Sending callback to %s", callback_url)
                with httpx.Client(timeout=30.0) as client:
                    callback_response = client.post(
                        callback_url,
                        json={
                            "job_id": job_id,
                            "chat_id": chat_id,
                            "status": "COMPLETED",
                            "result": result,
                        },
                        headers=build_callback_headers(callback_token),
                    )
                    if callback_response.status_code == 200:
                        logger.info("Callback sent successfully for job %s", job_id)
                    else:
                        logger.warning("Callback failed: %s", callback_response.status_code)
            except Exception as callback_error:
                logger.error("Error sending callback: %s", callback_error)

        logger.info("Job %s completed successfully", job_id)
        return {
            "status": "success",
            "job_id": job_id,
            "result_key": result_key,
            "metadata": result["metadata"],
        }
    except Exception as exc:
        logger.error("Error processing job %s: %s", job_id, exc, exc_info=True)

        error_result = {
            "job_id": job_id,
            "status": "failed",
            "error": str(exc),
        }

        if result_upload_url:
            try:
                with httpx.Client(timeout=60.0) as client:
                    client.put(
                        result_upload_url,
                        data=json.dumps(error_result).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
            except Exception as upload_error:
                logger.error("Error uploading error result: %s", upload_error)

        if callback_url and chat_id:
            try:
                logger.info("Sending error callback to %s", callback_url)
                with httpx.Client(timeout=30.0) as client:
                    client.post(
                        callback_url,
                        json={
                            "job_id": job_id,
                            "chat_id": chat_id,
                            "status": "FAILED",
                            "error": str(exc),
                        },
                        headers=build_callback_headers(callback_token),
                    )
            except Exception as callback_error:
                logger.error("Error sending error callback: %s", callback_error)

        return {
            "status": "error",
            "job_id": job_id,
            "error": str(exc),
        }
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError as cleanup_error:
                logger.warning("Failed to delete temporary file %s: %s", audio_path, cleanup_error)


runpod_handler = handler


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
]]>
