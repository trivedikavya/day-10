document.addEventListener("DOMContentLoaded", () => {
  const agentText = document.getElementById("agent-text");
  const contentArea = document.getElementById("content-area");
  const micBtn = document.getElementById("mic-btn");
  const startBtn = document.getElementById("start-btn");
  const statusLabel = document.getElementById("status-label");
  const agentAudio = document.getElementById("agent-audio");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  let currentState = {
    last_search_results: []
  };

  // --- INIT ---
  async function initSession() {
    try {
      const res = await axios.post("http://localhost:5000/start-session");
      agentText.textContent = res.data.text;
      if (res.data.audioUrl) playAudio(res.data.audioUrl);
    } catch (err) {
      console.error(err);
    }
  }
  
  startBtn.addEventListener("click", () => location.reload());
  
  // Start immediately
  initSession();

  // --- MIC LOGIC ---
  micBtn.addEventListener("click", async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          statusLabel.textContent = "Processing...";
          micBtn.innerHTML = "⏳";
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-mic");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // 1. Text Response
            agentText.textContent = res.data.ai_text;

            // 2. Update State
            if (res.data.updated_state) {
                currentState = res.data.updated_state;
                // If we got new search results, render them!
                if (currentState.last_search_results && currentState.last_search_results.length > 0) {
                    renderProducts(currentState.last_search_results);
                }
            }

            // 3. Audio
            if (res.data.audioUrl) {
              playAudio(res.data.audioUrl);
            } else {
              resetMicUI();
            }

          } catch (err) {
            console.error(err);
            agentText.textContent = "Sorry, connection issue.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusLabel.textContent = "Listening...";
        micBtn.innerHTML = "⏹️"; 
        micBtn.classList.add("pulse-mic");

      } catch (err) {
        alert("Microphone denied.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  // --- RENDER PRODUCTS ---
  // --- RENDER PRODUCTS WITH IMAGES ---
  function renderProducts(products) {
    contentArea.innerHTML = products.map(p => `
        <div class="bg-white p-4 rounded-lg border border-gray-100 shadow-sm hover:shadow-md transition-all">
            <!-- IMAGE CONTAINER -->
            <div class="h-48 bg-gray-50 rounded mb-4 overflow-hidden flex items-center justify-center">
                <img src="products/${p.image}" alt="${p.name}" class="object-cover h-full w-full" onerror="this.src='https://via.placeholder.com/150?text=No+Image'">
            </div>
            
            <h3 class="font-bold text-gray-800 text-lg leading-tight">${p.name}</h3>
            
            <div class="flex justify-between items-center mt-3">
                <span class="text-purple-600 font-bold text-xl">₹${p.price}</span>
                <span class="text-xs text-gray-500 uppercase tracking-wide bg-gray-100 px-2 py-1 rounded">
                    ${p.sizes.join(", ")}
                </span>
            </div>
        </div>
    `).join("");
  }

  function playAudio(url) {
    agentAudio.src = url;
    statusLabel.textContent = "Speaking...";
    agentAudio.play();
    agentAudio.onended = resetMicUI;
    agentAudio.onerror = resetMicUI;
  }

  function resetMicUI() {
    statusLabel.textContent = "Ready";
    micBtn.disabled = false;
    micBtn.innerHTML = "🎙️";
    micBtn.classList.remove("pulse-mic");
  }
});