import os
from datetime import datetime as dt
from requests import get as get_request
from PIL import Image
from lib.clock_logging import logger

class Misc():
    """
    A class that provides miscellaneous utility functions for image manipulation and retrieval.
    """
    
    def save_image_from_url(self, track_image_link: str, file_name: str):
        """
        Saves an image from a given URL to a file.
        track_image_link (str): The URL of the image to be saved.
        file_name (str): The name of the file to save the image as.
        """
        os.makedirs("album_art", exist_ok=True)
        img_data = get_request(track_image_link, timeout=20).content
        with open(f"album_art/{file_name}", 'wb') as handler:
            handler.write(img_data)

    def resize_image(self, image_name: str):
        """
        Resize the given image and save it as a PNG file.
        image_name (str): The name of the image file to resize.
        """
        os.makedirs("album_art", exist_ok=True)
        size = 199, 199
        outfile = os.path.splitext(image_name)[0] + "_resize.PNG"
        if image_name == outfile:
            return None
        try:
            im = Image.open(f"album_art/{image_name}")
            im.thumbnail(size)
            im = im.convert("L")
            im.save(f"album_art/{outfile}", "PNG", mode="L")
        except IOError:
            logger.error("cannot create thumbnail for '%s'", image_name)

    def has_sun_set(self, sunset_info: tuple, sunset_flip: bool):
        """
        Checks if the sun has set based on the current time and sunset information.

        Args:
            sunset_info (tuple): A tuple containing the hour and minute of the sunset time.
            sunset_flip (bool): A flag indicating whether the sunset time should be flipped.

        Returns:
            bool: True if the sun has set, False otherwise.
        """
        if not sunset_info:
            logger.error("has_sun_set() given invalid sunset_info")
            return False
        date = dt.now()
        c_hour = int(date.strftime("%-H"))
        c_minute = int(date.strftime("%-M"))
        sun_h, sun_m = sunset_info
        return sunset_flip and ((sun_h < c_hour or c_hour < 2) or (sun_h == c_hour and sun_m <= c_minute))

    def get_album_art(self, track_image_link: str, album_image_name: str = "AlbumImage.PNG"):
        """
        Downloads the album art from the given track image link and saves it with the specified album image name.
        The downloaded image is then resized.
        
        Args:
            track_image_link (str): The URL of the track image.
            album_image_name (str): The name of the album image file (default is "AlbumImage.PNG").
        """
        self.save_image_from_url(track_image_link, album_image_name)
        self.resize_image(album_image_name)