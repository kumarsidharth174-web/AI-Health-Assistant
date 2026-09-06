// const API_URL ="https://ai-health-assistant-w6ht.onrender.com";
const API_URL = "https://ai-health-assistant-w6ht.onrender.com";
// const API_URL = "http://127.0.0.1:5000";
// https://ai-health-assistant-w6ht.onrender.com
// ==========================================
// ELEMENTS
// ==========================================

const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");
const voiceStatus = document.getElementById("voiceStatus");
const reportBtn = document.getElementById("reportBtn");
const reportBox = document.getElementById("reportBox");
const newChatBtn = document.getElementById("newChatBtn");
const historyList = document.getElementById("historyList");
const conversationCount = document.getElementById("conversationCount");
const emergencyBanner = document.getElementById("emergencyBanner");
const summaryGrid = document.getElementById("summaryGrid");
const symptomStat = document.getElementById("symptomStat");

const profileModal = document.getElementById("profileModal");
const profileName = document.getElementById("profileName");
const profileAge = document.getElementById("profileAge");
const profileGender = document.getElementById("profileGender");
const profilePhone = document.getElementById("profilePhone");
const profileSaveBtn = document.getElementById("profileSaveBtn");
const profileSkipBtn = document.getElementById("profileSkipBtn");

const patientBox = document.getElementById("patientBox");
const patientNameEl = document.getElementById("patientName");
const patientMetaEl = document.getElementById("patientMeta");
const patientAvatarEl = document.getElementById("patientAvatar");

const quickReportAction = document.getElementById("quickReportAction");


// ==========================================
// PATIENT SESSION
// ==========================================

let patientId = localStorage.getItem("patient_id");
let conversationId = localStorage.getItem("conversation_id");


function saveSession(patient, conversation) {

    patientId = patient;
    conversationId = conversation;

    if (patient) {
        localStorage.setItem("patient_id", patient);
    }

    if (conversation) {
        localStorage.setItem("conversation_id", conversation);
    }
}


// ==========================================
// PATIENT PROFILE SETUP
// ==========================================

async function initPatientProfile() {

    if (patientId) {

        await loadPatientInfo();
        await loadHistory();
        await refreshSummary();

        return;
    }

    profileModal.classList.remove("hidden");
}


profileSaveBtn.addEventListener("click", async function () {

    await createPatientProfile({
        name: profileName.value.trim() || "Guest Patient",
        age: profileAge.value ? Number(profileAge.value) : null,
        gender: profileGender.value || null,
        phone: profilePhone.value.trim() || null
    });

});


profileSkipBtn.addEventListener("click", async function () {

    await createPatientProfile({ name: "Guest Patient" });

});


async function createPatientProfile(profile) {

    try {

        const response = await fetch(`${API_URL}/patient`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profile)
        });

        const data = await response.json();

        if (!response.ok || !data.patient_id) {
            alert("Could not save your profile. Please check the backend is running.");
            return;
        }

        saveSession(data.patient_id, null);

        applyPatientToHeader(data.patient);

        profileModal.classList.add("hidden");

        await loadHistory();

    } catch (error) {

        console.error(error);
        alert("Could not connect to the server. Please make sure the backend is running.");

    }

}


async function loadPatientInfo() {

    try {

        const response = await fetch(`${API_URL}/patient/${patientId}`);
        const data = await response.json();

        if (response.ok && data.patient) {
            applyPatientToHeader(data.patient);
        }

    } catch (error) {

        console.error("Could not load patient info:", error);

    }

}


function applyPatientToHeader(patient) {

    if (!patient) return;

    const displayName = patient.name || "Guest Patient";

    patientNameEl.textContent = displayName;
    patientAvatarEl.textContent = displayName.charAt(0).toUpperCase();

    const metaParts = [];

    if (patient.age) metaParts.push(`${patient.age} yrs`);
    if (patient.gender) metaParts.push(patient.gender);

    patientMetaEl.textContent = metaParts.length ? metaParts.join(" • ") : "Personal Health";

}


patientBox.addEventListener("click", function () {

    profileName.value = patientNameEl.textContent === "Guest Patient" ? "" : patientNameEl.textContent;
    profileModal.classList.remove("hidden");

});


// ==========================================
// SEND BUTTON
// ==========================================

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {
        sendMessage();
    }

});


// ==========================================
// SEND MESSAGE
// ==========================================

