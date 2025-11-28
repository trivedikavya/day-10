from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# 1. CONFIGURE GEMINI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# 2. HELPER: MURF VOICE (Storyteller)
def generate_murf_speech(text):
    MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
    # 'en-US-marcus' has a good "Movie Trailer" / "Narrator" vibe
    voice_id = "en-US-marcus" 
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "voice_id": voice_id,
        "style": "Promo", # Adds dramatic flair
        "multiNativeLocale": "en-US"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if response.status_code != 200:
             # Fallback
             payload["voice_id"] = "en-UK-ruby"
             retry = requests.post(url, headers=headers, data=json.dumps(payload))
             return retry.json().get('audioFile')
        return data.get('audioFile')
    except:
        return None

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Game Master Active 🎲</h1>", status_code=200)

@router.post("/start-session")
async def start_session():
    # The Opening Scene
    intro_text = "System Online. Welcome to Neon City, 2099. You wake up in a rainy alleyway behind a noodle shop. Your head hurts, and you are clutching a mysterious data chip. A security drone is scanning the area nearby. What do you do?"
    
    return JSONResponse(content={
        "text": intro_text,
        "audioUrl": generate_murf_speech(intro_text)
    })

# --- MAIN GAME LOOP ---
@router.post("/chat-with-voice")
async def chat_with_voice(
    file: UploadFile = File(...), 
    current_state: str = Form(...)
):
    try:
        # A. SETUP
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        try:
            # We expect state to contain the conversation history
            state = json.loads(current_state)
            history = state.get("history", [])
        except:
            history = []

        # B. TRANSCRIBE PLAYER ACTION
        audio_data = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        user_action = transcript.text or ""
        print(f"🗡️ Player: {user_action}")

        if not user_action:
             return JSONResponse(content={"error": "Silence detected"}, status_code=400)

        # C. GAME MASTER BRAIN (Gemini)
        # We construct the prompt using the history to ensure continuity
        
        system_prompt = f"""
        You are the Game Master (GM) for a gritty Cyberpunk RPG adventure set in 'Neon City'.
        
        TONE: Noir, high-tech, dangerous, atmospheric.
        ROLE: Describe the outcome of the player's actions vividly. Keep descriptions concise (2-3 sentences) for voice.
        ALWAYS END WITH: "What do you do?"
        
        HISTORY OF THIS SESSION:
        {json.dumps(history)}
        
        PLAYER JUST SAID: "{user_action}"
        
        INSTRUCTIONS:
        1. If the player's action is impossible, tell them why.
        2. If they succeed/fail, describe the consequence.
        3. Introduce characters or threats dynamically.
        4. Move the plot forward (Mini-arc: Escaping the drone -> Finding a contact -> Decrypting the chip).
        
        Respond with the GM's narration text only.
        """

        result = model.generate_content(system_prompt)
        gm_reply = result.text
        
        print(f"🎲 GM: {gm_reply}")

        # D. UPDATE HISTORY
        # Append this turn to the history list
        new_history_entry = [
            {"role": "user", "content": user_action},
            {"role": "model", "content": gm_reply}
        ]
        updated_history = history + new_history_entry

        # E. AUDIO GENERATION
        audio_url = generate_murf_speech(gm_reply)

        return {
            "user_transcript": user_action,
            "ai_text": gm_reply,
            "audio_url": audio_url,
            "updated_state": {
                "history": updated_history
            }
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})