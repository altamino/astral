from dataclasses import dataclass
from httpx import get as download
from io import BytesIO
from uuid import uuid4
from PIL import Image
import zipfile
import json


@dataclass
class ThemeFile:
    path: str
    data: bytes


class ThemeEditor:
    """
    Modify .json to edit theme data.

    Call .new_image() to pass new image for theme.
    """

    def __init__(self, url: str):
        theme_raw = download(url).content
        theme_obj = BytesIO(theme_raw)

        self.info = None
        self.background = None
        self.titlebar = None
        self.icon = None
        self.titlebar_background = None

        # saving files
        with zipfile.ZipFile(theme_obj, "r") as zin:
            for item in zin.infolist():
                if item.is_dir():
                    continue

                filename = item.filename
                if filename.endswith("theme_info.json"):
                    self.info = ThemeFile(filename, zin.read(filename))
                    self.json = json.loads(zin.read(filename))
                elif filename.startswith("images/background/"):
                    self.background = ThemeFile(filename, zin.read(filename))
                elif filename.startswith("images/titlebarBackground/"):
                    self.titlebar_background = ThemeFile(filename, zin.read(filename))
                elif filename.startswith("images/titlebar/"):
                    self.titlebar = ThemeFile(filename, zin.read(filename))
                elif filename.startswith("images/logo/"):
                    self.icon = ThemeFile(filename, zin.read(filename))

        # resetting defaults
        self.json["author"] = "Astral"
        if self.json["id"] == "oled-black-theme":
            self.json["id"] = str(uuid4())

    def _get_image_size(self, img_bytes: bytes):
        return Image.open(BytesIO(img_bytes)).size

    def rebuild(self) -> BytesIO:
        theme_obj = BytesIO()
        self.info.data = json.dumps(self.json, ensure_ascii=False).encode()
        with zipfile.ZipFile(theme_obj, "w") as zout:
            for file in [
                self.info,
                self.background,
                self.titlebar,
                self.icon,
                self.titlebar_background,
            ]:
                if file:
                    zout.writestr(file.path, file.data)

        theme_obj.seek(0)
        return theme_obj

    def new_image(self, for_what: str, url: str):
        """
        - icon/logo is "community name Amino" image
        - titlebar is image that you see at the top when entering community
        - titlebar-background is leftpanel bg
        - background is ...

        i confused
        """
        mapper = {
            "icon": self.icon,
            "logo": self.icon,
            "titlebar": self.titlebar,
            "tbar": self.titlebar,
            "tb": self.titlebar,
            "titlebarbackground": self.titlebar,
            "titlebarbg": self.titlebar_background,
            "tbarbg": self.titlebar_background,
            "tbbg": self.titlebar_background,
            "bg": self.background,
            "background": self.background,
        }
        mapped: ThemeFile = mapper[for_what]
        if not mapped:
            raise Exception("invalid for_what parameter!!")

        new_path = mapped.path.rsplit("/", 1)[0] + "/" + url.rsplit("/", 1)[-1]
        new_image_data = download(url).content
        width, height = self._get_image_size(new_image_data)
        if for_what in ["icon", "logo"]:
            if width != height:
                raise Exception("logo should be squard")
            self.logo = ThemeFile(new_path, new_image_data)
            self.json["logo"][0]["path"] = new_path
            self.json["logo"][0]["width"] = width
            self.json["logo"][0]["height"] = height

        elif for_what in ["titlebar", "tb", "tbar"]:
            self.titlebar = ThemeFile(new_path, new_image_data)
            self.json["titlebar-background-image"][0]["path"] = new_path
            self.json["titlebar-background-image"][0]["width"] = width
            self.json["titlebar-background-image"][0]["height"] = height

        elif for_what in ["background", "bg", "leftpanel"]:
            self.background = ThemeFile(new_path, new_image_data)
            self.json["background-image"][0]["path"] = new_path
            self.json["background-image"][0]["width"] = width
            self.json["background-image"][0]["height"] = height
