import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

import spacy
from pydantic import BaseModel

# Assume this client exists as per instructions
from adapters.external import gemini_client 

# Initialize static-ffmpeg to ensure ffmpeg/ffprobe are in PATH for yt-dlp and subprocess
try:
    from static_ffmpeg import add_paths
    add_paths()
    logger = logging.getLogger(__name__)
    logger.info("static-ffmpeg initialized: ffmpeg/ffprobe added to PATH")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("static-ffmpeg not found. Ensure ffmpeg is installed in system PATH.")

# Load SpaCy small model for efficiency
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Fallback or strict requirement
    logger.warning("SpaCy model 'en_core_web_sm' not found, downloading...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class AudioMetrics(BaseModel):
    wpm: float
    pause_density: float
    avg_sentence_length: float
    filler_rate: float
    duration_minutes: float

class CadenceRules(BaseModel):
    sentence_length_rule: str
    paragraph_break_rule: str
    conciseness_rule: str
    tone_rule: str

class MultiModalAnalyzer:
    """
    Orchestrates the Multi-Modal Ingestion Workflow (Video/Audio).
    1. Download/Extract Audio
    2. Transcribe via Gemini
    3. Compute Metrics
    4. Derive Cadence Rules
    5. Cleanup
    """

    def __init__(self):
        self.supported_extensions = {".mp3", ".wav", ".mp4", ".mov", ".m4a"}
        self.filler_words = {"um", "uh", "like", "you know", "sort of", "kind of", "mean", "right"}

    async def process(self, input_type: str, input_value: str) -> Dict[str, Any]:
        """
        Main entry point for processing audio/video content.
        
        Args:
            input_type: 'url' (YouTube) or 'file' (local path)
            input_value: URL or file path/bytes
            
        Returns:
            Dict containing transcript, audio_profile (metrics + rules), and metadata.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Acquire Media
            if input_type == "url":
                raw_audio_path = self._download_youtube(input_value, temp_dir)
            else:
                 # Assume input_value is a local path for the 'file' case in this context
                raw_audio_path = Path(input_value)

            # Validate extraction
            if not raw_audio_path or not raw_audio_path.exists():
                raise ValueError("Failed to acquire valid media file.")

            # 2. Normalize Audio (16kHz mono WAV for API stability)
            normalized_audio = self._normalize_audio(raw_audio_path, temp_dir)

            # 3. Validation (Duration/Size)
            self._validate_media(normalized_audio)

            # 4. Transcribe (Gemini)
            transcription_data = await self._transcribe(normalized_audio)
            transcript_text = transcription_data.get("transcript", "")
            timestamps = transcription_data.get("word_timestamps", [])

            if not transcript_text:
                raise ValueError("Transcription failed or produced empty output.")

            # 5. Compute Metrics
            metrics = self._compute_metrics(transcript_text, timestamps, normalized_audio)

            # 6. Derive Cadence Rules
            rules = self._derive_cadence_rules(metrics)

            return {
                "transcript": transcript_text,
                "audio_profile": {
                    "metrics": metrics.dict(),
                    "cadence_rules": rules.dict()
                },
                "metadata": {
                    "source": input_value,
                    "type": input_type,
                    "duration_min": metrics.duration_minutes
                }
            }

        except Exception as e:
            logger.error(f"MultiModal processing error: {str(e)}")
            raise e
        finally:
            # Cleanup
            self._cleanup(temp_dir)

    def _download_youtube(self, url: str, output_dir: str) -> Path:
        """Downloads YouTube audio using yt-dlp."""
        output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-x", # Extract audio
            "--audio-format", "wav",
            "--no-playlist",      # Ensure we don't download a whole playlist
            "--force-ipv4",       # Stability fix for some networks
            "--no-check-certificate", # aggressive fix for some SSL issues
            "-o", output_template,
            url
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Find the downloaded file
            for f in os.listdir(output_dir):
                if f.endswith(".wav"):
                    return Path(output_dir) / f
            raise ValueError("yt-dlp execution finished but no WAV file found.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"yt-dlp failed: {e.stderr.decode()}")

    def _normalize_audio(self, input_path: Path, output_dir: str) -> Path:
        """Converts to 16kHz Mono WAV using ffmpeg."""
        output_path = Path(output_dir) / "normalized.wav"
        
        cmd = [
            "ffmpeg",
            "-y", # Overwrite
            "-i", str(input_path),
            "-ar", "16000", # 16kHz
            "-ac", "1", # Mono
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return output_path
        except subprocess.CalledProcessError as e:
            # Check if input path exists
            if not input_path.exists():
                raise RuntimeError(f"ffmpeg input file not found: {input_path}")
            raise RuntimeError(f"ffmpeg normalization failed: {e.stderr.decode()}")

    def _validate_media(self, file_path: Path):
        """Rejects media > 60 mins or > 500MB."""
        # Check size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > 500:
            raise ValueError(f"File too large: {size_mb:.2f}MB (Max 500MB)")

        # Check duration using ffmpeg/ffprobe logic or reliable estimation
        # We can also check duration AFTER metrics computation if strictly needed, 
        # but better to fail fast. Using ffprobe here.
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(file_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration_sec = float(result.stdout.strip())
            if duration_sec > 3600: # 60 mins
                raise ValueError(f"Duration too long: {duration_sec/60:.2f} mins (Max 60 mins)")
        except Exception:
            # If ffprobe fails, proceed (metrics step has fallback duration calc)
            logger.warning("Could not validate duration via ffprobe, skipping check.")

    async def _transcribe(self, file_path: Path) -> Dict[str, Any]:
        """Calls Gemini Speech API."""
        try:
            return await gemini_client.transcribe_audio(str(file_path))
        except Exception as e:
            raise RuntimeError(f"Gemini Transcription failed: {str(e)}")

    def _compute_metrics(self, transcript: str, timestamps: List[Dict], audio_path: Path) -> AudioMetrics:
        """Computes WPM, Pause Density, Filler Rate, etc."""
        
        # 1. Text Analysis (SpaCy)
        try:
            doc = nlp(transcript)
        except NameError:
             # Fallback if nlp load failed
             import spacy
             try:
                nlp_local = spacy.load("en_core_web_sm")
                doc = nlp_local(transcript)
             except:
                # Mock split if spacy fails entirely
                class MockDoc:
                    sents = [s for s in transcript.split('. ')]
                    def __str__(self): return transcript
                doc = MockDoc()

        sentences = list(doc.sents)
        num_sentences = len(sentences)
        num_words = len(str(doc).split()) # Simple split for raw count
        
        avg_sent_len = (sum(len(str(sent).split()) for sent in sentences) / num_sentences) if num_sentences > 0 else 0

        # 2. Filler Rate
        # Normalize text for filler search
        text_lower = transcript.lower()
        filler_count = 0
        for filler in self.filler_words:
            # Simple count - can be improved with regex
            filler_count += text_lower.count(filler)
        
        filler_rate = filler_count / num_words if num_words > 0 else 0.0

        # 3. Time Analysis (from timestamps)
        if not timestamps:
            # Fallback if no timestamps
            return AudioMetrics(
                wpm=0, pause_density=0, 
                avg_sentence_length=avg_sent_len, 
                filler_rate=filler_rate,
                duration_minutes=0
            )

        start_time = timestamps[0]['start']
        end_time = timestamps[-1]['end']
        duration_min = (end_time - start_time) / 60
        
        wpm = num_words / duration_min if duration_min > 0 else 0

        # 4. Pause Density (> 600ms)
        long_pauses = 0
        for i in range(len(timestamps) - 1):
            gap = timestamps[i+1]['start'] - timestamps[i]['end']
            if gap > 0.6:
                long_pauses += 1
        
        # Pause density = pauses per minute
        pause_density = long_pauses / duration_min if duration_min > 0 else 0

        return AudioMetrics(
            wpm=round(wpm, 1),
            pause_density=round(pause_density, 2),
            avg_sentence_length=round(avg_sent_len, 1),
            filler_rate=round(filler_rate, 3),
            duration_minutes=round(duration_min, 2)
        )

    def _derive_cadence_rules(self, metrics: AudioMetrics) -> CadenceRules:
        """Map metrics to writing constraints."""
        
        # WPM Rule
        if metrics.wpm > 160:
            sent_len_rule = "Use short, punchy sentences to match fast delivery."
        elif metrics.wpm < 110:
            sent_len_rule = "Use longer, contemplative sentences for slow delivery."
        else:
            sent_len_rule = "Maintain standard conversational sentence length."

        # Pause Density Rule
        if metrics.pause_density > 0.8:
            para_rule = "Use strong paragraph breaks to reflect frequent pauses."
        else:
            para_rule = "Group ideas into larger, flowing paragraphs."

        # Avg Sentence Length Logic (Syntactic Complexity)
        if metrics.avg_sentence_length < 14:
            concise_rule = "Keep syntax simple and concise."
        else:
            concise_rule = "Allow for complex, multi-clause sentence structures."

        # Filler Logic (Confidence)
        if metrics.filler_rate < 0.01:
            tone_rule = "Use a decisive, confident tone (minimal hedging)."
        elif metrics.filler_rate > 0.05:
            tone_rule = "Adopt a casual, extemporaneous tone (allow softeners)."
        else:
            tone_rule = "Balance professional clarity with natural conversational flow."

        return CadenceRules(
            sentence_length_rule=sent_len_rule,
            paragraph_break_rule=para_rule,
            conciseness_rule=concise_rule,
            tone_rule=tone_rule
        )

    def _cleanup(self, dir_path: str):
        try:
            import shutil
            shutil.rmtree(dir_path)
            # Log cleanup success
        except Exception:
            pass