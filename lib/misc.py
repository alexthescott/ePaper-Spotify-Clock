from requests import get as get_request
from PIL import Image, ImageFont, ImageDraw, ImageMath
import os
from datetime import datetime as dt

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
                im = im.convert("L")
                im.save(f"album_art/{outfile}", "PNG", mode="L")
            except IOError:
                print ("cannot create thumbnail for '%s'" % imageName)

    def has_sun_set(self, sunset_info, sunset_flip):
        date = dt.now()
        c_hour = int(date.strftime("%-H"))
        c_minute = int(date.strftime("%-M"))
        sun_h, sun_m = sunset_info
        return sunset_flip and ((sun_h < c_hour or c_hour < 2) or (sun_h == c_hour and sun_m <= c_minute))

    def get_album_art(self, track_image_link, album_image_name="AlbumImage.PNG"):
        self.save_image_from_URL(track_image_link, album_image_name)
        self.resize_image(album_image_name)

    def create_cache_file(self, file_name):
        """
        if the folder "cache" does not exist, create it
        if the file "file_name" does not exist, create it
        - file_name contains the file extension as part of it's string
        """
        if not os.path.exists("cache"):
            os.makedirs("cache")
        if not os.path.exists(f"cache/{file_name}"):
            open(file_name, 'w').close()