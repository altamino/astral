import functools
import traceback
from json import dumps
from re import match
from time import time

from aminofixfix import Client, SubClient
from aminofixfix.lib.exceptions import InvalidSession
from aminofixfix.lib.objects import Event, FromCode

from .config import Config
from .database import UserManager
from .i18n import i18n


def valid_color(arg: str):
    return bool(match(r"^#[0-9a-fA-F]{6}$", arg))


def timestamp() -> int:
    return int(time() * 1000)


def edit_community(app: Client | SubClient, ndcId: int, data: dict):
    data = dumps(data | {"timestamp": timestamp()})
    response = app.session.post(
        f"/altacm/s/community/x{ndcId}/edit",
        data=data,
        headers=app.additional_headers(data=data),
    )
    if response.status_code != 200:
        print(f"edit_community failed!: {response.content}")
        raise Exception(response.content)


def promotion(app: Client | SubClient, ndcId: int, userId: str, role: int):
    data = dumps({"role": role, "timestamp": timestamp()})
    response = app.session.post(
        f"/altacm/s/community/x{ndcId}/user/{userId}/promote",
        data=data,
        headers=app.additional_headers(data=data),
    )
    if response.status_code != 200:
        print(f"promotion failed!: {response.content}")
        raise Exception(response.content)


def link_resolution(app: Client | SubClient, ndcId: int, code: str):
    response = app.session.get(
        f"/x{ndcId}/s/link-resolution?q={code}", headers=app.additional_headers()
    )
    if response.status_code != 200:
        print(f"link_resolution failed!: {response.content}")
        return Exception(response)
    else:
        return FromCode(response.json()["linkInfoV2"]).FromCode


def demotion(app: Client | SubClient, ndcId: int, userId: str):
    response = app.session.delete(
        f"/altacm/s/community/x{ndcId}/user/{userId}/promote",
        headers=app.additional_headers(),
    )
    if response.status_code != 200:
        print(f"promotion failed!: {response.content}")
        raise Exception(response.content)


def is_admin(app: Client | SubClient, userId: str):
    user = app.get_user_info(userId)
    return user.role in [100, 102, 200, 201, 254, 555]


def exception_handler(client: Client):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(data: Event, *args, **kwargs):
            try:
                return func(data, *args, **kwargs)
            except InvalidSession:
                print("Session died. Probably its because of reinited cache server.")
                try:
                    client.login(Config.BOT_MAIL, Config.BOT_PSWD)
                    print("Session restored..")
                except Exception:
                    print(
                        "And now we have invalid credentials or dead server/endpoint. Great. "
                    )
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                traceback.print_exc()
                try:
                    ndcId = data.comId
                    messageId = data.message.messageId
                    threadId = data.message.chatId
                    authorId = data.message.author.userId

                    app = (
                        SubClient(socket_enabled=False, mainClient=client, comId=ndcId)
                        if ndcId > 0
                        else client
                    )
                    users = UserManager()
                    authorData = users.get(authorId)
                    lang = authorData.lang

                    app.send_message(
                        threadId, i18n.get("errors.default", lang), replyTo=messageId
                    )
                except Exception:
                    print("Can't tell about exception to user. Sorry mate!")

        return wrapper

    return decorator
