document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("start-game-btn");
  const restartBtn = document.getElementById("restart-btn");
  const storyLog = document.getElementById("story-log");
  const startOverlay = document.getElementById("start-overlay");
  const controlsArea = document.getElementById("controls-area");
  
  const micBtn = document.getElementById("mic-toggle-btn");
  const statusText = document.getElementById("status-text");
  const agentAudio = document.getElementById("agent-audio");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  // GAME STATE
  let currentState = {
    history: [] // Stores [{role: 'user', content: '...'}, {role: 'model', content: '...'}]
  };

  // --- START GAME ---
  startBtn.addEventListener("click", async () => {
    startOverlay.classList.add("hidden");
    controlsArea.classList.remove("hidden");
    statusText.textContent = "INITIALIZING WORLD...";
    
    // Clear log just in case
    currentState.history = [];
    
    try {
      const res = await axios.post("http://localhost:5000/start-session");
      
      // Add GM Intro to log
      appendLog("GM", res.data.text);
      
      // Update history for next turn
      currentState.history.push({role: "model", content: res.data.text});

      if (res.data.audioUrl) {
        playAudio(res.data.audioUrl);
      }
    } catch (error) {
      statusText.textContent = "SYSTEM FAILURE.";
      console.error(error);
    }
  });

  // --- RESTART ---
  restartBtn.addEventListener("click", () => {
    location.reload();
  });

  // --- MIC LOGIC ---
  micBtn.addEventListener("click", async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          statusText.textContent = "PROCESSING INPUT...";
          micBtn.innerHTML = "⏳";
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-mic", "border-cyan-400");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          // Send Full History
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // 1. Show User Text
            appendLog("PLAYER", res.data.user_transcript);

            // 2. Show GM Text
            appendLog("GM", res.data.ai_text);

            // 3. Update History State
            if (res.data.updated_state && res.data.updated_state.history) {
                currentState.history = res.data.updated_state.history;
            }

            // 4. Play Audio
            if (res.data.audio_url) {
              playAudio(res.data.audio_url);
            } else {
              statusText.textContent = "AUDIO DATA CORRUPT.";
              resetMicUI();
            }

          } catch (err) {
            console.error(err);
            statusText.textContent = "CONNECTION LOST.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusText.textContent = "RECORDING...";
        micBtn.innerHTML = "🛑"; 
        micBtn.classList.add("pulse-mic", "border-cyan-400");

      } catch (err) {
        alert("Microphone denied.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  // --- HELPER: Append to Chat Log ---
  function appendLog(sender, text) {
    const div = document.createElement("div");
    div.className = "p-4 rounded-lg mb-4 max-w-[90%] text-sm leading-relaxed shadow-md";
    
    if (sender === "GM") {
        div.classList.add("chat-bubble-gm", "mr-auto");
        div.innerHTML = `<strong class="text-pink-500 block text-xs mb-1 tracking-wider">GAME MASTER</strong>${text}`;
    } else {
        div.classList.add("chat-bubble-player", "ml-auto");
        div.innerHTML = `<strong class="text-cyan-300 block text-xs mb-1 tracking-wider">YOU</strong>${text}`;
    }
    
    storyLog.appendChild(div);
    // Auto Scroll to bottom
    storyLog.scrollTop = storyLog.scrollHeight;
  }

  function playAudio(url) {
    agentAudio.src = url;
    statusText.textContent = "NARRATING...";
    agentAudio.play();

    agentAudio.onended = () => {
      resetMicUI();
    };
  }

  function resetMicUI() {
    statusText.textContent = "AWAITING INPUT";
    micBtn.disabled = false;
    micBtn.innerHTML = "🎙️";
    micBtn.classList.remove("pulse-mic", "border-cyan-400");
  }
});