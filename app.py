from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Ollama OpenAI-compatible client
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

conversations = {}

SYSTEM_PROMPT = """You are a friendly, engaging conversation partner designed to help users improve their conversation skills. You start the conversation and ask the user to speak their mind by making a short opening statement. You just need to talk to the user without giving any feedback about his conversation skills or stutters. Let the user speak, analyze and express your own opinion in short and ask questions to keep the conversation going."""

ANALYSIS_PROMPT = """You are an expert conversation coach. Analyze the following conversation and provide constructive feedback in a structured format.

Format your response EXACTLY like this:

**STRENGTHS:**
- [Point 1 about what they did well]
- [Point 2 about what they did well]
- [Point 3 about what they did well]

**AREAS FOR IMPROVEMENT:**
- [Point 1 with specific suggestion]
- [Point 2 with specific suggestion]
- [Point 3 with specific suggestion]

**CONVERSATION FLOW:**
- [Observation about how the conversation progressed]
- [Comment on topic transitions]
- [Note on engagement level]

**KEY TAKEAWAYS:**
- [Main lesson 1]
- [Main lesson 2]
- [Main lesson 3]

**NEXT STEPS:**
- [Actionable tip 1]
- [Actionable tip 2]
- [Actionable tip 3]

Use "you" and "your" when addressing the user. Be specific and constructive."""

def get_ai_response(messages):
    try:
        response = client.chat.completions.create(
            model="llama3.2",
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI Error:", e)
        return "I'm having trouble connecting right now."

def analyze_conversation(conversation_history):
    formatted = "\n".join(
        f"{'User' if m['role']=='user' else 'AI'}: {m['content']}"
        for m in conversation_history if m['role'] != 'system'
    )

    try:
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": f"Analyze this conversation and provide structured feedback:\n\n{formatted}"}
            ],
            temperature=0.6,
            max_tokens=1000  # Increased for structured output
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Analysis Error:", e)
        return "Unable to analyze conversation."

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)