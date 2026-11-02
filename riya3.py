import streamlit as st
import json
import os
import requests
import uuid
import ctypes
import platform
import shutil
import subprocess
import webbrowser

# --- Configuration ---
MEMORY_FILE = "riya_multichat_memory.json"
# The locally installed conversational Ollama model.
CHAT_MODEL = "llama3.2:1b"


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_system_info():
    """Return basic device information without exposing personal files."""
    disk = shutil.disk_usage(os.path.abspath(os.sep))
    gib = 1024 ** 3
    return {
        "Operating system": f"{platform.system()} {platform.release()}",
        "Machine": platform.machine(),
        "Processor": platform.processor() or "Not reported",
        "Python": platform.python_version(),
        "Storage": f"{disk.free / gib:.1f} GB free of {disk.total / gib:.1f} GB",
    }


def get_battery_status():
    if os.name != "nt":
        return "Battery status is available on Windows only."
    status = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return "Could not read battery status."
    if status.BatteryLifePercent == 255:
        return "No battery information is available."
    power_source = "plugged in" if status.ACLineStatus == 1 else "on battery"
    return f"Battery: {status.BatteryLifePercent}% ({power_source})"


def open_system_tool(tool):
    """Launch only a small allow-list of safe Windows tools."""
    commands = {
        "Calculator": ["calc.exe"],
        "Notepad": ["notepad.exe"],
        "File Explorer": ["explorer.exe"],
        "Settings": ["cmd.exe", "/c", "start", "", "ms-settings:"],
    }
    subprocess.Popen(commands[tool], shell=False)


# Streamlit page configuration must run before any widgets or session-state access.
st.set_page_config(page_title="Riya AI", page_icon="🤖", layout="wide")

# --- Data Persistence Functions ---
def load_all_chats():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_chats(all_chats):
    with open(MEMORY_FILE, "w") as f:
        json.dump(all_chats, f, indent=4)

# --- Session State Initialization ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()

if not st.session_state.all_chats:
    # Create an initial chat if none exist
    first_id = str(uuid.uuid4())
    st.session_state.all_chats[first_id] = {"name": "New Conversation", "messages": []}
    st.session_state.current_chat_id = first_id
elif "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]

# --- Sidebar: Multi-Conversation Manager ---
with st.sidebar:
    st.title("Riya Assistant 🤖")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"name": "New Conversation", "messages": []}
        st.session_state.current_chat_id = new_id
        save_all_chats(st.session_state.all_chats)
        st.rerun()

    st.divider()
    st.subheader("Recent Chats")
    
    # List all chats like ChatGPT/Gemini
    for chat_id in list(st.session_state.all_chats.keys()):
        col1, col2 = st.columns([0.8, 0.2])
        
        # Highlight the active chat
        btn_type = "primary" if chat_id == st.session_state.current_chat_id else "secondary"
        
        if col1.button(st.session_state.all_chats[chat_id]["name"], key=f"btn_{chat_id}", use_container_width=True, type=btn_type):
            st.session_state.current_chat_id = chat_id
            st.rerun()
            
        if col2.button("🗑️", key=f"del_{chat_id}"):
            del st.session_state.all_chats[chat_id]
            save_all_chats(st.session_state.all_chats)
            # Reset current chat if we deleted the active one
            if not st.session_state.all_chats:
                st.rerun() # Will trigger re-init
            else:
                st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
                st.rerun()

    st.divider()
    st.header("Settings")
    st.caption(f"Local model: `{CHAT_MODEL}`")

    st.divider()
    st.header("System Controls")
    if st.button("Show laptop details", use_container_width=True):
        st.session_state.show_system_info = not st.session_state.get("show_system_info", False)
    if st.session_state.get("show_system_info", False):
        st.json(get_system_info())

    if st.button("Check battery", use_container_width=True):
        st.info(get_battery_status())

    tool = st.selectbox("Open a system tool", ["Calculator", "Notepad", "File Explorer", "Settings"])
    if st.button(f"Open {tool}", use_container_width=True):
        try:
            open_system_tool(tool)
            st.success(f"Opening {tool}.")
        except OSError as error:
            st.error(f"Could not open {tool}: {error}")

    if st.button("Open Google Search", use_container_width=True):
        webbrowser.open("https://www.google.com")
        st.success("Opened Google Search.")

# --- Main Chat Area ---
active_chat = st.session_state.all_chats[st.session_state.current_chat_id]
st.title(f"💬 {active_chat['name']}")

# Display chat history for the ACTIVE chat only
for message in active_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Logic ---
if prompt := st.chat_input("What's on your mind?"):
    # 1. Add user message
    active_chat["messages"].append({"role": "user", "content": prompt})
    
    # 2. Auto-rename the chat based on the first prompt (just like ChatGPT)
    if active_chat["name"] == "New Conversation":
        active_chat["name"] = prompt[:25] + "..." if len(prompt) > 25 else prompt
        
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        system_prompt = (
            "You are Riya, a practical and sharp AI assistant for Vignesh. "
            "The interface provides explicit system-control buttons. Never claim you opened "
            "an app, changed a system setting, or accessed a file unless the interface confirms it."
        )

        try:
            # Only send the history of the current chat
            payload = {
                "model": CHAT_MODEL,
                "messages": [{"role": "system", "content": system_prompt}, *active_chat["messages"]],
                "stream": True 
            }
            
            response = requests.post(
                "http://localhost:11434/api/chat", json=payload, stream=True, timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if 'message' in chunk:
                        content = chunk['message']['content']
                        full_response += content
                        response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)

        except Exception as e:
            st.error("Ollama connection error.")
            full_response = "I'm having trouble connecting to my local brain."

    # 3. Save assistant response and update file
    active_chat["messages"].append({"role": "assistant", "content": full_response})
    save_all_chats(st.session_state.all_chats)
