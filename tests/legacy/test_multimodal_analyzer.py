import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from core.voice.video_audio_loader import MultiModalAnalyzer, AudioMetrics

@pytest.mark.async_io
async def test_multimodal_process_flow_url():
    """Test full flow with URL input (mocked)"""
    analyzer = MultiModalAnalyzer()
    
    mock_gemini_response = {
        "transcript": "Hello world. This is a fast speaker testing the wpm calculation.",
        "word_timestamps": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.6, "end": 1.0},
            {"word": "This", "start": 1.2, "end": 1.5},
            {"word": "is", "start": 1.5, "end": 1.7},
            {"word": "a", "start": 1.7, "end": 1.8},
            {"word": "fast", "start": 1.8, "end": 2.1},
            {"word": "speaker", "start": 2.1, "end": 2.6},
            {"word": "testing", "start": 2.7, "end": 3.2},
            {"word": "the", "start": 3.2, "end": 3.3},
            {"word": "wpm", "start": 3.3, "end": 3.6},
            {"word": "calculation", "start": 3.6, "end": 4.5}
        ]
    }
    
    # Mock dependencies
    with patch("adapters.external.gemini_client.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = mock_gemini_response
        
        with patch("subprocess.run") as mock_subprocess:
            # Mock success for yt-dlp and ffmpeg and ffprobe
            mock_subprocess.return_value.stdout = b"Done" 
            # ffprobe duration mock (though metrics uses timestamps as fallback, let's mock validation too)
            # wait, validation uses ffprobe. metrics uses timestamps if avail.
            
            # Use side_effect to distinguish calls if needed, or just return success
            # We need to mock _download_youtube to return a path
            with patch.object(analyzer, "_download_youtube", return_value=Path("mock.wav")):
                 with patch.object(analyzer, "_normalize_audio", return_value=Path("mock_norm.wav")):
                      with patch.object(analyzer, "_validate_media"): # Skip validation logic
                           
                           result = await analyzer.process("url", "http://youtube.com/test")
                           
                           assert result["transcript"] == mock_gemini_response["transcript"]
                           assert "audio_profile" in result
                           metrics = result["audio_profile"]["metrics"]
                           rules = result["audio_profile"]["cadence_rules"]
                           
                           # 11 words / 4.5s (0.075 min) ~= 146 WPM
                           assert metrics["wpm"] > 100 
                           assert rules["sentence_length_preference"] == "Maintain standard conversational sentence length."

@pytest.mark.async_io
async def test_cadence_rules_fast_speaker():
    """Test rule derivation logic"""
    analyzer = MultiModalAnalyzer()
    
    # Fast speaker wpm > 160
    metrics = AudioMetrics(
        wpm=170.0,
        pause_density=0.2, # low
        avg_sentence_length=10.0, # short
        filler_rate=0.0, # confident
        duration_minutes=1.0
    )
    
    rules = analyzer._derive_cadence_rules(metrics)
    
    assert "short, punchy sentences" in rules.sentence_length_rule
    assert "confident tone" in rules.tone_rule

@pytest.mark.async_io
async def test_cadence_rules_hesitant_speaker():
    """Test rule derivation logic"""
    analyzer = MultiModalAnalyzer()
    
    # Hesitant, high filler
    metrics = AudioMetrics(
        wpm=120.0,
        pause_density=1.5, # High pause
        avg_sentence_length=15.0,
        filler_rate=0.06, # High filler
        duration_minutes=1.0
    )
    
    rules = analyzer._derive_cadence_rules(metrics)
    
    assert "strong paragraph breaks" in rules.paragraph_break_rule
    assert "casual" in rules.tone_rule
