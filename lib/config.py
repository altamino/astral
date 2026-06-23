from os import environ


class Config:
    BOT_MAIL = environ["BOT_MAIL"]
    BOT_PSWD = environ["BOT_PSWD"]
    LOCAL_DB = environ["LOCAL_DB"]
    I18N_PATH = environ["I18N_PATH"]