async function sendMessage() {

    const message = userInput.value.trim();

    if (!message) return;

    addUserMessage(message);

    userInput.value = "";

    sendBtn.disabled = true;

    const thinking = addThinkingMessage();

    try {

        const response = await fetch(`${API_URL}/chat`, {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify({
                message: message,
                patient_id: patientId,
                conversation_id: conversationId
            })

        });

        const data = await response.json();

        thinking.remove();

        if (!response.ok) {
            addAIMessage(data.reply || "AI server error. Please try again.");
            return;
        }

        saveSession(data.patient_id, data.conversation_id);

        addAIMessage(data.reply);

        if (data.emergency) {
            showEmergencyBanner();
        }

        await loadHistory();
        await refreshSummary();

    } catch (error) {

        console.error(error);

        thinking.remove();

        addAIMessage(
            "Unable to connect to the AI server. Please check your internet connection " +
            "or try again in a moment."
        );

    } finally {

        sendBtn.disabled = false;

    }

}


function showEmergencyBanner() {

    emergencyBanner.classList.remove("hidden");
    emergencyBanner.classList.add("shake");
    emergencyBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });

    setTimeout(() => emergencyBanner.classList.remove("shake"), 700);

}


// ==========================================
// USER MESSAGE
// ==========================================

function addUserMessage(text) {

    const div = document.createElement("div");

    div.className = "message user-message fade-in";

    div.innerHTML = `
        <div class="user-bubble">
            <strong>You</strong>
            <p>${escapeHTML(text)}</p>
        </div>
    `;

    chatBox.appendChild(div);

    scrollChat();

}


// ==========================================
// THINKING
// ==========================================

function addThinkingMessage() {

    const div = document.createElement("div");

    div.className = "message ai-message fade-in";

    div.innerHTML = `
        <div class="message-icon">AI</div>
        <div class="ai-bubble">
            <strong>AI Assistant</strong>
            <p class="typing-dots"><span></span><span></span><span></span></p>
        </div>
    `;

    chatBox.appendChild(div);

    scrollChat();

    return div;

}


// ==========================================
// AI MESSAGE (auto-speak REMOVED - only speaks on button click now)
// ==========================================

function addAIMessage(text) {

    const div = document.createElement("div");

    div.className = "message ai-message fade-in";

    div.innerHTML = `
        <div class="message-icon">AI</div>
        <div class="ai-bubble">
            <strong>AI Assistant</strong>
            <p>${escapeHTML(text)}</p>
            <button class="speak-btn" data-text="${escapeAttribute(text)}">
                🔊 Speak
            </button>
        </div>
    `;

    chatBox.appendChild(div);

    const speakButton = div.querySelector(".speak-btn");

    speakButton.addEventListener("click", function () {
        speakText(text, speakButton);
    });

    scrollChat();

    // NOTE: automatic speech-on-arrival removed on purpose.
    // The AI reply no longer speaks itself - only clicking
    // "🔊 Speak" plays the voice now.

}


// ==========================================
// SPEECH OUTPUT (Indian English female voice)
// ==========================================

let cachedVoices = [];

if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = function () {
        cachedVoices = window.speechSynthesis.getVoices();
    };
    cachedVoices = window.speechSynthesis.getVoices();
}


// Common Indian-English / female voice names across
// Chrome, Edge, Android and Windows so we catch more matches.
const INDIAN_FEMALE_NAME_HINTS =
    /female|woman|zira|heera|priya|veena|raveena|neerja|kalpana|lekha|india/i;


function pickVoice() {

    const voices = cachedVoices.length ? cachedVoices : window.speechSynthesis.getVoices();

    // 1) Best match: en-IN + sounds female
    let selected = voices.find(
        v => v.lang === "en-IN" && INDIAN_FEMALE_NAME_HINTS.test(v.name)
    );

    // 2) Any en-IN voice (Google's default en-IN is usually female)
    if (!selected) {
        selected = voices.find(v => v.lang === "en-IN");
    }

    // 3) Any voice with an Indian-sounding female name, any locale
    if (!selected) {
        selected = voices.find(v => INDIAN_FEMALE_NAME_HINTS.test(v.name));
    }

    // 4) Fallback: any female-sounding English voice
    if (!selected) {
        selected = voices.find(v => /en-/i.test(v.lang) && /female|woman/i.test(v.name));
    }

    return selected || null;

}


