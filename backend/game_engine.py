import json
import random

# --- SCENARIOS LIST ---
SCENARIOS = [
    "You are a barista telling a customer their latte is a portal to another dimension.",
    "You are a time-travelling tour guide explaining TikTok to a peasant from 1400 AD.",
    "You are a cat trying to convince a dog to let you blame him for the broken vase.",
    "You are an alien tour guide pretending to be human but getting basic facts wrong.",
    "You are a waiter calmly explaining that the customer's soup is actually a magical potion."
]

def get_initial_state():
    return {
        "phase": "intro",        
        "player_name": "",
        "round": 0,
        "max_rounds": 3,         # Game ends after 3 rounds
        "current_scenario": "",
        "history": [] 
    }

def get_system_prompt(state, user_text):
    # SAFETY: Default to 'playing' if phase is weird
    phase = state.get("phase", "playing")
    
    # 1. INTRO PHASE
    if phase == "intro":
        return f"""
        You are the host of a chaotic improv game show called 'Improv Battle'.
        User Input: "{user_text}"
        
        GOAL:
        1. Extract name.
        2. Welcome them.
        3. Give FIRST Scenario: "{SCENARIOS[0]}"
        
        OUTPUT JSON:
        {{
            "reply": "Welcome [Name]! Your first scenario is: {SCENARIOS[0]}",
            "player_name": "extracted_name",
            "next_phase": "playing",
            "next_scenario": "{SCENARIOS[0]}"
        }}
        """

    # 2. PLAYING PHASE
    elif phase == "playing":
        current_round = state.get("round", 0)
        max_r = state.get("max_rounds", 3)
        
        # Logic: Are we moving to the next round OR ending?
        next_r_index = current_round + 1
        is_game_over = next_r_index >= max_r
        
        # SAFETY: Cycle scenarios if we run out (Modulo operator)
        safe_scenario_idx = next_r_index % len(SCENARIOS)
        next_scenario = SCENARIOS[safe_scenario_idx]

        return f"""
        Host of 'Improv Battle'. 
        SCENARIO: "{state.get('current_scenario')}"
        ACT: "{user_text}"
        
        GOAL:
        1. Rate performance (witty/funny).
        2. IF game NOT over ({next_r_index}/{max_r}): Give next scenario: "{next_scenario}".
        3. IF game IS over: Say "That was the final round! Let's see how you did..."
        
        OUTPUT JSON:
        {{
            "reply": "Great acting! Next scenario: {next_scenario}..." (OR "Game over summary..."),
            "next_phase": "{'summary' if is_game_over else 'playing'}",
            "next_scenario": "{'' if is_game_over else next_scenario}"
        }}
        """

    # 3. SUMMARY PHASE
    elif phase == "summary":
        return f"""
        Host of 'Improv Battle'. Game Over.
        HISTORY: {json.dumps(state.get('history', []))}
        
        GOAL: Summarize player style and say goodbye.
        
        OUTPUT JSON:
        {{
            "reply": "You were hilarious! Thanks for playing.",
            "next_phase": "ended",
            "next_scenario": ""
        }}
        """
    
    # FALLBACK (Prevents "contents must not be empty" error)
    return "You are a helpful AI. Just say 'Error in game state, let's reset'."