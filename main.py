from os import environ
from threading import Thread
from time import sleep

from aminofixfix import Client, SubClient
from aminofixfix.lib.objects import Event, Message

from lib.database import UserManager
from lib.functions import (
    demotion,
    edit_community,
    exception_handler,
    is_admin,
    link_resolution,
    promotion,
    valid_color,
)
from lib.i18n import i18n
from lib.theme_editor import ThemeEditor

client = Client(
    socket_url="wss://ws1.altamino.top",
    api_url="https://dev-service.altamino.top/api/v1",
)

# since sessions are not so stable!
relogin_timeout = 3600
relogin_hitted_timeout = 60


def relogin_thread():
    global relogin_timeout, relogin_hitted_timeout
    global client

    hit_happened = False
    while True:
        try:
            client.logout()
        except Exception:
            print("Can't logout for some reason.")

        try:
            client.login(email=environ["BOT_MAIL"], password=environ["BOT_PSWD"])
            print("Relogined!")
            hit_happened = False
        except Exception as e:
            print(f"Can't relogin! Reason: {e}")
            hit_happened = True

        if hit_happened:
            sleep(relogin_hitted_timeout)
            continue

        sleep(relogin_timeout)


@client.event("on_text_message")
@exception_handler(client)
def on_text_message(data: Event):
    ndcId = data.comId
    messageId = data.message.messageId
    threadId = data.message.chatId
    content = data.message.content
    authorId = data.message.author.userId

    app: Client | SubClient = (
        SubClient(socket_enabled=False, mainClient=client, comId=ndcId)
        if ndcId > 0
        else client
    )
    if app.profile.userId == authorId:
        return

    command, _, args = content.partition(" ")
    if not command.startswith("/"):
        return

    users = UserManager()
    authorData = users.get(authorId)
    lang = authorData.lang

    if command == "/start":
        app.join_chat(threadId)
        app.send_message(threadId, i18n.get("start", lang), replyTo=messageId)
    elif command == "/help":
        app.send_message(threadId, i18n.get("help", lang), replyTo=messageId)
    elif command == "/promotion":
        link, _, role = args.partition(" ")
        resolved = link_resolution(app, ndcId, link.strip())
        if resolved.objectId == authorId:
            return

        # process a role

        promotion(app, ndcId, resolved.objectId, role)
        app.send_message(threadId, i18n.get("promotion", lang), replyTo=messageId)
    elif command == "/demotion":
        resolved = link_resolution(app, ndcId, args.strip())
        if resolved.objectId == authorId:
            return
        demotion(app, ndcId, resolved.objectId, role)
        app.send_message(threadId, i18n.get("demotion", lang), replyTo=messageId)
    elif command[:4] == "/set":
        mapper = {
            "name": "name",
            "slogan": "tagline",
            "tagline": "tagline",
            "aminoid": "aminoId",
            "aid": "aminoId",
            "tag": "aminoId",
            "desc": "description",
            "guidelines": "guidelines",
            "guide": "guidelines",
            "rules": "guidelines",
            "rulez": "guidelines",
            "icon": "theme.icon",
            "logo": "theme.logo",
            "leftpanel": "theme.titlebar-background",
            "titlebar": "theme.titlebar",
            "tbar": "theme.titlebar",
            "tb": "theme.titlebar",
            "lpanel": "theme.titlebar-background",
            "background": "theme.background",
            "bg": "theme.background",
            "cover": "theme.cover",
            "color": "theme.color",
        }
        action = command[4:]
        mapped_action = mapper.get(action)
        if mapped_action is None:
            return app.send_message(
                threadId, i18n.get("errors.no-args", lang), replyTo=messageId
            )

        if not is_admin(app, authorId):
            return app.send_message(
                threadId,
                i18n.get("errors.not-enough-rights", lang),
                replyTo=messageId,
            )

        additional = {}
        rm_content, rm_mediaUrl = None, None
        reply_message = Message(data.message.replyMessage).Message
        if reply_message:
            rm_content = reply_message.content
            if reply_message.mediaValue and reply_message.mediaType == 100:
                rm_mediaUrl = reply_message.mediaValue

        if mapped_action.startswith("theme"):
            mapped_action, change = mapped_action.split(".")

            theme_url = client.get_community_info(ndcId).themeUrl
            editor = ThemeEditor(theme_url)
            editor.json["revision"] += 1
            additional.update({"themeRevision": editor.json["revision"]})

            if change == "color" and valid_color(args.strip()):
                additional.update({"themeColor": args.strip()})
                editor.json["theme-color"] = args.strip()
            else:
                if rm_mediaUrl is None:
                    return app.send_message(
                        threadId,
                        i18n.get("errors.no-image-args", lang),
                        replyTo=messageId,
                    )

                if change == "icon":
                    additional.update({"icon": rm_mediaUrl})
                elif change == "logo":
                    editor.new_image("logo", rm_mediaUrl)
                elif change == "background":
                    editor.new_image("background", rm_mediaUrl)
                elif change == "titlebar":
                    editor.new_image("titlebar", rm_mediaUrl)
                elif change == "titlebar-background":
                    editor.new_image("titlebarbg", rm_mediaUrl)
                elif change == "cover":
                    additional.update({"coverUrl": rm_mediaUrl})
                else:
                    return app.send_message(
                        threadId, i18n.get("errors.no-args", lang), replyTo=messageId
                    )

            new_theme = editor.rebuild()
            args = app.upload_media(new_theme, "theme", ndcId=ndcId)

        replic = i18n.get(f"set.{mapped_action}", lang)
        if mapped_action in ["guidelines", "description"]:
            if isinstance(rm_content, str) and len(rm_content.strip()) > 0:
                args = rm_content
            else:
                replic += "\n\n" + i18n.get("info.use-reply-msg", lang)

        # I don't really feel like reuse mapped_action
        if mapped_action == "theme":
            data = {"themeUrl": args.strip()} | additional
        else:
            data = {mapped_action: args.strip()} | additional

        edit_community(app, ndcId, data)
        app.send_message(threadId, replic, replyTo=messageId)
    elif command == "/sub":
        app.follow(authorId)
        app.send_message(threadId, i18n.get("sub", lang), replyTo=messageId)
    elif command == "/botlang":
        if args.lower() in ["ru", "en"]:
            users.update(authorId, lang=args.lower())
            authorData = users.get(authorId)
            lang = authorData.lang

        app.send_message(threadId, i18n.get("botlang", lang), replyTo=messageId)
    elif command == "/invite":
        if not args.strip():
            app.send_message(
                threadId, i18n.get("errors.no-args", lang), replyTo=messageId
            )

        found = client.search_community(args.strip())
        app.join_community(found.comId[0])
        app.send_message(threadId, i18n.get("invite", lang), replyTo=messageId)


if __name__ == "__main__":
    # client.login(email=environ["BOT_MAIL"], password=environ["BOT_PSWD"])
    Thread(target=relogin_thread).start()
    print("Started!")