function speakText(text, button) {

    if (!window.speechSynthesis) return;

    window.speechSynthesis.cancel();

    const speech = new SpeechSynthesisUtterance(text);

    speech.lang = "en-IN";
    speech.rate = 0.9;
    speech.pitch = 1.1;

    const selectedVoice = pickVoice();

    if (selectedVoice) {
        speech.voice = selectedVoice;
    }

    if (button) {
        button.textContent = "🔊 Speaking...";
        button.classList.add("speaking");
    }

    speech.onend = function () {
        if (button) {
            button.textContent = "🔊 Speak";
            button.classList.remove("speaking");
        }
    };

    speech.onerror = function () {
        if (button) {
            button.textContent = "🔊 Speak";
            button.classList.remove("speaking");
        }
    };

    window.speechSynthesis.speak(speech);

}


function stopSpeaking() {
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
}


// ==========================================
// MICROPHONE (Speech-to-Text)
// ==========================================

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";

    voiceBtn.addEventListener("click", function () {

        try {

            stopSpeaking();

            recognition.start();

            voiceBtn.textContent = "🔴";
            voiceBtn.classList.add("listening");
            voiceStatus.textContent = "Listening... Speak now.";

        } catch (error) {
            console.log(error);
        }

    });

    recognition.onresult = function (event) {

        const transcript = event.results[0][0].transcript;

        userInput.value = transcript;

        voiceStatus.textContent = "Voice captured. Sending...";
        voiceBtn.textContent = "🎤";
        voiceBtn.classList.remove("listening");

        setTimeout(sendMessage, 400);

    };

    recognition.onend = function () {
        voiceBtn.textContent = "🎤";
        voiceBtn.classList.remove("listening");
    };

    recognition.onerror = function (event) {

        console.log("Voice error:", event.error);

        voiceBtn.textContent = "🎤";
        voiceBtn.classList.remove("listening");

        if (event.error === "not-allowed" || event.error === "permission-denied") {
            voiceStatus.textContent = "Microphone permission denied.";
        } else if (event.error === "no-speech") {
            voiceStatus.textContent = "No speech detected. Try again.";
        } else {
            voiceStatus.textContent = "Could not hear you. Try again.";
        }

    };

} else {

    voiceBtn.addEventListener("click", function () {
        alert("Voice recognition is not supported in this browser. Please use Google Chrome.");
    });

}


// ==========================================
// SPEAK BUTTONS ALREADY ON PAGE
// ==========================================

document.querySelectorAll(".speak-btn").forEach(button => {

    button.addEventListener("click", function () {
        speakText(button.dataset.text, button);
    });

});


// ==========================================
// GENERATE REPORT
// ==========================================

reportBtn.addEventListener("click", generateReport);
quickReportAction.addEventListener("click", generateReport);


async function generateReport() {

    if (!patientId) {
        reportBox.textContent = "Please have a conversation first.";
        return;
    }

    reportBtn.disabled = true;
    reportBtn.textContent = "Generating...";
    reportBox.textContent = "AI is analyzing the patient's conversation...";
    reportBox.classList.add("pulse-loading");

    try {

        const response = await fetch(`${API_URL}/report`, {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify({ patient_id: patientId })

        });

        const data = await response.json();

        if (data.report) {
            reportBox.textContent = data.report;
        } else {
            reportBox.textContent = data.error || "Unable to generate report.";
        }

    } catch (error) {

        console.error(error);
        reportBox.textContent = "Could not connect to the server.";

    }

    reportBox.classList.remove("pulse-loading");
    reportBtn.disabled = false;
    reportBtn.textContent = "📊 Generate Health Report";

}


// ==========================================
// PATIENT HEALTH SUMMARY (auto-updates)
// ==========================================

