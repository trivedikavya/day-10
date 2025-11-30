from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv
import random
import re

load_dotenv()

router = APIRouter()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# LOAD SCENARIOS
try:
    with open("improv_scenarios.json", "r") as f:
        SCENARIOS = json.load(f)
except:
    SCENARIOS = [{"id": 999, "scenario": "You are a robot trying to explain love."}]

# HELPER: MURF VOICE
def generate_murf_speech(text):
    MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
    voice_id = "en-US-marcus" 
    
    spoken_text = text.replace("-", " ")
    spoken_text = re.sub(r'[(){}\[\]]', '', spoken_text)
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": spoken_text,
        "voice_id": voice_id,
        "style": "Promo",
        "multiNativeLocale": "en-US"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if response.status_code != 200:
             payload["voice_id"] = "en-UK-ruby"
             retry = requests.post(url, headers=headers, data=json.dumps(payload))
             return retry.json().get('audioFile')
        return data.get('audioFile')
    except:
        return None

# HELPER: ROBUST JSON PARSER
def clean_and_parse_json(text):
    try:
        # Try direct parse
        return json.loads(text)
    except:
        # Try to find JSON block if LLM added markdown like ```json ... ```
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except:
            pass
            
        # Fallback if parsing fails completely
        print(f"⚠️ JSON Parse Failed. Raw text: {text}")
        return {
            "host_reaction": "Wow! That was... something! Moving on!",
            "next_action": "next_round",
            "next_scenario_id": None
        }

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Improv Battle Host Active 🎤</h1>", status_code=200)

@router.post("/start-session")
async def start_session(request: dict):
    player_name = request.get("player_name", "Contestant")
    
    first_scenario_obj = random.choice(SCENARIOS)
    
    initial_state = {
        "player_name": player_name,
        "current_round": 1,
        "max_rounds": 3,
        "phase": "awaiting_improv",
        "current_scenario": first_scenario_obj['scenario'],
        "used_scenario_ids": [first_scenario_obj['id']]
    }
    
    greeting = f"Welcome to IMPROV BATTLE! I'm Marcus. {player_name}, get ready! Round 1: {initial_state['current_scenario']} ... ACTION!"
    
    audio_url = generate_murf_speech(greeting)
    
    return JSONResponse(content={
        "text": greeting,
        "audioUrl": audio_url,
        "game_state": initial_state
    })

@router.post("/chat-with-voice")
async def chat_with_voice(
    file: UploadFile = File(...), 
    current_state: str = Form(...)
):
    try:
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        try:
            state = json.loads(current_state) 
        except:
            state = {}

        audio_data = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        user_text = transcript.text or ""
        print(f"🎭 Performer: {user_text}")

        if "stop" in user_text.lower() or "end" in user_text.lower():
             goodbye = "Thanks for playing Improv Battle! Goodnight!"
             return {
                 "user_transcript": user_text,
                 "ai_text": goodbye,
                 "audio_url": generate_murf_speech(goodbye),
                 "updated_state": {**state, "phase": "done"}
             }

        # Filter Scenarios
        used_ids = state.get("used_scenario_ids", [])
        available_scenarios = [s for s in SCENARIOS if s['id'] not in used_ids]
        if not available_scenarios: available_scenarios = SCENARIOS

        system_prompt = f"""
        You are the host of 'Improv Battle'.
        
        Round: {state.get('current_round')} / {state.get('max_rounds')}
        Scenario: "{state.get('current_scenario')}"
        User Performance: "{user_text}"
        
        Task:
        1. React specifically to their performance (be witty).
        2. Decide next step (next_round OR end_game).
        3. Pick ONE scenario ID from this list for the next round:
        {json.dumps(available_scenarios)}
        
        Return ONLY valid JSON. No markdown.
        {{
            "host_reaction": "reaction text",
            "next_action": "next_round" | "end_game",
            "next_scenario_id": 123
        }}
        """

        result = model.generate_content(
            system_prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        # USE ROBUST PARSER
        ai_resp = clean_and_parse_json(result.text)
        
        host_reaction = ai_resp.get("host_reaction", "Interesting choice!")
        next_action = ai_resp.get("next_action", "next_round")
        
        full_reply = host_reaction
        updated_state = state.copy()
        
        if updated_state["current_round"] >= updated_state["max_rounds"]:
            next_action = "end_game"

        if next_action == "next_round":
            updated_state["current_round"] += 1
            
            next_id = ai_resp.get("next_scenario_id")
            next_scenario_obj = next((s for s in SCENARIOS if s['id'] == next_id), None)
            
            if not next_scenario_obj:
                next_scenario_obj = random.choice(available_scenarios)
            
            new_scenario = next_scenario_obj['scenario']
            updated_state["used_scenario_ids"].append(next_scenario_obj['id'])
            updated_state["current_scenario"] = new_scenario
            
            full_reply += f" Next Round! {new_scenario} ... GO!"
            
        elif next_action == "end_game":
            updated_state["phase"] = "done"
            full_reply += f" And that's a wrap! Amazing show, {state.get('player_name')}! Goodnight!"

        print(f"🎤 Host: {full_reply}")

        audio_url = generate_murf_speech(full_reply)

        return {
            "user_transcript": user_text,
            "ai_text": full_reply,
            "audio_url": audio_url,
            "updated_state": updated_state
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})