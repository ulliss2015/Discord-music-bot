#!/bin/bash

# tmux session name 
SESSION_NAME="discord-music-bot"

# Путь к файлу 
BOT_PATH="source ~/Discord-music-bot/.venv/bin/activate && python3 ~/Discord-music-bot/bot_main.py"

# tmux window name
WINDOW_NAME="discord-music-bot"

# check if session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # if it doesn't exist create it
    tmux new-session -d -s "$SESSION_NAME" -n "$WINDOW_NAME" bash
fi

# go to session and window tmux 
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" "$BOT_PATH" C-m

# attach to session
# tmux attach-session -t "$SESSION_NAME"