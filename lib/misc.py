from requests import get as get_request
from PIL import Image, ImageFont, ImageDraw, ImageMath
import os
from datetime import timedelta, datetime as dt

class Misc():
    def save_image_from_URL(self, track_image_link, fileName):
        if not os.path.exists("album_art"):
            os.makedirs("album_art")
        img_data = get_request(track_image_link).content
        with open(f"album_art/{fileName}", 'wb') as handler:
            handler.write(img_data)

    def resize_image(self, imageName):
        if not os.path.exists("album_art"):
            os.makedirs("album_art")
        size = 199, 199
        outfile = os.path.splitext(imageName)[0] + "_resize.PNG"
        if imageName != outfile:
            try:
                im = Image.open(f"album_art/{imageName}")
                im.thumbnail(size)
                im.save(f"album_art/{outfile}", "PNG")
            except IOError:
                print ("cannot create thumbnail for '%s'" % imageName)

    def has_sun_set(self, sunset_info, sunset_flip):
        date = dt.now()
        c_hour = int(date.strftime("%-H"))
        c_minute = int(date.strftime("%-M"))
        sun_h, sun_m = sunset_info
        return sunset_flip and ((sun_h < c_hour or c_hour < 2) or (sun_h == c_hour and sun_m <= c_minute))

    def get_album_art(self, track_image_link, album_image_name="AlbumImage.PNG"):
        new_image_name = album_image_name.split('.')[0] + "_resize.PNG"
        self.save_image_from_URL(track_image_link, album_image_name)
        self.resize_image(album_image_name)