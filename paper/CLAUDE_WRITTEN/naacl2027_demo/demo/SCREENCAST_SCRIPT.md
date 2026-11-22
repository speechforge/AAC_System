# Screencast script (limit 2:30)

**Recorded so far:** `screencast/screencast_silent_captioned.mp4` (2:03, 1280x720, ten frames per second, burned-in captions, **no audio**). It was recorded by `record_screencast.py` from the live build; the captions are generated from the real `/generate` responses, so they describe what happened in that run. `screencast/captions.srt` carries the same captions as a separate file.

**Pending (mandatory for submission):** an audible take. IndicF5 weights are gated and were unavailable, so the build returns a placeholder tone. Record on a machine with the weights (see `README_DEMO.md`), either with the same script after enabling audio capture, or with a screen recorder (for example `ffmpeg -f x11grab -video_size 1280x720 -i :0.0 -f pulse -i default out.mp4`).

## Timed narration (English; about 135 words per minute)
| Time | On screen | Narration |
|---|---|---|
| 0:00-0:12 | Board, English | "Indic AAC Studio is a symbol board for English, Hindi, Gujarati and Marathi. A person taps symbols; a language model expands the selection; a validator checks it before it is spoken." |
| 0:12-0:45 | Food > Water > AI Polish & Speak | "I select Water. The model proposes a fluent sentence about food, not water. The validator rejects it because the selected concept is missing, and a template built from my own label returns 'I want Water.' The card does not show this, which is a limitation." *(play the audio here)* |
| 0:45-1:20 | Gujarati: No + Water | "In Gujarati I select No and Water. The sentence keeps the negation and is accepted. The suggestion shelf shows English words because Gujarati has no predictor." *(play the audio here)* |
| 1:20-1:55 | English: Tired | "For a feeling the client sends a request intent, and the gate only checks concepts. The sentence is fluent but adds content I did not choose. We report this as a defect." |
| 1:55-2:25 | Summary captions | "On 175 frozen scenarios the gate raises success from 37 to 55 percent and keeps every selected concept; explicit polarity and intent fields give 75 percent. A template alone reaches 95 percent, so the gate is a safeguard, not a quality gain. Code, fixtures and scorer accompany the submission." |

## Capture steps for the audible take
1. Start the backend with IndicF5 weights present; confirm `GET /api/voice/list` shows `engine_ready: true`.
2. Open `http://localhost:8000` signed out in a clean browser profile; set the window to 1280x720.
3. Run the four segments above in order; wait for the output card before narrating each result; trim to 2:30.
4. Export H.264/AAC MP4 and attach it to the OpenReview submission with `captions.srt` if captions are not burned in.
