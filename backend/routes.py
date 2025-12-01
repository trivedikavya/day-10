from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv
import game_engine 
import re
import traceback

load_dotenv()

router = APIRouter()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

def generate_murf_speech(text):
    if not text: return None
    try:
        MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
        url = "https://api.murf.ai/v1/speech/generate"
        headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        clean_text = re.sub(r'[(){}\[\]]', '', text.replace("₹", " Rupees "))
        payload = {"text": clean_text, "voice_id": "en-US-natalie", "style": "Promo"}
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if isinstance(data, dict): return data.get('audioFile')
        return None
    except:
        return None

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Improv Host Active 🎭</h1>")

@router.post("/start-session")
async def start_session():
    initial_state = game_engine.get_initial_state()
    greeting = "Welcome to Improv Battle! I'm your host. What's your name?"
    return JSONResponse(content={
        "text": greeting,
        "audioUrl": generate_murf_speech(greeting),
        "initial_state": initial_state 
    })

@router.post("/chat-with-voice")
async def chat_with_voice(file: UploadFile = File(...), current_state: str = Form(...)):
    try:
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        # 1. State Management
        try:
            state = json.loads(current_state)
            if isinstance(state, list) or "last_search_results" in state:
                state = game_engine.get_initial_state()
        except:
            state = game_engine.get_initial_state()

        # 2. Transcribe
        audio_data = await file.read()
        transcript = aai.Transcriber().transcribe(audio_data)
        user_text = transcript.text or ""
        print(f"🎤 User: {user_text}")

        # 3. Generate Content
        system_prompt = game_engine.get_system_prompt(state, user_text)
        
        # CRITICAL FIX: Handle empty prompt case
        if not system_prompt:
            reply_text = "Whoops, I lost my train of thought. Let's start over."
            state = game_engine.get_initial_state()
        else:
            result = model.generate_content(
                system_prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            ai_response = json.loads(result.text)
            if isinstance(ai_response, list): ai_response = ai_response[0] if ai_response else {}
            
            reply_text = ai_response.get("reply", "Let's continue.")
            
            # Update State
            if "player_name" in ai_response: state["player_name"] = ai_response["player_name"]
            
            # Update History & Rounds
            if state.get("phase") == "playing":
                state["history"].append({"action": user_text, "feedback": reply_text})
                state["round"] = state.get("round", 0) + 1 # Increment round

            state["phase"] = ai_response.get("next_phase", state["phase"])
            state["current_scenario"] = ai_response.get("next_scenario", "")

        print(f"🎭 Host: {reply_text}")

        return {
            "ai_text": reply_text,
            "audio_url": generate_murf_speech(reply_text),
            "updated_state": state
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})