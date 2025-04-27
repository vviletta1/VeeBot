
from flask import Flask, render_template, request, redirect
import wikipedia
import cohere
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Cohere client
cohere_api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(cohere_api_key)

app = Flask(__name__)

# Memory & Chat State
chat_memory = []
titles = []
autocorrect_on = False
memory_on = False

@app.route("/", methods=["GET", "POST"])
def home():
    global autocorrect_on, memory_on
    selected_chat = None

    if request.method == "POST":
        message = request.form["message"]

        # Try Wikipedia first
        try:
            response = wikipedia.summary(message, sentences=2)
        except Exception:
            # If Wikipedia fails, fallback to Cohere
            response = co.generate(
                model='command-light',
                prompt=message,
                max_tokens=100
            ).generations[0].text.strip()

        chat_memory.append({"prompt": message, "response": response})
        titles.append(message[:30])

    if "chat" in request.args:
        index = int(request.args["chat"])
        if index < len(chat_memory):
            selected_chat = chat_memory[index]

    return render_template("index.html", selected_chat=selected_chat, titles=titles, autocorrect_on=autocorrect_on, memory_on=memory_on)

@app.route("/clear", methods=["POST"])
def clear():
    chat_memory.clear()
    titles.clear()
    return redirect("/")

@app.route("/new", methods=["POST"])
def new_chat():
    chat_memory.append({"prompt": "", "response": ""})
    return redirect("/")

@app.route("/toggle_autocorrect", methods=["POST"])
def toggle_autocorrect():
    global autocorrect_on
    autocorrect_on = not autocorrect_on
    return redirect("/")

@app.route("/toggle_memory", methods=["POST"])
def toggle_memory():
    global memory_on
    memory_on = not memory_on
    return redirect("/")

@app.route("/export", methods=["GET"])
def export_chat():
    return {"chat": chat_memory}

if __name__ == "__main__":
    app.run(debug=True)
