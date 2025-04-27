from flask import Flask, render_template, request, session, redirect, url_for, make_response
import wikipedia
import cohere
import os
from dotenv import load_dotenv
import language_tool_python

# Setup
load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))
tool = language_tool_python.LanguageTool('en-US')

app = Flask(__name__)
app.secret_key = 'secret_key_for_session_storage'

# Triggers
search_keywords = ["search", "who is", "what is", "tell me about", "find", "define", "what’s", "give me info on"]
greetings = ["hello", "hi", "hey", "yo", "what’s up", "sup", "good morning", "good afternoon"]
thanks = ["thanks", "thank you", "thx", "much appreciated"]
goodbyes = ["bye", "goodbye", "see ya", "later", "peace out", "catch you later"]

def get_bot_response(user_input):
    user_input = user_input.lower()

    # Translation feature
    if "translate" in user_input and "to" in user_input:
        try:
            parts = user_input.split("translate")[1].strip().split("to")
            phrase = parts[0].strip()
            target_lang = parts[1].strip()
            translated = GoogleTranslator(source='auto', target=target_lang).translate(phrase)
            return f"🗣️ '{phrase}' in {target_lang.title()} is: <strong>{translated}</strong>"
        except:
            return "❌ I couldn't translate that. Please use the format: 'translate hello to French'"

    # (continue with your other conditions below...)
    if any(word in user_input for word in greetings):
        return "Hey there! How can I help you today? 😊"
    # etc...

    if any(keyword in user_input for keyword in search_keywords):
        topic = user_input
        for phrase in search_keywords:
            topic = topic.replace(phrase, "")
        topic = topic.strip()

        try:
            summary = wikipedia.summary(topic, sentences=2)
            link = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
            return f"🧠 <strong>{topic.title()}</strong><br>{summary}<br><a href='{link}' target='_blank'>Read more on Wikipedia</a>"
        except wikipedia.exceptions.DisambiguationError as e:
            options = ', '.join(e.options[:5])
            return f"🧠 Too broad. Did you mean: {options}"
        except:
            wiki_url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
            return f"❌ Couldn't find it. Try here: <a href='{wiki_url}' target='_blank'>{wiki_url}</a>"

    if any(word in user_input for word in greetings):
        return "Hey there! How can I help you today? 😊"
    elif "how are you" in user_input:
        return "I'm just code, but I'm feeling great! 😄"
    elif "your name" in user_input:
        return "I'm VeeBot, your AI buddy!"
    elif "what can you do" in user_input:
        return "I can chat, search, and help with grammar using AI tools!"
    elif any(word in user_input for word in thanks):
        return "You're welcome!"
    elif any(word in user_input for word in goodbyes):
        return "Goodbye! 👋"

    try:
        messages = []
        if session.get("memory_on", True):
            history = session.get("conversations", [])[-10:]
            for convo in history:
                messages.append({"role": "USER", "message": convo["prompt"]})
                messages.append({"role": "CHATBOT", "message": convo["response"]})

        response = co.chat(model='command-nightly', message=user_input, chat_history=messages)
        return response.text.strip()
    except Exception as e:
        print("❌ Cohere error:", e)
        return "Sorry, I'm having trouble thinking right now. 🧠❌"


# Routes
@app.route("/", methods=["GET", "POST"])
def chatbot():
    if "conversations" not in session:
        session["conversations"] = []
    if "titles" not in session:
        session["titles"] = []
    if "memory_on" not in session:
        session["memory_on"] = True
    if "autocorrect_on" not in session:
        session["autocorrect_on"] = True

    if request.method == "POST":
        user_message = request.form["message"]
        if session.get("autocorrect_on"):
            suggested = correct_text(user_message)
            if suggested != user_message:
                session["last_corrected"] = suggested
                return redirect(url_for("chatbot", preview="1"))

        if session.get("last_corrected"):
            user_message = session.pop("last_corrected")

        bot_reply = get_bot_response(user_message)
        session["conversations"].append({
            "prompt": user_message,
            "response": bot_reply
        })
        session["titles"].append(user_message[:40] + ("..." if len(user_message) > 40 else ""))
        session.modified = True
        return redirect(url_for("chatbot", chat=len(session["conversations"]) - 1))

    selected_index = request.args.get("chat")
    selected_chat = None
    if selected_index is not None:
        try:
            selected_index = int(selected_index)
            selected_chat = session["conversations"][selected_index]
        except:
            selected_chat = None
    elif session["conversations"]:
        selected_chat = session["conversations"][-1]

    return render_template("index.html",
        conversations=session["conversations"],
        selected_chat=selected_chat,
        titles=session["titles"],
        memory_on=session.get("memory_on", True),
        autocorrect_on=session.get("autocorrect_on", True),
        suggestion=session.get("last_corrected")
    )

@app.route("/toggle_memory", methods=["POST"])
def toggle_memory():
    session["memory_on"] = not session.get("memory_on", True)
    return redirect(url_for("chatbot"))

@app.route("/toggle_autocorrect", methods=["POST"])
def toggle_autocorrect():
    session["autocorrect_on"] = not session.get("autocorrect_on", True)
    return redirect(url_for("chatbot"))

@app.route("/clear", methods=["POST"])
def clear_chat():
    session.clear()
    return redirect(url_for("chatbot"))

@app.route("/new", methods=["POST"])
def new_chat():
    session["conversations"] = []
    session["titles"] = []
    return redirect(url_for("chatbot"))

@app.route("/export")
def export_chat():
    history = session.get("conversations", [])
    chat_lines = [f"You: {item['prompt']}\nBot: {item['response']}" for item in history]
    response = make_response("\n\n".join(chat_lines))
    response.headers["Content-Disposition"] = "attachment; filename=veebot_chat.txt"
    response.headers["Content-Type"] = "text/plain"
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5001)