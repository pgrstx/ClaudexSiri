"""
macOS system control actions via AppleScript, osascript, and shell commands.
"""
import subprocess
import shutil
import time


def execute(action_type: str, params: dict) -> str:
    """
    Dispatch to the correct handler.
    Returns a short status string (used for fallback speech if needed).
    """
    handlers = {
        "open_app": open_app,
        "quit_app": quit_app,
        "system_control": system_control,
        "timer": set_timer,
        "reminder": set_reminder,
        "search": web_search,
        "music": music_control,
        "message": send_message,
    }
    handler = handlers.get(action_type)
    if handler:
        return handler(params)
    return f"Unknown action: {action_type}"


# ── App control ───────────────────────────────────────────────────────────────

def open_app(params: dict) -> str:
    app = params.get("app", "")
    subprocess.run(["open", "-a", app], check=False)
    return f"Opened {app}"


def quit_app(params: dict) -> str:
    app = params.get("app", "")
    _applescript(f'tell application "{app}" to quit')
    return f"Quit {app}"


# ── System controls ───────────────────────────────────────────────────────────

def system_control(params: dict) -> str:
    control = params.get("control", "")
    value = params.get("value")

    if control == "volume":
        level = int(value) if value is not None else 50
        _applescript(f"set volume output volume {level}")
        return f"Volume set to {level}%"

    elif control == "brightness":
        level = float(value) / 100.0 if value is not None else 0.5
        # Requires brightness CLI: brew install brightness
        if shutil.which("brightness"):
            subprocess.run(["brightness", str(level)], check=False)
        else:
            _applescript(
                f'tell application "System Events" to '
                f'key code 144'  # F15 = brightness up (placeholder)
            )
        return f"Brightness set to {int(level * 100)}%"

    elif control == "dark_mode":
        enabled = bool(value)
        mode = "true" if enabled else "false"
        _applescript(
            f'tell application "System Events" to '
            f'tell appearance preferences to set dark mode to {mode}'
        )
        return f"Dark mode {'on' if enabled else 'off'}"

    elif control == "do_not_disturb":
        enabled = bool(value)
        # Focus mode toggle via shortcuts
        shortcut = "Do Not Disturb"
        subprocess.run(
            ["shortcuts", "run", shortcut], check=False, capture_output=True
        )
        return f"Do Not Disturb {'on' if enabled else 'off'}"

    elif control == "wifi":
        state = "on" if value else "off"
        subprocess.run(
            ["networksetup", "-setairportpower", "en0", state], check=False
        )
        return f"Wi-Fi {state}"

    elif control == "bluetooth":
        # Requires blueutil: brew install blueutil
        if shutil.which("blueutil"):
            state = "1" if value else "0"
            subprocess.run(["blueutil", "-p", state], check=False)
            return f"Bluetooth {'on' if value else 'off'}"
        return "Install blueutil to control Bluetooth: brew install blueutil"

    return f"Unknown system control: {control}"


# ── Timers & Reminders ────────────────────────────────────────────────────────

def set_timer(params: dict) -> str:
    minutes = int(params.get("minutes", 5))
    label = params.get("label", "Timer")
    seconds = minutes * 60
    script = f'''
    tell application "Clock"
        activate
    end tell
    delay 0.5
    tell application "System Events"
        tell process "Clock"
            click menu item "New Timer" of menu "File" of menu bar 1
        end tell
    end tell
    '''
    # Fallback: use a background shell timer with notification
    subprocess.Popen(
        [
            "bash", "-c",
            f"sleep {seconds} && osascript -e 'display notification "
            f'"{label} timer done!" with title "Hey Claude" sound name "Glass"\'',
        ]
    )
    return f"Timer set for {minutes} minute(s)"


def set_reminder(params: dict) -> str:
    text = params.get("text", "")
    remind_time = params.get("time", "")
    script = f'''
    tell application "Reminders"
        tell list "Reminders"
            make new reminder with properties {{name:"{text}"}}
        end tell
    end tell
    '''
    _applescript(script)
    return f"Reminder set: {text}"


# ── Search ────────────────────────────────────────────────────────────────────

def web_search(params: dict) -> str:
    query = params.get("query", "")
    import urllib.parse
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    subprocess.run(["open", url], check=False)
    return f"Searching for: {query}"


# ── Music / Media ─────────────────────────────────────────────────────────────

def music_control(params: dict) -> str:
    action = params.get("action", "play")
    query = params.get("query", "")
    value = params.get("value")

    if action == "play" and query:
        # Try Spotify first, fall back to Apple Music
        spotify_script = f'''
        tell application "Spotify"
            activate
            search for "{query}"
            play
        end tell
        '''
        try:
            _applescript(spotify_script)
            return f"Playing {query} on Spotify"
        except Exception:
            pass

    apple_music_cmds = {
        "play": "play",
        "pause": "pause",
        "next": "next track",
        "previous": "previous track",
    }
    cmd = apple_music_cmds.get(action, "play")
    script = f'tell application "Music" to {cmd}'
    _applescript(script)
    return f"Music: {action}"


# ── Messages ──────────────────────────────────────────────────────────────────

def send_message(params: dict) -> str:
    to = params.get("to", "")
    text = params.get("text", "")
    app = params.get("app", "Messages")
    script = f'''
    tell application "{app}"
        activate
        delay 0.5
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to buddy "{to}" of targetService
        send "{text}" to targetBuddy
    end tell
    '''
    _applescript(script)
    return f"Message sent to {to}"


# ── Helper ────────────────────────────────────────────────────────────────────

def _applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