async function refreshSummary() {

    if (!patientId) return;

    try {

        const response = await fetch(`${API_URL}/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ patient_id: patientId })
        });

        const data = await response.json();

        if (!response.ok || !data.summary) return;

        Object.entries(data.summary).forEach(([key, value]) => {

            const el = summaryGrid.querySelector(`[data-field="${key}"]`);

            if (el && el.textContent !== value) {
                el.textContent = value || "Not provided";
                el.classList.add("value-updated");
                setTimeout(() => el.classList.remove("value-updated"), 900);
            }

        });

        if (data.summary.symptoms && data.summary.symptoms !== "Not provided") {
            symptomStat.textContent = data.summary.symptoms;
        }

    } catch (error) {

        console.log("Summary not available yet:", error);

    }

}


// ==========================================
// QUICK ACTIONS
// ==========================================

document.querySelectorAll(".quick-action[data-message]").forEach(button => {

    button.addEventListener("click", function () {
        userInput.value = button.dataset.message;
        userInput.focus();
    });

});


// ==========================================
// NEW CHAT (keeps old conversation saved)
// ==========================================

newChatBtn.addEventListener("click", async function () {

    if (!patientId) return;

    try {

        const response = await fetch(`${API_URL}/new-chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ patient_id: patientId })
        });

        const data = await response.json();

        if (response.ok && data.conversation_id) {
            saveSession(patientId, data.conversation_id);
        } else {
            localStorage.removeItem("conversation_id");
            conversationId = null;
        }

    } catch (error) {

        console.error(error);
        localStorage.removeItem("conversation_id");
        conversationId = null;

    }

    chatBox.innerHTML = `
        <div class="message ai-message fade-in">
            <div class="message-icon">AI</div>
            <div>
                <strong>AI Assistant</strong>
                <p>New consultation started. How can I help you?</p>
            </div>
        </div>
    `;

    emergencyBanner.classList.add("hidden");

    await loadHistory();

});


// ==========================================
// PATIENT HISTORY
// ==========================================

async function loadHistory() {

    if (!patientId) return;

    try {

        const response = await fetch(`${API_URL}/history/${patientId}`);
        const data = await response.json();

        if (!response.ok || !data.conversations) return;

        conversationCount.textContent = data.conversations.length;

        if (data.conversations.length === 0) {
            historyList.innerHTML = `<p class="empty-note">No previous conversations yet.</p>`;
            return;
        }

        historyList.innerHTML = "";

        data.conversations.forEach(conv => {

            const item = document.createElement("button");

            item.className = "history-item fade-in";

            if (String(conv.id) === String(conversationId)) {
                item.classList.add("active");
            }

            const date = new Date(conv.created_at);
            const dateLabel = isNaN(date) ? "" : date.toLocaleString();

            item.innerHTML = `
                <strong>${escapeHTML(conv.title || "Consultation")}</strong>
                <small>${escapeHTML(dateLabel)}</small>
            `;

            item.addEventListener("click", function () {
                openConversation(conv.id);
            });

            historyList.appendChild(item);

        });

    } catch (error) {

        console.log("Could not load history:", error);

    }

}


async function openConversation(id) {

    try {

        const response = await fetch(`${API_URL}/conversation/${id}`);
        const data = await response.json();

        if (!response.ok || !data.messages) return;

        saveSession(patientId, id);

        chatBox.innerHTML = "";

        if (data.messages.length === 0) {
            chatBox.innerHTML = `
                <div class="message ai-message fade-in">
                    <div class="message-icon">AI</div>
                    <div><strong>AI Assistant</strong><p>This conversation has no messages yet.</p></div>
                </div>
            `;
        }

        data.messages.forEach(msg => {

            if (msg.sender === "patient") {
                addUserMessageSilent(msg.message);
            } else {
                addAIMessageSilent(msg.message);
            }

        });

        scrollChat();

        document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
        await loadHistory();

    } catch (error) {

        console.error("Could not open conversation:", error);

    }

}


function addUserMessageSilent(text) {

    const div = document.createElement("div");
    div.className = "message user-message fade-in";
    div.innerHTML = `<div class="user-bubble"><strong>You</strong><p>${escapeHTML(text)}</p></div>`;
    chatBox.appendChild(div);

}


function addAIMessageSilent(text) {

    const div = document.createElement("div");
    div.className = "message ai-message fade-in";
    div.innerHTML = `
        <div class="message-icon">AI</div>
        <div class="ai-bubble">
            <strong>AI Assistant</strong>
            <p>${escapeHTML(text)}</p>
            <button class="speak-btn" data-text="${escapeAttribute(text)}">🔊 Speak</button>
        </div>
    `;

    chatBox.appendChild(div);

    div.querySelector(".speak-btn").addEventListener("click", function () {
        speakText(text, this);
    });

}


// ==========================================
// SCROLL
// ==========================================

function scrollChat() {
    chatBox.scrollTop = chatBox.scrollHeight;
}


// ==========================================
// SECURITY
// ==========================================

function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


function escapeAttribute(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}


// ==========================================
// START
// ==========================================

initPatientProfile();