import re


class Args:
    """
    path variables
    """
    CACHE_DIR: str = './cache'
    REDIS_PATH: str = './cache/redis/redis.db'
    REDIS_MSG_QUEUE: str = 'msg_queue'
    PROMPTS_DIR: str = './prompts/prompts_zh'

    """
    chatgpt variables
    """
    ENV_API_KEY: str = 'OPENAI_API_KEY'
    ENV_ORG_ID: str = 'OPENAI_ORG_ID'
    DEBUG_KEY: str = 'CHATGPT_CHATROOM_SERVER_DEBUG'
    CHATGPT_WAKING_PATTERN = re.compile(r'@chatgpt', re.IGNORECASE)
    CHATGPT_TEXT_COLOR = '#DE3163'

    """
    other variables
    """
    PING_HOST = 'www.google.com'

    """
    server message variables
    """
    UNKNOWN_RUNTIME_ERR_MSG = '【unknown system error, contact admin】'
    UNKNOWN_NETWORK_ERR_MSG = '【unknown network error, please try again】'
    ENTER_ROOM_MSG = 'joined    online'
    EXIT_ROOM_MSG = 'exited    online'
    EMPTY_INPUT_MSG = '【your message was empty】'

    """
    client web variables
    """
    CHAT_ROOM_NAME = 'ChatGPT Multi-Person Chatroom'
    ENTER_ROOM_BUTTON = 'Enter'
    USER_NAME_HINT = 'input your nick name'
    USER_NAME_TAKEN_ALERT = 'nick name taken!'
    SHOW_ALL = 'show all'
    SHOW_SELF = 'myself only'
    REALTIME_PANEL = 'Realtime Panel'
    CURRENT_USER = 'user'
    DISCONNECT_MSG = '\\n【you are disconnected, please refresh the page】\\n'
    TEXT_INPUT_HINT = 'enter text, @chatgpt, Shift + Enter for line break, refresh page for resetting context'
    SEND_BUTTON = 'send'
    COPY_ALERT = 'copied'
