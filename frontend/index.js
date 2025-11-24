document.addEventListener("DOMContentLoaded", () => {
  const startScreen = document.getElementById("start-screen");
  const conversationScreen = document.getElementById("conversation-screen");
  const startConvBtn = document.getElementById("start-conv-btn");
  const micToggleBtn = document.getElementById("mic-toggle-btn");
  const statusText = document.getElementById("status-text");
  const agentAudio = document.getElementById("agent-audio");

  // Display Fields
  const dispMood = document.getElementById("disp-mood");
  const dispEnergy = document.getElementById("disp-energy");
  const dispGoals = document.getElementById("disp-goals");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  // --- WELLNESS STATE ---
  let currentState = {
    mood: null,
    energy: null,
    goals: [],
    is_complete: false
  };

  // --- 1. START SESSION (With History Check) ---
  startConvBtn.addEventListener("click", async () => {
    startScreen.classList.add("hidden");
    conversationScreen.classList.remove("hidden");
    statusText.textContent = "Checking your history... 📖";
    
    // Reset UI
    updateDisplay();

    try {
      // Call the new SMART GREETING endpoint
      const res = await axios.post("http://localhost:5000/start-session");

      if (res.data.audioUrl) {
        playAudio(res.data.audioUrl);
      }
    } catch (error) {
      statusText.textContent = "Error connecting.";
      console.error(error);
    }
  });

  // --- 2. MIC TOGGLE ---
  micToggleBtn.addEventListener("click", async () => {
    if (!isRecording) {
      // START RECORDING
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          // STOPPED -> PROCESS
          statusText.textContent = "Reflecting... 🌿";
          micToggleBtn.innerHTML = "⏳";
          micToggleBtn.disabled = true;
          micToggleBtn.classList.remove("pulse-ring", "bg-teal-500", "text-white");
          micToggleBtn.classList.add("bg-teal-100", "text-teal-600");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // Update State & UI
            if (res.data.updated_state) {
                currentState = res.data.updated_state;
                updateDisplay();
            }

            // Play Reply
            if (res.data.audio_url) {
              playAudio(res.data.audio_url);
            }

          } catch (err) {
            console.error(err);
            statusText.textContent = "I didn't quite catch that.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        
        statusText.textContent = "Listening...";
        micToggleBtn.innerHTML = "⏹️"; 
        micToggleBtn.classList.remove("bg-teal-100", "text-teal-600");
        micToggleBtn.classList.add("bg-teal-500", "text-white", "pulse-ring");

      } catch (err) {
        alert("Microphone denied.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  function updateDisplay() {
    dispMood.textContent = currentState.mood || "-";
    dispEnergy.textContent = currentState.energy || "-";
    
    if (currentState.goals && currentState.goals.length > 0) {
        dispGoals.innerHTML = currentState.goals.map(g => `• ${g}`).join("<br>");
    } else {
        dispGoals.textContent = "-";
    }
  }

  function playAudio(url) {
    agentAudio.src = url;
    statusText.textContent = "Speaking... 🗣️";
    agentAudio.play();

    agentAudio.onended = () => {
      if (currentState.is_complete) {
        statusText.textContent = "Session Complete 🌿";
        micToggleBtn.innerHTML = "✨";
      } else {
        resetMicUI();
      }
    };
  }

  function resetMicUI() {
    statusText.textContent = "Tap to Reply";
    micToggleBtn.disabled = false;
    micToggleBtn.innerHTML = "🎙️";
  }
});