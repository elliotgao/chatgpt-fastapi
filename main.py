import os
import re
import builtins
from functools import partial
import traceback
import pickle
import time
from datetime import datetime
from typing import List, Dict, Union
import json

import threading
import redislite
from redislite.client import Redis
from redis.exceptions import ConnectionError
import asyncio

from pydantic import BaseModel
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response
)
from starlette.websockets import WebSocketState
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from chatgpt_api import time_now_str
from colorama import Fore, Style

from config.config_en import Args
# from config.config_zh import Args


builtins.print = partial(print, flush=True)


def time_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class SocketManager:
    def __init__(self):
        self.active_connections: Dict[str: List[WebSocket]] = {}

    async def connect(self, *, user: str, websocket: WebSocket) -> bool:
        await websocket.accept()
        status = True
        other_websocket = None
        if user in self.active_connections:
            other_websocket = self.active_connections[user]
            status = False
        self.active_connections[user] = websocket
        if other_websocket is not None:
            await other_websocket.close()
        return status

    async def disconnect(self, *, user: str, websocket: WebSocket) -> bool:
        if user in self.active_connections:
            _websocket: WebSocket = self.active_connections[user]
            if websocket == _websocket:
                cond1 = websocket.application_state != WebSocketState.DISCONNECTED
                cond2 = websocket.client_state != WebSocketState.DISCONNECTED
                if cond1 and cond2:
                    await websocket.close()
                del self.active_connections[user]
                return True
        return False

    async def broadcast(self, data: dict):
        for user, connection in self.active_connections.items():
            await connection.send_json(data)


def create_response(
        message: str = "",
        *,
        time_str: str = "",
        sender: str = "",
        receiver: str = "",
        italic: bool = False,
        strong: bool = False,
        color: str = "",
        complete: bool = True,
):
    response = {
        "time_str": time_str,
        "sender": sender,
        "receiver": receiver,
        "message": message,
        "italic": italic,
        "strong": strong,
        "color": color,
        "complete": complete,
    }
    return response


"""
path variables
"""
CACHE_DIR: str = Args.CACHE_DIR
REDIS_PATH: str = Args.REDIS_PATH
REDIS_MSG_QUEUE: str = Args.REDIS_MSG_QUEUE
PROMPTS_DIR: str = Args.PROMPTS_DIR

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.join(CACHE_DIR, 'log'), exist_ok=True)    # TODO: logging not implemented yet
os.makedirs(os.path.join(CACHE_DIR, 'redis'), exist_ok=True)
os.makedirs(os.path.dirname(REDIS_PATH), exist_ok=True)
redis: Redis = redislite.Redis(REDIS_PATH)


"""
chatgpt variables
"""
ENV_API_KEY: str = Args.ENV_API_KEY
ENV_ORG_ID: str = Args.ENV_ORG_ID
DEBUG_KEY: str = Args.DEBUG_KEY
CHATGPT_WAKING_PATTERN = Args.CHATGPT_WAKING_PATTERN
CHATGPT_TEXT_COLOR = Args.CHATGPT_TEXT_COLOR

if DEBUG_KEY in os.environ and str(os.environ[DEBUG_KEY]).lower() in ['1', 'true']:
    API_KEY: str = ''
    API_ORG: str = ''
    CHATGPT_DEBUG_MODE = True
else:
    for var_key in [ENV_API_KEY, ENV_ORG_ID]:
        if var_key not in os.environ:
            raise ValueError(f'{Fore.RED}environmental variable "{var_key}" not provided{Style.RESET_ALL}')
    API_KEY = str(os.environ[ENV_API_KEY])
    API_ORG = str(os.environ[ENV_ORG_ID])
    CHATGPT_DEBUG_MODE: bool = False
user_context_dict: Dict[str, Union[None, List]] = {}

"""
other variables
"""
PING_HOST = Args.PING_HOST

"""
server message variables
"""
UNKNOWN_RUNTIME_ERR_MSG = Args.UNKNOWN_RUNTIME_ERR_MSG
UNKNOWN_NETWORK_ERR_MSG = Args.UNKNOWN_NETWORK_ERR_MSG
ENTER_ROOM_MSG = Args.ENTER_ROOM_MSG
EXIT_ROOM_MSG = Args.EXIT_ROOM_MSG
EMPTY_INPUT_MSG = Args.EMPTY_INPUT_MSG

"""
client web variables
"""
CHAT_ROOM_NAME = Args.CHAT_ROOM_NAME
ENTER_ROOM_BUTTON = Args.ENTER_ROOM_BUTTON
USER_NAME_HINT = Args.USER_NAME_HINT
USER_NAME_TAKEN_ALERT = Args.USER_NAME_TAKEN_ALERT
SHOW_ALL = Args.SHOW_ALL
SHOW_SELF = Args.SHOW_SELF
REALTIME_PANEL = Args.REALTIME_PANEL
CURRENT_USER = Args.CURRENT_USER
DISCONNECT_MSG = Args.DISCONNECT_MSG
TEXT_INPUT_HINT = Args.TEXT_INPUT_HINT
SEND_BUTTON = Args.SEND_BUTTON
COPY_ALERT = Args.COPY_ALERT


