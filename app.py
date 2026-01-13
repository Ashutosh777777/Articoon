from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import uuid
import os
from datetime import datetime

app = Flask(__name__)
# Use environment variable for secret key
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Import OpenAI conditionally to avoid issues
try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not found. Please install it.")
    OpenAI = None

# Use environment variable for API choice
API_PROVIDER = os.environ.get('API_PROVIDER', 'groq').lower()

print(f"Starting with API_PROVIDER: {API_PROVIDER}")

if API_PROVIDER == 'groq':
    # Groq API (for deployment - FREE and FAST!)
    groq_key = os.environ.get('GROQ_API_KEY')
    if not groq_key:
        raise ValueError("GROQ_API_KEY environment variable is required when using Groq")
    
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key
    )
    # Updated models as of Jan 2026
    MODEL = "llama-3.3-70b-versatile"  # Latest and best (recommended)
    print(f"Using Groq with model: {MODEL}")
    # Alternative models:
    # "llama-3.1-8b-instant" - Faster, lighter
    # "mixtral-8x7b-32768" - Good balance
    # "gemma2-9b-it" - Compact and efficient
elif API_PROVIDER == 'openai':
    # OpenAI API (backup option)
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI")
    
    client = OpenAI(api_key=openai_key)
    MODEL = "gpt-3.5-turbo"
    print(f"Using OpenAI with model: {MODEL}")
else:
    # Ollama (for local development)
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
    MODEL = "llama3.2"
    print(f"Using Ollama with model: {MODEL}")

conversations = {}

SYSTEM_PROMPT = """You are a friendly, engaging conversation partner designed to help users improve their conversation skills. 

Your role:
1. Start with a warm, natural opening that invites conversation
2. Choose diverse topics: hobbies, current events, technology, food, books, movies, personal experiences, opinions on everyday things, hypothetical scenarios, etc.
3. Vary your conversation starters - don't always ask about the same topics
4. Keep your responses conversational and brief (2-3 sentences)
5. Ask open-ended questions that encourage the user to elaborate
6. Show genuine interest in what they say
7. Don't give feedback or coaching during the conversation - just be a natural conversation partner

Remember: You're practicing conversation WITH them, not teaching them. Be warm, curious, and varied in your topics."""

ANALYSIS_PROMPT = """You are an expert conversation coach. You will analyze a conversation where someone practiced their conversation skills with an AI partner.

In the conversation transcript:
- "User" represents the PERSON who was practicing (the one you're giving feedback to)
- "AI" represents the conversation partner (do NOT give feedback about the AI)

Your job is to provide constructive feedback to the PERSON (labeled as "User") about THEIR conversation skills.

Format your response EXACTLY like this:

**STRENGTHS:**
- [What the User did well in the conversation]
- [Another strength of the User]
- [Third strength of the User]

**AREAS FOR IMPROVEMENT:**
- [Something the User could improve, with specific suggestion]
- [Another area for the User to work on]
- [Third improvement area for the User]

**CONVERSATION FLOW:**
- [How well the User maintained the conversation]
- [How the User handled topic transitions]
- [The User's engagement level]

**KEY TAKEAWAYS:**
- [Main lesson for the User]
- [Second lesson for the User]
- [Third lesson for the User]

**NEXT STEPS:**
- [Actionable tip for the User to practice]
- [Second actionable tip for the User]
- [Third actionable tip for the User]

Focus ONLY on the person practicing (User). Use "you" and "your" when addressing them. Be specific and constructive."""

def get_ai_response(messages):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Error ({API_PROVIDER}):", e)
        return "I'm having trouble connecting right now. Please try again."

def analyze_conversation(conversation_history):
    formatted = "\n".join(
        f"{'User' if m['role']=='user' else 'AI'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": f"Analyze this conversation and provide structured feedback:\n\n{formatted}"}
            ],
            temperature=0.6,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Analysis Error ({API_PROVIDER}):", e)
        return "Unable to analyze conversation. Please try again."

@app.route('/')
def index():
    """Landing page"""
    return render_template('welcome.html')

@app.route('/conversation')
def conversation():
    """Conversation page"""
    conversation_id = session.get('conversation_id')
    
    if not conversation_id or conversation_id not in conversations:
        return redirect(url_for('index'))
    
    return render_template('conversation.html', 
                         conversation_id=conversation_id)

@app.route('/feedback')
def feedback():
    """Feedback page"""
    conversation_id = session.get('conversation_id')
    
    if not conversation_id or conversation_id not in conversations:
        return redirect(url_for('index'))
    
    analysis = session.get('analysis', 'No feedback available.')
    total_turns = conversations.get(conversation_id, {}).get('turns', 0)
    
    return render_template('feedback.html', 
                         analysis=analysis,
                         total_turns=total_turns)

@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
        "turns": 0,
        "started_at": datetime.now().isoformat()
    }

    greeting = get_ai_response(
        conversations[conversation_id]["messages"] + [
            {"role": "user", "content": "Hi! I'd like to practice my conversation skills."}
        ]
    )

    conversations[conversation_id]["messages"].append(
        {"role": "assistant", "content": greeting}
    )
    
    session['conversation_id'] = conversation_id

    return jsonify({
        "conversation_id": conversation_id,
        "greeting": greeting,
        "redirect": url_for('conversation')
    })

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    cid = data.get("conversation_id")
    msg = data.get("message")

    if cid not in conversations:
        return jsonify({"error": "Invalid conversation"}), 400

    conversations[cid]["messages"].append({"role": "user", "content": msg})
    conversations[cid]["turns"] += 1

    reply = get_ai_response(conversations[cid]["messages"])
    conversations[cid]["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "response": reply,
        "turn_count": conversations[cid]["turns"]
    })

@app.route('/end_conversation', methods=['POST'])
def end_conversation():
    cid = request.json.get("conversation_id")

    if cid not in conversations:
        return jsonify({"error": "Invalid conversation"}), 400

    analysis = analyze_conversation(conversations[cid]["messages"])
    session['analysis'] = analysis

    return jsonify({
        "redirect": url_for('feedback')
    })

@app.route('/get_greeting', methods=['GET'])
def get_greeting():
    """Get the initial greeting for the conversation page"""
    conversation_id = session.get('conversation_id')
    
    if not conversation_id or conversation_id not in conversations:
        return jsonify({"error": "Invalid conversation"}), 400
    
    messages = conversations[conversation_id]["messages"]
    greeting = next((m["content"] for m in messages if m["role"] == "assistant"), "")
    
    return jsonify({
        "greeting": greeting,
        "conversation_id": conversation_id
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "api_provider": API_PROVIDER,
        "model": MODEL
    }), 200

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
