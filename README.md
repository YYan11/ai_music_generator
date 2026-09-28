# Text Muse: AI Music Generator

Text Muse is an AI-powered music generation web application that creates MIDI music based on user prompts, emotions, and instrument preferences.

## Features

- Generate MIDI music from text prompts
- Select emotions to guide the music style
- Choose preferred instruments
- AI chatbot assistant for music prompt support
- User login and generation history
- Web-based interface for generating and playing music

## Tech Stack

- Python
- Flask
- HTML, CSS, JavaScript
- Firebase Authentication and Firestore
- MIDI processing
- Groq / LLaMA chatbot integration

## Project Structure

```text
src/                 Core music generation and emotion-control logic
web/backend/         Flask backend API
web/frontend/        Frontend website files
colab/               Dataset preprocessing notebook and script

## Setup and Run

1. Install the required Python libraries:

```bash
pip install -r web/backend/requirements.txt
```

2. Create a `.env` file using `.env.example` as a reference.

Example:

```ini
CHAT_PROVIDER=groq
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

3. Run the backend server:

```bash
python web/backend/app.py
```

4. Open the website in your browser:

```text
http://127.0.0.1:8000
```