"""
fastapi variables
"""
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
websocket_manager = SocketManager()   # websocket manager


@app.get("/")
def get_home(request: Request):
    param = {
        "request": request,
        "roomName": CHAT_ROOM_NAME,
        "enterRoomButton": ENTER_ROOM_BUTTON,
        "userNameHint": USER_NAME_HINT,
        "userNameTaken": USER_NAME_TAKEN_ALERT,
    }
    return templates.TemplateResponse("home.html", param)


@app.get("/chat")
def get_chat(request: Request):
    param = {
        "request": request,
        "roomName": CHAT_ROOM_NAME,
        "showAll": SHOW_ALL,
        "showSelf": SHOW_SELF,
        "chatgptColor": CHATGPT_TEXT_COLOR,
        "realtimePanel": REALTIME_PANEL,
        "currentUser": CURRENT_USER,
        "disconnectMsg": DISCONNECT_MSG,
        "textHint": TEXT_INPUT_HINT,
        "sendButton": SEND_BUTTON,
        "copyAlert": COPY_ALERT,
    }
    return templates.TemplateResponse("chat.html", param)


@app.get("/api/current_user")
def get_user(request: Request):
    uname = ''

    # noinspection PyBroadException
    try:
        uname = json.loads(request.cookies.get("X-Authorization"))
    except Exception:
        print('fail to decode uname from X-Authorization...')
    return uname


class RegisterValidator(BaseModel):
    username: str

    class Config:
        orm_mode = True


@app.post("/api/register")
def register_user(user: RegisterValidator, response: Response):
    uname = user.username
    if uname in user_context_dict or uname.lower() == 'chatgpt':
        return {'status': False}

    uname = json.dumps(uname)
    response.set_cookie(key="X-Authorization", value=uname, httponly=True)
    return {'status': True}


@app.websocket("/api/chat")
async def chat(websocket: WebSocket):
    uname = websocket.cookies.get("X-Authorization")

    if uname:
        uname = json.loads(uname)
        status = await websocket_manager.connect(user=uname, websocket=websocket)
        if status:
            user_context_dict[uname] = None
            enter_room_txt = f"{uname} {ENTER_ROOM_MSG} {len(user_context_dict)}"
            response = create_response(enter_room_txt, italic=True)
            print(f"[{time_now()}] {enter_room_txt}")
            print('users:', set(user_context_dict.keys()))
            await websocket_manager.broadcast(response)
        try:
            while True:
                data = await websocket.receive_json()
                _response = create_response(
                    time_str=f"{time_now()}",
                    sender=f"{uname}",
                    message=f"{data['message']}",
                )
                await websocket_manager.broadcast(_response)
                redis.lpush(
                    REDIS_MSG_QUEUE,
                    pickle.dumps(
                        {
                            'sender': uname,
                            'message': data['message'],
                        }
                    )
                )
        except WebSocketDisconnect:
            pass
        finally:
            status = await websocket_manager.disconnect(user=uname, websocket=websocket)
            if status:
                # remove user context
                if uname in user_context_dict:
                    del user_context_dict[uname]

                # noinspection PyBroadException
                try:
                    leave_room_txt = f"{uname} {EXIT_ROOM_MSG} {len(user_context_dict)}"
                    response = create_response(leave_room_txt, italic=True)
                    print(f"[{time_now()}] {leave_room_txt}")
                    print('users:', set(user_context_dict.keys()))
                    await websocket_manager.broadcast(response)
                except Exception:
                    pass


class ChatGPTThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.uname = 'ChatGPT'
        super().__init__(target=self.main, *args, **kwargs)

    @staticmethod
    def launch_chatgpt():
        # noinspection PyBroadException
        try:
            if not CHATGPT_DEBUG_MODE:
                from chatgpt_api import ChatGPT
            else:
                from chatgpt_api import ChatGPTDebug as ChatGPT

            chatgpt = ChatGPT(
                api_key=API_KEY,
                api_org=API_ORG,
                prompts_dir=PROMPTS_DIR,
                network_err_text=UNKNOWN_NETWORK_ERR_MSG,
            )

            print(f'chatgpt launched')
            print(f'--------------------------\n')
            return chatgpt
        except Exception:
            traceback.print_exc()
            raise ValueError(f"{Fore.RED}check env OPENAI_API_KEY and OPENAI_ORG_ID{Style.RESET_ALL}")

    @staticmethod
    def is_asking_for_response(text: str):
        res = re.findall(re.compile(r'@chatgpt', re.IGNORECASE), text)
        return len(res) > 0

    def process_data(self, data: dict):
        # noinspection PyBroadException
        try:
            sender: str = data['sender']
            text: str = data['message']
            asking_for_response = self.is_asking_for_response(text=text)
            if asking_for_response:
                text = re.sub(CHATGPT_WAKING_PATTERN, '', text).strip()
        except Exception:
            sender: str = ''
            text: str = ''
            asking_for_response: bool = False
        return sender, text, asking_for_response

    async def alert_empty_input(self, receiver: str):
        response = create_response(f"{EMPTY_INPUT_MSG}",
                                   time_str=f"{time_now()}",
                                   sender=f"{self.uname}",
                                   receiver=f"{receiver}",
                                   color=CHATGPT_TEXT_COLOR)
        await websocket_manager.broadcast(response)

    @staticmethod
    def get_user_context(*, chatgpt, user: str):
        context = user_context_dict[user] if user in user_context_dict else None
        if context is None:
            context = [
                {'role': 'system', 'content': chatgpt.get_prompt('chat-agent.txt')},
                {'role': 'system', 'content': f'user: {user}'},
            ]
        return context

    async def broadcast_head_lines(self, receiver: str, text: str):
        query_summary_html = f"[Q]\n{text[:17]}...\n\n[A]\n"
        response = create_response(
            query_summary_html,
            time_str=f"{time_now()}",
            sender=f"{self.uname}",
            receiver=f"{receiver}",
            color=CHATGPT_TEXT_COLOR,
            complete=False
        )
        await websocket_manager.broadcast(response)

    @staticmethod
    def text_to_html(text: str):
        return text

    @staticmethod
    def text_to_prompt(text: str):
        return text

    async def broadcast_stream_body(self, *, chatgpt, receiver: str, text: str, context: List, verbose: bool = True):
        prompt: str = self.text_to_prompt(text)
        full_content: str = ''

        if verbose:
            print(f"[{time_now_str()}] {self.uname} >> {receiver}")
        iterator = chatgpt.send_message(text=prompt, context=context, stream=True)
        for content, status, context, full_content in iterator:
            response = create_response(f"{content}", complete=False)
            if verbose:
                print(content, end='')
            await websocket_manager.broadcast(response)
            user_context_dict[receiver] = context
        if verbose:
            print()

        response = create_response(f"{self.text_to_html(full_content)}",
                                   time_str=f"{time_now()}",
                                   sender=f"{self.uname}",
                                   receiver=f"{receiver}",
                                   color=CHATGPT_TEXT_COLOR,
                                   complete=True)
        await websocket_manager.broadcast(response)

    async def chatgpt_main(self):
        chatgpt = self.launch_chatgpt()
        response = create_response(f"{self.uname} {ENTER_ROOM_MSG} ", italic=True, color=CHATGPT_TEXT_COLOR)
        await websocket_manager.broadcast(response)

        # noinspection PyBroadException
        try:
            while True:
                # noinspection PyBroadException
                try:
                    queue_pop = redis.brpop(REDIS_MSG_QUEUE, timeout=1.)
                    if queue_pop is None:
                        continue

                    ''' process input data '''
                    data: dict = pickle.loads(queue_pop[1])
                    sender, text, asking_for_response = self.process_data(data)
                    if not asking_for_response:
                        continue
                    if len(text) == 0:
                        await self.alert_empty_input(receiver=sender)
                        continue

                    ''' call ChatGPT API '''
                    print(f'[{time_now_str()}] {sender}')
                    print(text)
                    context: List[Dict] = self.get_user_context(chatgpt=chatgpt, user=sender)
                    await self.broadcast_head_lines(receiver=sender, text=text)
                    await self.broadcast_stream_body(
                        chatgpt=chatgpt, receiver=sender, text=text, context=context, verbose=True)
                    n_tokens_list = chatgpt.count_context_tokens(user_context_dict[sender])
                    print(f'[context size]: {n_tokens_list} -> total {sum(n_tokens_list)}')
                    print()
                    # await asyncio.sleep(1.)

                except ConnectionError:
                    break
                except ValueError:
                    break
                except KeyboardInterrupt:
                    break
                except Exception:
                    traceback.print_exc()
                    response = create_response(f"{UNKNOWN_RUNTIME_ERR_MSG}",
                                               time_str=f"{time_now()}",
                                               sender=f"{self.uname}",
                                               color=f"{CHATGPT_TEXT_COLOR}")
                    await websocket_manager.broadcast(response)
        except Exception:
            traceback.print_exc()
        finally:
            pass

    def main(self):
        asyncio.run(self.chatgpt_main())


chatgpt_thread = ChatGPTThread()
chatgpt_thread.setDaemon(True)
chatgpt_thread.start()


def keep_network_alive(cooldown: int = 55):
    while True:
        _ = os.popen(f"ping {PING_HOST} -c 3").read()
        for i in range(cooldown):
            time.sleep(1)


network_alive_thread = threading.Thread(target=keep_network_alive)
network_alive_thread.setDaemon(True)
network_alive_thread.start()
