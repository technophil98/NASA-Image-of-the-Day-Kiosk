import argparse
import tkinter as tk
from PIL import ImageTk, Image
import requests
from io import BytesIO
import feedparser as fp
from colorthief import ColorThief
import colorsys


def center(toplevel):
    """
    Centers window on screen (https://stackoverflow.com/a/3353112)
    :param toplevel: The window to center
    """
    toplevel.update_idletasks()
    w = toplevel.winfo_screenwidth()
    h = toplevel.winfo_screenheight()
    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = w / 2 - size[0] / 2
    y = 0
    toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))


def palette_to_hex(palette):
    hex_palette = []
    for color in palette:

        hsv_color = list(colorsys.rgb_to_hsv(color[0], color[1], color[2]))
        hsv_color[1] = 0.8  # Exaggerate color saturation for LEDs
        corrected_rgb = colorsys.hsv_to_rgb(hsv_color[0], hsv_color[1], hsv_color[2])

        hex_color = ""
        for channel in corrected_rgb:
            hex_color += "{0:0{1}x}".format(int(channel), 2)
        hex_palette.append(hex_color)

    return tuple(hex_palette)


class NasaIOTDApp:
    def __init__(self, refresh_rate_minutes, wemos_address):
        self.wemos_address = wemos_address

        self.window = tk.Tk()
        self.window.title("Nasa Image of the Day")
        self.window.geometry("{0}x{1}+0+0".format(self.window.winfo_screenwidth(), self.window.winfo_screenheight()))
        self.window.configure(background='black')
        center(self.window)

        self.window.attributes("-fullscreen", True)

        self.feed = fp.parse("https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss")
        self.refresh_rate = refresh_rate_minutes * 60 * 1000
        self.current_url = ""

        self.image_raw = Image.open("default.jpg")
        self.image = ImageTk.PhotoImage(self.resize_image_for_frame(self.image_raw))
        self.image_label = tk.Label(self.window, image=self.image, background="black")
        self.image_label.image = self.image
        self.image_label.pack()

        self.update_image()

        # On window resize
        self.window.bind("<Configure>", self.on_resize)
        # On window exit
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    def update_image(self, with_leds=True):
        self.feed = fp.parse("https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss")

        image_url = self.get_image_url_from_feed()
        if self.current_url != image_url:
            # We have a new image!
            self.current_url = image_url

            self.image_raw = requests.get(self.current_url).content
            parsed_image = Image.open(BytesIO(self.image_raw))

            self.image = ImageTk.PhotoImage(self.resize_image_for_frame(parsed_image))

        self.image_label.configure(image=self.image)
        self.image_label.image = self.image
        self.image_label.pack()

        if with_leds:
            self.update_leds()

        self.window.after(self.refresh_rate, self.update_image)

    def get_image_url_from_feed(self):
        for link in self.feed.entries[0].links:
            if "image" in link.type:
                return self.feed.entries[0].links[1].href

    def resize_image_for_frame(self, image):
        image_size = image.size
        aspect_ratio = image_size[0] / image_size[1]

        image_new_height = self.window.winfo_height()
        image_new_width = image_new_height * aspect_ratio
        image_new_size = (int(image_new_width), image_new_height)
        return image.resize(image_new_size, Image.ANTIALIAS)

    def on_resize(self, _):
        self.update_image(False)

    def update_leds(self):
        color_thief = ColorThief(BytesIO(self.image_raw))
        # build a color palette
        palette = color_thief.get_palette(color_count=4)
        palette = palette_to_hex(palette)

        request_url = "http://" + self.wemos_address + "/pattern?params=" + ';'.join(palette)
        print(request_url)

        try:
            requests.get(request_url, timeout=5)
        except requests.ConnectTimeout:
            print("Connection to wemos failed")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()

    ap.add_argument("-r", "--refresh-rate",
                    required=False, type=int, help="Refresh rate of the image (minutes)", default=30)

    ap.add_argument("-a", "--wemos-address",
                    required=True, help="IP address of Wemos controller")

    args = vars(ap.parse_args())

    app = NasaIOTDApp(args["refresh_rate"], args["wemos_address"])

    # Loop the GUI
    app.window.mainloop()
