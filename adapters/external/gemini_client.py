import os
import logging
import json
import asyncio
from functools import partial
from typing import Dict, Any

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

async def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """
    Transcribes audio using LangChain's ChatGoogleGenerativeAI (Gemini 1.5 Flash).
    
    Args:
        file_path: Absolute path to the audio file.
        
    Returns:
        Dict with keys: transcript, word_timestamps
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")

    # Explicitly configure genai for the file upload part
    genai.configure(api_key=api_key)

    try:
        # 1. Upload File (Blocking IO -> Run in Thread)
        # We still use the native SDK for upload as LangChain doesn't replace the File API management fully.
        logger.info(f"Uploading file to Gemini: {file_path}")
        
        loop = asyncio.get_running_loop()
        audio_file = await loop.run_in_executor(
            None, 
            partial(genai.upload_file, path=file_path)
        )
        logger.info(f"File uploaded: {audio_file.uri}")

        # 2. Initialize LangChain Model
        # Matching Agent usage pattern
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            google_api_key=api_key
        )

        # 3. Construct Message
        # We pass the file_uri which ChatGoogleGenerativeAI understands (via proper content block construction)
        prompt_text = """
        Transcribe the audio accurately.
        
        REQUIRED OUTPUT FORMAT (JSON):
        {
            "transcript": "Full text here...",
            "word_timestamps": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                ...
            ]
        }
        
        If precise word alignment is not possible, provide the best estimate or sentence-level timestamps.
        Ensure it is valid JSON.
        """

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "media", 
                    "file_uri": audio_file.uri, 
                    "mime_type": audio_file.mime_type
                }
            ]
        )

        # 4. Invoke LLM
        # Note: ChatGoogleGenerativeAI invocation returns a BaseMessage
        response = await llm.ainvoke([message])
        content = response.content

        # 5. Parse Response
        try:
            # Clean potential markdown code blocks ```json ... ```
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned_content)
            logger.info("Gemini transcription successful")
            return result
        except json.JSONDecodeError as je:
            logger.warning(f"Failed to parse JSON from Gemini: {je}. Returning raw text.")
            return {
                "transcript": content,
                "word_timestamps": [] 
            }

    except Exception as e:
        logger.error(f"Gemini Transcription Failed: {str(e)}")
        raise RuntimeError(f"Gemini API Error: {str(e)}")
