# Riya Version 2

A local Streamlit assistant powered by Ollama. This version provides multi-chat history, streamed responses, and practical desktop controls from the sidebar.

## Features

- Local chat through `llama3.2:1b`
- Multiple conversations with persistent history
- Automatic conversation titles
- Laptop details and battery status
- Safe shortcuts for Calculator, Notepad, File Explorer, and Windows Settings
- Google Search shortcut

## Setup

Install Python 3.10 or newer, Streamlit, and Requests:

```powershell
python -m pip install -r requirements.txt
```

Install and start Ollama, then make the chat model available:

```powershell
ollama pull llama3.2:1b
```

## Run

```powershell
streamlit run riya3.py
```

The assistant requires Ollama to be available at `http://localhost:11434`.
