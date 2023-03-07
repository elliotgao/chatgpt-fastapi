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
    PING_HOST = 'www.sina.com.cn'

    """
    server message variables
    """
    UNKNOWN_RUNTIME_ERR_MSG = '【未知系统错误，请联系管理员】'
    UNKNOWN_NETWORK_ERR_MSG = '【遭遇未知网络波动，请重试】'
    ENTER_ROOM_MSG = '进入聊天室 当前人数'
    EXIT_ROOM_MSG = '退出聊天室   当前人数'
    EMPTY_INPUT_MSG = '【您的输入为空，请重新输入】'

    """
    client web variables
    """
    CHAT_ROOM_NAME = 'ChatGPT 多人聊天室'
    ENTER_ROOM_BUTTON = '进入房间'
    USER_NAME_HINT = '输入昵称'
    USER_NAME_TAKEN_ALERT = '用户名已占用，请更换'
    SHOW_ALL = '显示所有'
    SHOW_SELF = '仅显示自己'
    REALTIME_PANEL = '实时面板'
    CURRENT_USER = '当前用户'
    DISCONNECT_MSG = '\\n【您已与服务器断开，请尝试刷新页面，或重新登入】\\n'
    TEXT_INPUT_HINT = '输入聊天内容， 可以@chatgpt，shift+回车换行，刷新页面重置上下文'
    SEND_BUTTON = '发送'
    COPY_ALERT = '已复制到剪贴板'
