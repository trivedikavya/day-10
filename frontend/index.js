document.addEventListener("DOMContentLoaded", () => {
  // Screens
  const joinScreen = document.getElementById("join-screen");
  const gameStage = document.getElementById("game-stage");
  
  // Inputs/Outputs
  const playerNameInput = document.getElementById("player-name");
  const startBtn = document.getElementById("start-btn");
  const roundDisp = document.getElementById("round-disp");
  const playerDisp = document.getElementById("player-disp");
  const scenarioText = document.getElementById("scenario-text");
  const hostFeedback = document.getElementById("host-feedback");
  const micBtn = document.getElementById("mic-btn");
  const statusText = document.getElementById("status-text");
  const agentAudio = document.getElementById("agent-audio");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  // Game State (Frontend Mirror)
  let gameState = {
    player_name: "",
    current_round: 1,
    max_rounds: 3,
    phase: "intro",
    current_scenario: ""
  };

  // --- JOIN GAME ---
  startBtn.addEventListener("click", async () => {
    const name = playerNameInput.value.trim() || "Contestant";
    gameState.player_name = name;
    
    // UI Switch
    joinScreen.classList.add("hidden");
    gameStage.classList.remove("hidden");
    playerDisp.textContent = name;
    
    try {
      const res = await axios.post("http://localhost:5000/start-session", { player_name: name });
      
      // Update State from Backend
      if (res.data.game_state) {
          gameState = res.data.game_state;
          updateStage();
      }
      
      if (res.data.audioUrl) {
        statusText.textContent = "HOST IS SPEAKING...";
        playAudio(res.data.audioUrl);
      }
      
    } catch (err) {
      console.error(err);
      scenarioText.textContent = "Error connecting to studio.";
    }
  });

  // --- MIC LOGIC ---
  micBtn.addEventListener("click", async () => {
    if (gameState.phase === "done") return; // Game over

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          statusText.textContent = "HOST IS JUDGING...";
          micBtn.style.opacity = "0.5";
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-mic");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(gameState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // 1. Show Feedback (AI Text)
            hostFeedback.textContent = `"${res.data.ai_text}"`; // Show full text for now, or splice if needed
            hostFeedback.style.opacity = "1";

            // 2. Update State
            if (res.data.updated_state) {
                gameState = res.data.updated_state;
                // Delay UI update slightly so they hear the feedback first? 
                // Actually better to update scenario text immediately so they can read while host speaks transition
                updateStage();
            }

            // 3. Play Audio
            if (res.data.audio_url) {
              playAudio(res.data.audio_url);
            } else {
              resetMicUI();
            }

          } catch (err) {
            console.error(err);
            statusText.textContent = "Connection drop.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusText.textContent = "YOU ARE LIVE! (ACTION!)";
        micBtn.classList.add("pulse-mic");

      } catch (err) {
        alert("Microphone denied.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  function updateStage() {
    roundDisp.textContent = gameState.current_round;
    
    if (gameState.phase === "done") {
        scenarioText.textContent = "Show's Over! Thanks for playing!";
        scenarioText.classList.remove("text-yellow-300");
        scenarioText.classList.add("text-white");
        micBtn.style.display = "none";
        statusText.textContent = "REFRESH TO PLAY AGAIN";
    } else {
        scenarioText.textContent = gameState.current_scenario;
    }
  }

  function playAudio(url) {
    agentAudio.src = url;
    agentAudio.play();
    
    // While host speaks, disable mic
    micBtn.disabled = true;
    micBtn.style.opacity = "0.5";

    agentAudio.onended = () => {
      if (gameState.phase !== "done") {
        resetMicUI();
        statusText.textContent = "TAP MIC TO PERFORM";
      }
    };
    
    agentAudio.onerror = () => {
        resetMicUI();
    };
  }

  function resetMicUI() {
    micBtn.disabled = false;
    micBtn.style.opacity = "1";
    micBtn.classList.remove("pulse-mic");
  }
});