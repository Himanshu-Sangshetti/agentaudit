setopt interactivecomments
export AGENTAUDIT_CACHE=$(mktemp -d)
agentaudit() { uv run --quiet agentaudit "$@"; }
PROMPT='%F{183}❯%f '
clear
