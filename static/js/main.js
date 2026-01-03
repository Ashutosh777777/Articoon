// ===== DOM Elements =====
const welcomeScreen = document.getElementById('welcome-screen');
const conversationScreen = document.getElementById('conversation-screen');
const feedbackScreen = document.getElementById('feedback-screen');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

const startBtn = document.getElementById('start-btn');
const micBtn = document.getElementById('mic-btn');
const sendBtn = document.getElementById('send-btn');
const endBtn = document.getElementById('end-btn');
const restartBtn = document.getElementById('restart-btn');

const textInput = document.getElementById('text-input');
const chatArea = document.getElementById('chat-area');
const timerDisplay = document.getElementById('timer-display');
const turnCount = document.getElementById('turn-count');
const voiceIndicator = document.getElementById('voice-indicator');
const feedbackContent = document.getElementById('feedback-content');

// ===== State =====
let conversationId = null;
let recognition = null;
let isListening = false;
let timerInterval = null;
let timeRemaining = 300;
let selectedVoice = null;
let voicesReady = false;

// Silence detection
let silenceTimer = null;
let finalTranscript = '';
let interimTranscript = '';

// ===== Cleanup Function =====
function cleanupEverything() {
    console.log('Cleaning up speech and recognition...');
    
    // Stop and cancel speech synthesis
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }
    
    // Stop recognition
    stopListening();
    
    // Clear timers
    clearTimeout(silenceTimer);
    stopTimer();
}

// ===== Speech Recognition Setup =====
function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        
        // Enable continuous recognition
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            console.log('Recognition started');
            isListening = true;
            voiceIndicator.classList.add('active');
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-microphone"></i><span>Listening...</span>';
                micBtn.classList.add('recording');
            }
        };

        recognition.onresult = (event) => {
            // Clear existing silence timer
            clearTimeout(silenceTimer);
            
            interimTranscript = '';
            
            // Process all results
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            // Show what user is saying in real-time
            console.log('Interim:', interimTranscript);
            console.log('Final so far:', finalTranscript);

            // Start 5-second silence timer
            silenceTimer = setTimeout(() => {
                console.log('5 seconds of silence detected');
                stopListeningAndSend();
            }, 5000);
        };

        recognition.onerror = (event) => {
            console.error('Recognition error:', event.error);
            
            // Don't restart on "no-speech" error during natural pauses
            if (event.error === 'no-speech') {
                console.log('No speech detected, waiting...');
                return;
            }
            
            // For other errors, try to restart
            if (event.error !== 'aborted') {
                console.log('Attempting to restart recognition...');
                setTimeout(() => {
                    if (isListening) {
                        startListening();
                    }
                }, 1000);
            }
        };

        recognition.onend = () => {
            console.log('Recognition ended');
            
            // If we're still supposed to be listening, restart
            if (isListening) {
                console.log('Restarting recognition...');
                setTimeout(() => {
                    if (isListening) {
                        startListening();
                    }
                }, 100);
            }
        };
    } else {
        alert('Speech recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
        if (micBtn) micBtn.style.display = 'none';
    }
}

// ===== Speech Output with Enhanced Female Voice =====
function loadVoices() {
    const voices = speechSynthesis.getVoices();
    
    selectedVoice = 
        voices.find(v => v.name.includes('Samantha')) ||
        voices.find(v => v.name.includes('Karen')) ||
        voices.find(v => v.name.includes('Victoria')) ||
        voices.find(v => v.name.includes('Joanna')) ||
        voices.find(v => v.name.includes('Salli')) ||
        voices.find(v => v.name.includes('Google US English Female')) ||
        voices.find(v => v.name.includes('Zira')) ||
        voices.find(v => v.name.includes('Microsoft Zira')) ||
        voices.find(v => v.name.toLowerCase().includes('female')) ||
        voices.find(v => v.lang === 'en-US' && v.name.toLowerCase().includes('woman')) ||
        voices.find(v => v.lang === 'en-US') ||
        voices[0];

    voicesReady = true;
    console.log('Selected voice:', selectedVoice?.name);
}

if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
}
loadVoices();

function speak(text, callback) {
    if (!text) return;
    
    // Stop listening while AI speaks
    stopListening();
    
    speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (!selectedVoice) loadVoices();
    if (selectedVoice) {
        utterance.voice = selectedVoice;
    }
    
    utterance.rate = 0.95;
    utterance.pitch = 1.2;
    utterance.volume = 1.0;
    utterance.lang = 'en-US';
    
    // Resume listening after AI finishes speaking
    utterance.onend = () => {
        console.log('AI finished speaking');
        setTimeout(() => {
            startListening();
            if (callback) callback();
        }, 500); // Small delay before restarting mic
    };
    
    utterance.onerror = () => {
        console.error('Speech synthesis error');
        setTimeout(() => {
            startListening();
            if (callback) callback();
        }, 500);
    };
    
    speechSynthesis.speak(utterance);
}

// ===== Listening Control =====
function startListening() {
    if (!recognition || isListening) return;
    
    try {
        finalTranscript = '';
        interimTranscript = '';
        recognition.start();
    } catch (e) {
        console.error('Error starting recognition:', e);
    }
}

