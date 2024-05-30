import os
from datetime import datetime as dt
from typing import Optional, Tuple

import requests
from PIL import Image

from lib.clock_logging import logger

class Misc():
    """
    A class that provides miscellaneous utility functions for image manipulation and retrieval.
    """
    
    def save_image_from_url(self, track_image_link: str, file_name: str) -> bool:
        """
        Saves an image from a given URL to a file.

        Args:
            track_image_link (str): The URL of the image to be saved.
            file_name (str): The name of the file to save the image as.

        Returns:
            bool: True if the image was successfully saved, False otherwise.
        """
        os.makedirs("cache", exist_ok=True)
        os.makedirs("cache/album_art", exist_ok=True)
        try:
            img_data = requests.get(track_image_link, timeout=25).content
        except requests.exceptions.RequestException as e:
            logger.error("Failed to get %s: %s", track_image_link, e)
            return False

        with open(f"cache/album_art/{file_name}", 'wb') as handler:
            handler.write(img_data)

        return True

    def resize_image(self, image_name: str, size: Tuple[int, int] = (199, 199)) -> None:
        """
        Resize the given image and save it as a PNG file.

        Args:
            image_name (str): The name of the image file to resize.
            size (Tuple[int, int]): The desired size of the resized image. Default is (199, 199).
        """
        os.makedirs("cache", exist_ok=True)
        os.makedirs("cache/album_art", exist_ok=True)
        postfix = "resize" if any(s >= 100 for s in size) else "thumbnail"
        outfile = os.path.splitext(image_name)[0] + f"_{postfix}.PNG"
        try:
            im = Image.open(f"cache/album_art/{image_name}")
            im.thumbnail(size)
            im = im.convert("L")
            im.save(f"cache/album_art/{outfile}", "PNG")
        except IOError:
            logger.error("Cannot create %s for '%s'", postfix, image_name)

    def has_sun_set(self, sunset_info: Optional[Tuple[int, int]], sunset_flip: bool) -> bool:
        """
        Checks if the sun has set based on the current time and sunset information.

        Args:
            sunset_info (Optional[Tuple[int, int]]): A tuple containing the hour and minute of the sunset time.
            sunset_flip (bool): A flag indicating whether the sunset time should be flipped.

        Returns:
            bool: True if the sun has set, False otherwise.
        """
        if sunset_info is None or None in sunset_info:
            logger.error("has_sun_set() given invalid sunset_info")
            return False

        current_time = dt.now()
        current_hour = current_time.hour
        current_minute = current_time.minute

        sunset_hour, sunset_minute = sunset_info

        return sunset_flip and ((sunset_hour < current_hour or current_hour < 2) or (sunset_hour == current_hour and sunset_minute <= current_minute))

    def get_album_art(self, track_image_link: str, album_image_name: str = "AlbumImage.PNG") -> bool:
        """
        Downloads the album art from the given track image link and saves it with the specified album image name.
        The downloaded image is then resized.
        
        Args:
            track_image_link (str): The URL of the track image.
            album_image_name (str): The name of the album image file (default is "AlbumImage.PNG").

        Returns:
            bool: True if the album art was successfully downloaded and resized, False otherwise.
        """
        if not self.save_image_from_url(track_image_link, album_image_name):
            return False

        self.resize_image(album_image_name)
        self.resize_image(album_image_name, (46, 46))
        return True