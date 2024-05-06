#!/bin/bash

# Имя сессии tmux (можно изменить на ваше предпочтение)
SESSION_NAME="bbc-bot"

# Путь к файлу server.js
SERVER_JS_PATH="./server.js"

# Название окна tmux (можно изменить на ваше предпочтение)
WINDOW_NAME="bbc-window"

# Проверяем, существует ли сессия tmux
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  # Если сессия не существует, создаем ее
  tmux new-session -d -s "$SESSION_NAME" -n "$WINDOW_NAME"
fi

# Переходим в сессию и окно tmux
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" "node $SERVER_JS_PATH" C-m

# Переключаемся в сессию tmux
tmux attach-session -t "$SESSION_NAME"