function stopListening() {
    if (!recognition) return;
    
    isListening = false;
    clearTimeout(silenceTimer);
    
    try {
        recognition.stop();
    } catch (e) {
        console.error('Error stopping recognition:', e);
    }
    
    voiceIndicator.classList.remove('active');
    if (micBtn) {
        micBtn.innerHTML = '<i class="fas fa-microphone"></i><span>AI is speaking...</span>';
        micBtn.classList.remove('recording');
    }
}

function stopListeningAndSend() {
    const messageToSend = finalTranscript.trim();
    
    stopListening();
    
    if (messageToSend) {
        console.log('Sending message:', messageToSend);
        sendMessage(messageToSend);
    } else {
        console.log('No message to send, resuming listening');
        // If nothing was said, just resume listening
        setTimeout(() => startListening(), 500);
    }
}

// ===== Timer =====
function startTimer() {
    timerInterval = setInterval(() => {
        timeRemaining--;
        if (timerDisplay) {
            timerDisplay.textContent =
                `${String(Math.floor(timeRemaining / 60)).padStart(2, '0')}:${String(timeRemaining % 60).padStart(2, '0')}`;
        }
        if (timeRemaining <= 0) endConversation();
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
}

// ===== UI =====
function showScreen(screen) {
    if (welcomeScreen && conversationScreen && feedbackScreen) {
        [welcomeScreen, conversationScreen, feedbackScreen].forEach(s => s.classList.remove('active'));
        screen.classList.add('active');
    }
}

function showLoading(text) {
    if (loadingText) loadingText.textContent = text;
    if (loadingOverlay) loadingOverlay.classList.add('active');
}

function hideLoading() {
    if (loadingOverlay) loadingOverlay.classList.remove('active');
}

function addMessage(text, isUser) {
    if (!chatArea) return;
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'ai'}`;
    div.textContent = text;
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// ===== API =====
async function startConversation() {
    showLoading('Starting conversation...');
    
    try {
        // Wait for voices to be ready
        let attempts = 0;
        while (!voicesReady && attempts < 60) {
            await new Promise(r => setTimeout(r, 50));
            attempts++;
        }
        if (!voicesReady) loadVoices();
        
        const res = await fetch('/start_conversation', { method: 'POST' });
        if (!res.ok) throw new Error('Failed to start conversation');

        const data = await res.json();
        conversationId = data.conversation_id;

        if (chatArea) chatArea.innerHTML = '';
        hideLoading();
        if (conversationScreen) showScreen(conversationScreen);
        
        addMessage(data.greeting, false);
        
        // Speak greeting and then start listening
        speak(data.greeting, () => {
            console.log('Ready to listen after greeting');
        });
        
        startTimer();
    } catch (error) {
        console.error('Error starting conversation:', error);
        hideLoading();
        alert('Failed to start conversation. Please try again.');
    }
}

async function sendMessage(msg) {
    if (!msg || !conversationId) return;
    
    addMessage(msg, true);
    if (textInput) textInput.value = '';

    try {
        const res = await fetch('/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: conversationId, message: msg })
        });

        const data = await res.json();
        addMessage(data.response, false);
        if (turnCount) turnCount.textContent = data.turn_count;
        
        // Speak response and resume listening after
        speak(data.response);
    } catch (error) {
        console.error('Error sending message:', error);
        // Resume listening even on error
        setTimeout(() => startListening(), 1000);
    }
}

async function endConversation() {
    stopTimer();
    stopListening();
    
    // IMPORTANT: Cancel speech before redirecting
    speechSynthesis.cancel();
    
    showLoading('Analyzing your conversation...');
    
    try {
        const res = await fetch('/end_conversation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: conversationId })
        });

        const data = await res.json();
        
        // Clean up before navigation
        cleanupEverything();
        
        // Navigate to feedback page
        window.location.href = data.redirect;
    } catch (error) {
        console.error('Error ending conversation:', error);
        hideLoading();
        alert('Failed to end conversation. Please try again.');
    }
}

// ===== Events =====
if (startBtn) {
    startBtn.onclick = startConversation;
}

if (sendBtn) {
    sendBtn.onclick = () => {
        const msg = textInput.value.trim();
        if (msg) {
            stopListeningAndSend();
            textInput.value = msg;
            sendMessage(msg);
        }
    };
}

if (endBtn) {
    endBtn.onclick = endConversation;
}

if (restartBtn) {
    restartBtn.onclick = () => {
        cleanupEverything();
        window.location.href = '/';
    };
}

if (textInput) {
    textInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            const msg = textInput.value.trim();
            if (msg) {
                sendMessage(msg);
            }
        }
    };
}

// Hide mic button since it's automatic now
if (micBtn) {
    micBtn.style.display = 'none';
}

// ===== Page Lifecycle Events =====
// Clean up when page is about to unload
window.addEventListener('beforeunload', () => {
    console.log('Page unloading - cleaning up...');
    cleanupEverything();
});

// Clean up when navigating away (using pagehide for better mobile support)
window.addEventListener('pagehide', () => {
    console.log('Page hiding - cleaning up...');
    cleanupEverything();
});

// Clean up when page visibility changes (tab switching, minimizing)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden - pausing speech...');
        speechSynthesis.pause();
    } else {
        console.log('Page visible - resuming speech...');
        speechSynthesis.resume();
    }
});

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    setupSpeechRecognition();
    loadVoices();
});