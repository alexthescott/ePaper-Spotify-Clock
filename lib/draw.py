import os
import subprocess
from time import time
from datetime import datetime as dt
from typing import List, Optional, Tuple

from PIL import Image, ImageFont, ImageDraw, ImageMath

from lib.clock_logging import logger
from lib.display_settings import display_settings

class Draw:
    """ 
    Draw to EPaper - Alex Scott 2024
    Companion functions for Draw() within clock.py for the Spotify EPaper display Clock project

    Functions rely on PIL to draw to a self-stored draw object
    Draw() draws context, date time temp, artist and track info, time since, detailed_weather, and names

    Made in companion with the Waveshare 4.2inch e-Paper Module
    https://www.waveshare.com/wiki/4.2inch_e-Paper_Module
    """
    def __init__(self, local_run: bool = False):
        self.local_run = local_run
        self.width, self.height = 400, 300
        self.set_dictionaries()
        self.ds = display_settings
        self.load_resources()
        self.album_image = None
        self.dt = None
        self.time_str = None
        self.weather_mode = False

        # Make and get the full path to the 'album_art' directory
        os.makedirs("album_art", exist_ok=True)
        self.dir_path = os.path.abspath('album_art')

        self.image_mode = 'L' if self.ds.four_gray_scale else '1'
        if self.ds.four_gray_scale:
            # Create four grayscale color palette
            subprocess.run([
                'convert', '-size', '1x4', 
                'xc:#FFFFFF', 
                'xc:#C0C0C0', 
                'xc:#808080', 
                'xc:#000000', 
                '+append', 
                os.path.join(self.dir_path, 'palette.PNG')
            ], check=True)
        
        self.image_obj = Image.new(self.image_mode, (self.width, self.height), 255)
        self.image_draw = ImageDraw.Draw(self.image_obj)

    def load_resources(self):
        """
        Load local resources. 

        This method loads fonts and icons from the /ePaperFonts and /Icons directories respectively.
        It initializes several instance variables with these resources. The fonts are loaded with 
        different sizes (16, 32, 64) and the icons are loaded as images.

        Fonts:
        - DSfnt16, DSfnt32, DSfnt64: Fonts from the Nintendo-DS-BIOS.ttf file.
        - helveti16, helveti32, helveti64: Fonts from the Habbo.ttf file.

        Icons:
            - music_context:
                - playlist_icon: Icon for playlist.
                - artist_icon: Icon for artist.
                - album_icon: Icon for album.
                - dj_icon: Icon for DJ.
                - collection_icon: Icon for collection.
            - weather:
                - 01n: Icon for clear sky at night.
                - 02n: Icon for few clouds at night.
                - 03n: Icon for scattered clouds at night.
                - 04n: Icon for broken clouds at night.
                - 09n: Icon for shower rain at night.
                - 10n: Icon for rain at night.
                - 11n: Icon for thunderstorm at night.
                - 13n: Icon for snow at night.
                - 50n: Icon for mist at night.
        """
        self.DSfnt16, self.DSfnt32, self.DSfnt64 = None, None, None
        self.helveti16, self.helveti32, self.helveti64 = None, None, None
        self.playlist_icon, self.artist_icon, self.album_icon, self.dj_icon, self.collection_icon, self.failure_icon = None, None, None, None, None, None
        self.weather_icon_dict = None
        font_sizes = [16, 32, 64]
        font_files = ['Nintendo-DS-BIOS.ttf', 'Habbo.ttf']
        for font_file in font_files:
            for size in font_sizes:
                font_attribute = f'DSfnt{size}' if "bios" in font_file.lower() else f'helveti{size}'
                setattr(self, font_attribute, ImageFont.truetype(f'ePaperFonts/{font_file}', size))

        music_context_icons = ['playlist', 'artist', 'album', 'dj', 'collection', 'failure']
        for icon in music_context_icons:
            setattr(self, f'{icon}_icon', Image.open(f'Icons/music_context/{icon}.png'))

        weather_icons = ['01', '02', '03', '04', '09', '10', '11', '13', '50']
        self.weather_icon_dict = {icon: Image.open(f'Icons/weather/{icon}.png') for icon in weather_icons}

    def set_dictionaries(self):
        """
        This method initializes three dictionaries: sf_dict, mf_dict, and lf_dict. Each dictionary represents a mapping
        from characters to their corresponding pixel lengths in different font sizes. This method is used to get the 
        pixel length of strings as they're built.
        """
        self.sf_dict = {' ': '2', '!': '2', '"': '4', '#': '8', '$': '6', '%': '8',
        '&': '7', "'": '2', '(': '4', ')': '4', '*': '8', '+': '6', ',': '3',
        '-': '6', '.': '2', '/': '4', '0': '6', '1': '3', '2': '6', '3': '6',
        '4': '7', '5': '6', '6': '6', '7': '6', '8': '6', '9': '6', ':': '2',
        ';': '3', '<': '4', '=': '6', '>': '4', '?': '5', '@': '8', 'A': '6',
        'B': '6', 'C': '6', 'D': '6', 'E': '5', 'F': '5', 'G': '6', 'H': '6',
        'I': '2', 'J': '5', 'K': '6', 'L': '5', 'M': '6', 'N': '6', 'O': '6',
        'P': '6', 'Q': '6', 'R': '6', 'S': '5', 'T': '6', 'U': '6', 'V': '6',
        'W': '6', 'X': '6', 'Y': '6', 'Z': '5', '[': '4', '\\': '4', ']': '4',
        '^': '4', '_': '6', 'a': '6', 'b': '6', 'c': '6', 'd': '6', 'e': '6',
        'f': '5', 'g': '6', 'h': '6', 'i': '2', 'j': '4', 'k': '5', 'l': '3',
        'm': '8', 'n': '6', 'o': '6', 'p': '6', 'q': '6', 'r': '5', 's': '5',
        't': '5', 'u': '6', 'v': '6', 'w': '6', 'x': '6', 'y': '6', 'z': '6',
        '{': '5', '|': '2', '}': '5', '~': '6', '¡': '2', '¢': '7', '£': '6',
        '©': '10', '®': '10', '±': '6', '¿': '5', 'À': '6', 'Á': '6', 'Â': '6',
        'Ä': '6', 'Ç': '5', 'È': '5', 'É': '5', 'Ê': '5', 'Ë': '5', 'Ì': '3',
        'Í': '3', 'Î': '4', 'Ï': '4', 'Ñ': '6', 'Ò': '6', 'Ó': '6', 'Ô': '6',
        'Ö': '6', '×': '6', 'Ù': '6', 'Ú': '6', 'Û': '6', 'Ü': '6', 'ß': '6',
        'à': '6', 'á': '6', 'â': '6', 'ä': '6', 'è': '6', 'é': '6', 'ê': '6',
        'ë': '6', 'ì': '3', 'í': '3', 'î': '4', 'ï': '4', 'ñ': '6', 'ò': '6',
        'ó': '6', 'ô': '6', 'ö': '6', '÷': '6', 'ù': '6', 'ú': '6', 'û': '6',
        'ü': '6', '‘': '3', '’': '3', '“': '5', '”': '5', '…': '6', '€': '7',
        '™': '10', '\x00': '9'}
        self.mf_dict = {' ': '4', '!': '4', '"': '8', '#': '16', '$': '12', '%': '16',
        '&': '14', "'": '4', '(': '8', ')': '8', '*': '16', '+': '12', ',': '6',
        '-': '12', '.': '4', '/': '8', '0': '12', '1': '6', '2': '12', '3': '12',
        '4': '14', '5': '12', '6': '12', '7': '12', '8': '12', '9': '12',
        ':': '4', ';': '6', '<': '8', '=': '12', '>': '8', '?': '10', '@': '16',
        'A': '12', 'B': '12', 'C': '12', 'D': '12', 'E': '10', 'F': '10',
        'G': '12', 'H': '12', 'I': '4', 'J': '10', 'K': '12', 'L': '10',
        'M': '12', 'N': '12', 'O': '12', 'P': '12', 'Q': '12', 'R': '12',
        'S': '10', 'T': '12', 'U': '12', 'V': '12', 'W': '12', 'X': '12',
        'Y': '12', 'Z': '10', '[': '8', '\\': '8', ']': '8', '^': '8', '_': '12',
        'a': '12', 'b': '12', 'c': '12', 'd': '12', 'e': '12', 'f': '10',
        'g': '12', 'h': '12', 'i': '4', 'j': '8', 'k': '10', 'l': '6', 'm': '16',
        'n': '12', 'o': '12', 'p': '12', 'q': '12', 'r': '10', 's': '10',
        't': '10', 'u': '12', 'v': '12', 'w': '12', 'x': '12', 'y': '12',
        'z': '12', '{': '10', '|': '4', '}': '10', '~': '12', '¡': '4',
        '¢': '14', '£': '12', '©': '20', '®': '20', '±': '12', '¿': '10',
        'À': '12', 'Á': '12', 'Â': '12', 'Ä': '12', 'Ç': '10', 'È': '10',
        'É': '10', 'Ê': '10', 'Ë': '10', 'Ì': '6', 'Í': '6', 'Î': '8', 'Ï': '8',
        'Ñ': '12', 'Ò': '12', 'Ó': '12', 'Ô': '12', 'Ö': '12', '×': '12',
        'Ù': '12', 'Ú': '12', 'Û': '12', 'Ü': '12', 'ß': '12', 'à': '12',
        'á': '12', 'â': '12', 'ä': '12', 'è': '12', 'é': '12', 'ê': '12',
        'ë': '12', 'ì': '6', 'í': '6', 'î': '8', 'ï': '8', 'ñ': '12', 'ò': '12',
        'ó': '12', 'ô': '12', 'ö': '12', '÷': '12', 'ù': '12', 'ú': '12',
        'û': '12', 'ü': '12', '‘': '6', '’': '6', '“': '10', '”': '10',
        '…': '12', '€': '14', '™': '20', '\x00': '18'}
        self.lf_dict = {' ': '9', '!': '9', '"': '17', '#': '33', '$': '25', '%': '33',
        '&': '29', "'": '9', '(': '17', ')': '17', '*': '33', '+': '25',
        ',': '13', '-': '25', '.': '9', '/': '17', '0': '25', '1': '13',
        '2': '25', '3': '25', '4': '29', '5': '25', '6': '25', '7': '25',
        '8': '25', '9': '25', ':': '9', ';': '13', '<': '17', '=': '25',
        '>': '17', '?': '21', '@': '33', 'A': '25', 'B': '25', 'C': '25',
        'D': '25', 'E': '21', 'F': '21', 'G': '25', 'H': '25', 'I': '9',
        'J': '21', 'K': '25', 'L': '21', 'M': '25', 'N': '25', 'O': '25',
        'P': '25', 'Q': '25', 'R': '25', 'S': '21', 'T': '25', 'U': '25',
        'V': '25', 'W': '25', 'X': '25', 'Y': '25', 'Z': '21', '[': '17',
        '\\': '17', ']': '17', '^': '17', '_': '25', 'a': '25', 'b': '25',
        'c': '25', 'd': '25', 'e': '25', 'f': '21', 'g': '25', 'h': '25',
        'i': '9', 'j': '17', 'k': '21', 'l': '13', 'm': '33', 'n': '25',
        'o': '25', 'p': '25', 'q': '25', 'r': '21', 's': '21', 't': '21',
        'u': '25', 'v': '25', 'w': '25', 'x': '25', 'y': '25', 'z': '25',
        '{': '21', '|': '9', '}': '21', '~': '25', '¡': '9', '¢': '29', '£': '25',
        '©': '41', '®': '41', '±': '25', '¿': '21', 'À': '25', 'Á': '25',
        'Â': '25', 'Ä': '25', 'Ç': '21', 'È': '21', 'É': '21', 'Ê': '21',
        'Ë': '21', 'Ì': '13', 'Í': '13', 'Î': '17', 'Ï': '17', 'Ñ': '25',
        'Ò': '25', 'Ó': '25', 'Ô': '25', 'Ö': '25', '×': '25', 'Ù': '25',
        'Ú': '25', 'Û': '25', 'Ü': '25', 'ß': '25', 'à': '25', 'á': '25',
        'â': '25', 'ä': '25', 'è': '25', 'é': '25', 'ê': '25', 'ë': '25',
        'ì': '13', 'í': '13', 'î': '17', 'ï': '17', 'ñ': '25', 'ò': '25',
        'ó': '25', 'ô': '25', 'ö': '25', '÷': '25', 'ù': '25', 'ú': '25',
        'û': '25', 'ü': '25', '‘': '13', '’': '13', '“': '21', '”': '21',
        '…': '25', '€': '29', '™': '41', '\x00': '36'}

    def set_weather_mode(self, weather_mode: bool) -> None:
        """
        Set the weather mode.

        Args:
            weather_mode (bool): Flag indicating whether to set the weather mode.
        """
        self.weather_mode = weather_mode

    def clear_image(self) -> None:
        """
        Clears the current image by creating a new blank image filled with the color white (255).
        """
        self.image_obj = Image.new(self.image_mode, (self.width, self.height), 255)
        self.image_draw = ImageDraw.Draw(self.image_obj)

    def save_png(self, file_name: str) -> None:
        """
        Saves the image object as a PNG file.

        Args:
            file_name (str): The name of the file to save the image as.
        """
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        self.image_obj.save(os.path.join(output_dir, f"{file_name}.png"))

    # ---- Formatting Functions ----------------------------------------------------------------------------
    def get_text_width(self, text: str, size: int) -> int:
        """
        Return an int representing the size of a word.

        Requires three dictionaries, defining the width of each char
        for our given font, Nintendo-DS-BIOS.ttf

        Args:
            text (str): The text to measure.
            size (int): The size of the text.

        Returns:
            int: The width of the text.
        """
        size_dict = {
            2: (self.lf_dict, 25),
            1: (self.mf_dict, 12),
            0: (self.sf_dict, 6)
        }

        char_dict, default_value = size_dict.get(size)
        if char_dict is None:
            raise ValueError(f"Invalid size: {size}")
        return sum(int(char_dict.get(c, default_value)) for c in text)

    def format_x_word(self, text_size_list: List[int], text_list: List[str], size: int) -> List[str]:
        """
        Return a list of 'squished' words to fit exact width dimensions.

        Parameters:
            text_size_list: a list of ints representing the width of each word.
            text_list: a list of strs to be combined as to print neater words.
            size: {0, 1, 2} to denote DS font sizes {16, 32, 64}.

        Returns:
            new text_list: a list of strs, occasionally combined if possible.
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        max_width = 189  # Widest width we will allow as we build word by word
        space_size = (1 + size // .6) * 2  # Correlation between size{0, 1, 2} and the pixel count of a ' ' char

        for i, word_width in enumerate(text_size_list):
            if i != len(text_size_list) - 1:  # Not our last word
                if phrase_width + word_width + space_size < max_width:  # Can fit word in last row
                    phrase_width += word_width + space_size
                else:  # Cannot fit word in last row
                    temp_text_list.append(" ".join(text_list[floor_index:i]))
                    floor_index, phrase_width = i, word_width
            else:  # Last word
                if phrase_width + word_width + space_size < max_width:  # Can fit last word in last row
                    temp_text_list.append(" ".join(text_list[floor_index:i + 1]))
                else:  # Cannot fit last word in last row
                    if len(text_list) != 1:  # If we have more than one word, separate prior to current
                        temp_text_list.append(" ".join(text_list[floor_index:i]))
                        temp_text_list.append(text_list[i])
                    else:  # Only one word, return whole word to be hyphenated later
                        temp_text_list.append(text_list[i])

        temp_text_list = [word for word in temp_text_list if word != '']
        return temp_text_list

    def hyphenate_words(self, word: str, size: int) -> List[str]:
        """
        Return a list of 'spliced' word segments to fit exact width dimensions.

        Parameters:
            word: our string to hyphenate
            size: {0, 1, 2} to denote DS font sizes {16, 32, 64}

        Returns:
            new text_list: a list of split strs from our word
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        max_width = 177  # Widest width we will allow as we build char by char

        size_dict = {
            1: self.mf_dict,
            0: self.sf_dict
        }

        char_dict = size_dict.get(size)
        if char_dict is None:
            raise ValueError(f"Invalid size: {size}")

        default_value = 12 if size == 1 else 25

        # Iterate over every character in the word
        for i, c in enumerate(word):
            char_size = int(char_dict.get(c, default_value))

            # Our last character
            if len(word) - 1 == i:
                temp_text_list.append(word[floor_index:i + 1])
            # We can add more characters to our split string
            elif phrase_width + char_size < max_width:
                phrase_width += char_size
            # Attach hyphen and start building new split string
            else:
                temp_text_list.append(word[floor_index:i] + "-")
                floor_index, phrase_width = i, char_size

        return temp_text_list

    def can_full_words_fit(self, text_size_list: List[int]) -> bool:
        """
        Check if all words can fit within the maximum width.

        Parameters:
            text_size_list: a list of ints representing the width of each word.

        Returns:
            bool: True if all words can fit, False otherwise.
        """
        max_width = 189  # Maximum width a word can have
        return all(word_len < max_width for word_len in text_size_list)

    # ---- DRAWING FUNCs ----------------------------------------------------------------------------
    def draw_border_lines(self) -> None:
        """
        Draw vertical and horizontal lines of width 3 on the image.
        """
        line_width = 3
        vertical_line_y = 224
        horizontal_line_x = 199

        for i in range(line_width):
            self.image_draw.line([(0, vertical_line_y + i), (400, vertical_line_y + i)], fill=0)
            self.image_draw.line([(horizontal_line_x + i, 0), (horizontal_line_x + i, 225)], fill=0)

    def draw_name(self, text: str, name_x: int, name_y: int) -> Tuple[int, float]:
        """
        Draw the given text at the specified position and return its dimensions.

        Parameters:
            text: The text to draw.
            name_x: The x-coordinate of the top-left corner of the text.
            name_y: The y-coordinate of the top-left corner of the text.

        Returns:
            A tuple containing the width and height of the text.
        """
        name_width = self.image_draw.textlength(text, font=self.helveti32)
        name_height = self.helveti32.size / 1.3
        self.image_draw.text((name_x, name_y), text, font=self.helveti32)

        line_start = (name_x - 1, name_y + name_height + 3)
        line_end = (name_x + name_width - 1, name_y + name_height + 3)
        self.image_draw.line([line_start, line_end], fill=0)

        return name_width, name_height

    def draw_user_time_ago(self, text: str, time_x: int, time_y: int) -> None:
        """
        Draw the given text at the specified position using the DSfnt16 font.

        Parameters:
            text: The text to draw.
            time_x: The x-coordinate of the top-left corner of the text.
            time_y: The y-coordinate of the top-left corner of the text.
        """
        self.image_draw.text((time_x, time_y), text, font=self.DSfnt16)

    def draw_detailed_weather_border(self) -> None:
        """
        Draw vertical and horizontal lines of width 2 on the image.
        """
        line_width = 2
        border_fill = 32 if self.ds.four_gray_scale else 0
        border_x = 200 if self.ds.album_art_right_side else 0

        for i in range(line_width):
            line_start = (border_x, 46 + i)
            line_end = (border_x + 200, 46 + i)
            self.image_draw.line([line_start, line_end], fill=border_fill)

    def detailed_weather_album_name(self, album_name: str) -> None:
        """
        Write the album_name in medium font in the top right of the display.

        Parameters:
            album_name: The name of the album to draw.
        """
        album_name_x = 253 if self.ds.album_art_right_side else 53
        album_name_y = 10
        max_album_width = 126
        default_char_width = 23
        album_width, formatted_album_name = 0, ""

        # make sure we don't run past context width requirements
        for c in album_name:
            char_width = int(self.mf_dict.get(c, default_char_width))
            if album_width + char_width < max_album_width:
                album_width += char_width
                formatted_album_name += c
            else:
                formatted_album_name += "..."
                break
        else:
            self.image_obj.paste(self.album_icon, (album_name_x + max_album_width - 4, album_name_y + 3))

        self.image_draw.text((album_name_x, album_name_y), formatted_album_name, font=self.DSfnt32)

    def draw_detailed_weather_information(self, weather_info: dict) -> None:
        """
        Draw a four hour forecast of the weather in the top right of the display.
        
        example weather_info:
        {'11PM': {'description': 'scattered clouds', 'temp': 61},
        '2AM': {'description': 'broken clouds', 'temp': 60},
        '5AM': {'description': 'overcast clouds', 'temp': 58},
        '8PM': {'description': 'scattered clouds', 'temp': 62}}
        """
        weather_x = 210 if self.ds.album_art_right_side else 10
        weather_y = 53
        box_width = 180
        box_height = 35

        if weather_info is None:
            logger.error("Weather info is None")
            return

        for i, (hour_str, info) in enumerate(weather_info.items()):
            box_x = weather_x
            box_y = weather_y + (box_height + 8) * i

            hour_str = hour_str.lower()
            am_pm = hour_str[-2:] if "am" in hour_str or "pm" in hour_str else ""
            current_time = hour_str[:-2] if am_pm else hour_str
            time_pos = (box_x + 5, box_y + 5)
            self.image_draw.text(time_pos, current_time, font=self.DSfnt32)

            if am_pm:
                am_pm_x = time_pos[0] + self.image_draw.textlength(current_time, font=self.DSfnt32)
                self.image_draw.text((am_pm_x + 1, time_pos[1] + 11), am_pm, font=self.DSfnt16)

            desc_icon_id = info.get('desc_icon_id', '')[:2]
            if desc_icon_id in self.weather_icon_dict:
                icon = self.weather_icon_dict[desc_icon_id]
                resized_icon = icon.resize((44, 44))
                self.image_obj.paste(resized_icon, (box_x + 98, box_y - 4))

            t_fill = 32 if self.ds.four_gray_scale else 0
            temp = info.get('temp', '')
            temp_width = self.get_text_width(str(temp), 1)
            self.image_draw.text((box_x + box_width - temp_width - 12, box_y + 5), str(temp), font=self.DSfnt32, fill=t_fill)
            unit = "C" if self.ds.metric_units else "F"
            self.image_draw.text((box_x + box_width - 10, box_y + 7), unit, font=self.DSfnt16, fill=t_fill)

    def draw_spot_context(self, context_type: str, context_text: str, context_x: int, context_y: int) -> bool:
        """
        Draws both icon {playlist, album, artist} and context text in the bottom of Spot box.

        Args:
            context_type (str): The type of context (e.g., playlist, album, artist).
            context_text (str): The text to be displayed as the context.
            context_x (int): The x-coordinate of the starting position for drawing the context.
            context_y (int): The y-coordinate of the starting position for drawing the context.

        Returns:
            bool: True if the context was successfully drawn, False otherwise.
        """
        if not context_type or not context_text:
            return False

        context_width, temp_context = 0, ""
        max_context_width = 168
        default_char_width = 6

        # make sure we don't run past context width requirements
        for c in context_text:
            char_width = int(self.sf_dict.get(c, default_char_width))
            if context_width + char_width < max_context_width:
                context_width += char_width
                temp_context += c
            else:
                temp_context += "..."
                break

        self.image_draw.text((context_x, context_y), temp_context, font=self.DSfnt16)

        # ATTACH ICONS
        icon_dict = {
            'DJ': self.dj_icon,
            'playlist': self.playlist_icon,
            'album': self.album_icon,
            'artist': self.artist_icon,
            'collection': self.collection_icon
        }

        icon = icon_dict.get(context_type, self.failure_icon)
        icon_x = context_x - 24
        icon_y = context_y - 4
        self.image_obj.paste(icon, (icon_x, icon_y))

        return True

    def draw_album_image(self, dark_mode: bool, image_file_name: str="AlbumImage_resize.PNG", pos: tuple=(0, 0), convert_image: bool=True) -> None:
        """
        Draws the album image on the ePaper display.

        Parameters:
        dark_mode (bool): Flag indicating whether to apply dark mode to the album image.
        image_file_name (str, optional): The name of the album image file. Defaults to "AlbumImage_resize.PNG".
        pos (tuple, optional): The position (x, y) where the album image should be pasted on the display. Defaults to (0, 0).
        convert_image (bool, optional): Flag indicating whether to convert the image to the specified image mode. Defaults to True.
        """
        image_file_name = "AlbumImage_resize.PNG" if image_file_name is None else image_file_name
        if convert_image or self.album_image is None:
            self.album_image = Image.open(f"album_art/{image_file_name}")
            self.album_image = self.album_image.convert(self.image_mode)
            
            if self.ds.four_gray_scale:
                before_dither = time()
                self.dither_album_art()
                after_dither = time()
                logger.info("* Dithering took %.2f seconds *", after_dither - before_dither)

        chosen_album_image = "album_art/AlbumImage"
        chosen_album_image += "_thumbnail" if self.weather_mode else "_resize"
        chosen_album_image = chosen_album_image.replace("_resize", "_dither") if self.ds.four_gray_scale else chosen_album_image
        chosen_album_image += "_dither" if self.ds.four_gray_scale and self.weather_mode else ""
        self.album_image = Image.open(f"{chosen_album_image}.PNG")

        if dark_mode:
            self.album_image = ImageMath.eval('255-(a)', a=self.album_image)

        self.image_obj.paste(self.album_image, pos)

    def draw_weather(self, pos: tuple, weather_info: tuple) -> None:
        """
        This method draws the current and forecasted temperatures on the image.

        Parameters:
        pos (tuple): A tuple containing the x and y coordinates where the temperature should be drawn.
        weather_info (tuple): A tuple containing the current temperature, high forecasted temperature, 
                            low forecasted temperature, and another temperature value.
        """
        if not weather_info:
            temp = temp_high = temp_low = "NA"
            temp_degrees = ""
        else:
            temp, temp_high, temp_low = weather_info
            temp_degrees = "C" if self.ds.metric_units else "F"

        # main temp pos calculations
        temp_start_x = pos[0]
        temp_width = self.image_draw.textlength(str(temp), font=self.DSfnt64)

        # forecast temp pos calculations
        temp_high_width = self.get_text_width(str(temp_high), 1)
        temp_low_width = self.get_text_width(str(temp_low), 1)
        forecast_temp_x = temp_start_x + temp_width + 18 + max(temp_low_width, temp_high_width)

        # fixes negative temperature formatting issue
        if (isinstance(temp_high, int) and isinstance(temp_low, int)) and (temp_high < 0 or temp_low < 0):
            forecast_temp_x -= 5

        # draw main temp
        self.image_draw.text(pos, str(temp), font=self.DSfnt64)
        self.image_draw.text((temp_start_x + temp_width, 245), temp_degrees, font=self.DSfnt32)

        # draw forecast temp
        f_fill = 32 if self.ds.four_gray_scale else 0
        self.image_draw.text((forecast_temp_x - temp_high_width, 242), str(temp_high), font=self.DSfnt32, fill=f_fill)
        self.image_draw.text((forecast_temp_x + 2, 244), temp_degrees, font=self.DSfnt16, fill=f_fill)
        self.image_draw.text((forecast_temp_x - temp_low_width, 266), str(temp_low), font=self.DSfnt32, fill=f_fill)
        self.image_draw.text((forecast_temp_x + 2, 268), temp_degrees, font=self.DSfnt16, fill=f_fill)

    def draw_time(self, pos: tuple) -> None:
        """
        Draws the given time at the specified position on the image.

        If the time includes "am" or "pm", it separates these from the main time and draws them separately.

        Parameters:
        pos (tuple): A tuple containing the x and y coordinates where the time should be drawn.
        """
        if not self.time_str:
            date = dt.now()
            self.time_str = date.strftime("%-H:%M") if self.ds.twenty_four_hour_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()

        am_pm = self.time_str[-2:] if "am" in self.time_str or "pm" in self.time_str else ""
        current_time = self.time_str[:-2] if am_pm else self.time_str

        text_width, text_height = self.image_draw.textlength(current_time, font=self.DSfnt64), self.DSfnt64.size/1.3
        if am_pm:
            text_width += self.image_draw.textlength(am_pm, font=self.DSfnt32)

        # Draw a white rectangle over the old date
        rectangle_pos = [pos[0]-15, pos[1]-10, pos[0]+text_width+20, pos[1]+text_height]
        self.image_draw.rectangle(rectangle_pos, fill="white", outline="white")

        self.image_draw.text(pos, current_time, font=self.DSfnt64)

        if am_pm:
            am_pm_x = pos[0] + self.image_draw.textlength(current_time, font=self.DSfnt64)
            self.image_draw.text((am_pm_x, pos[1] + 22), am_pm, font=self.DSfnt32)

    def draw_date_time_temp(self, weather_info: Optional[Tuple[int, int, int]], time_str: str) -> None:
        """
        This function draws the date, time, and temperature on the display. 
        """
        temp, temp_high, temp_low = weather_info if weather_info else (0, 0, 0)
        left_elem_x = 10
        bar_height = 74  # the height of the bottom bar
        self.time_str = time_str

        # Calculate common elements
        temp_width, temp_height = self.image_draw.textlength(str(temp), font=self.DSfnt64), self.DSfnt64.size/1.3
        time_width, time_height = self.calculate_time_dimensions()

        if self.ds.time_on_right:
            left_elem_y = self.height - (bar_height // 2) - (temp_height // 2)
            self.draw_weather((left_elem_x, left_elem_y), weather_info)

            right_elem_x = self.width - time_width - 5
            right_elem_y = self.height - (bar_height // 2) - (time_height // 2)
            self.draw_time((right_elem_x, right_elem_y))
        else:
            left_elem_y = self.height - (bar_height // 2) - (time_height // 2)
            self.draw_time((left_elem_x, left_elem_y))

            forecast_temp_x = temp_width + 20
            temp_high_width, temp_low_width = self.get_text_width(str(temp_high), 1), self.get_text_width(str(temp_low), 1)
            right_elem_x = self.width - (forecast_temp_x + max(temp_high_width, temp_low_width) + 12)
            right_elem_y = self.height - (bar_height // 2) - (temp_height // 2)
            self.draw_weather((right_elem_x, right_elem_y), weather_info)

        # Draw the date in the center of the bottom bar
        self.dt = dt.now()
        date_width, date_height = self.image_draw.textlength(self.dt.strftime("%a, %b %-d"), font=self.DSfnt32), self.DSfnt32.size/1.3
        date_x =  left_elem_x + time_width + (right_elem_x - left_elem_x - time_width) // 2 - date_width // 2
        date_y = 239 + date_height
        self.image_draw.text((date_x, date_y), self.dt.strftime("%a, %b %-d"), font=self.DSfnt32)

    def calculate_time_dimensions(self) -> tuple:
        """
        Calculates the width and height of the time string to be drawn on the image.

        If the time includes "am" or "pm", it separates these from the main time and calculates their dimensions separately.

        Returns:
        tuple: A tuple containing the width and height of the time string.
        """
        am_pm = self.time_str[-2:] if "am" in self.time_str or "pm" in self.time_str else ""
        current_time = self.time_str[:-2] if am_pm else self.time_str

        time_width = self.image_draw.textlength(current_time, font=self.DSfnt64)
        time_height = self.DSfnt64.size / 1.3

        if am_pm:
            time_width += self.image_draw.textlength(am_pm, font=self.DSfnt32)

        return time_width, time_height

    def draw_track_text(self, track_name: str, track_x: int, track_y: int) -> tuple:
        """
        Draws the track name at the specified position on the image.

        The track name is split into lines and drawn in a large, medium, or small format depending on its length.

        Parameters:
        track_name (str): The name of the track to be drawn.
        track_x (int): The x-coordinate where the track name should be drawn.
        track_y (int): The y-coordinate where the track name should be drawn.

        Returns:
        tuple: A tuple containing the number of lines the track name was split into and the height of the text.
        """
        track_name_split = track_name.split(" ")
        track_name_size = list(map(self.get_text_width, track_name_split, [2] * len(track_name_split)))
        track_lines = self.format_x_word(track_name_size, track_name_split, 2)
        track_size = list(map(self.get_text_width, track_lines, [2] * len(track_name_split)))

        # Large Text Format Check
        if sum(track_size) <= 378 and self.can_full_words_fit(track_size) and len(track_size) <= 2:
            for line in track_lines:
                self.image_draw.text((track_x, track_y), line, font=self.DSfnt64)
                track_y += 43
            return len(track_lines), 55

        # Medium Text Format Check
        track_name_split = track_name.split(" ") if len(track_name.split(" ")) > 1 else [track_name]
        track_name_size = list(map(self.get_text_width, track_name_split, [1] * len(track_name_split)))
        track_lines = self.format_x_word(track_name_size, track_name_split, 1)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(track_lines)))

        if sum(track_size) <= 945:
            if not self.can_full_words_fit(track_size):
                track_lines = self.hyphenate_words(str(track_name_split)[2:-2], 1)
            for line in track_lines:
                self.image_draw.text((track_x, track_y), line, font=self.DSfnt32)
                track_y += 26
            return len(track_lines), 26

        # Small Text Format Check
        track_name_split = track_name.split(" ") if len(track_name.split(" ")) > 1 else [track_name]
        track_name_size = list(map(self.get_text_width, track_name_split, [0] * len(track_name_split)))
        track_lines = self.format_x_word(track_name_size, track_name_split, 0)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(track_name_split)))
        track_y += 5

        if not self.can_full_words_fit(track_name_size):
            track_lines = self.hyphenate_words(str(track_name_split)[2:-2], 1)
        for line in track_lines:
            self.image_draw.text((track_x, track_y), line, font=self.DSfnt16)
            track_y += 12
        return len(track_lines), 13

    def draw_artist_text(self, artist_name: str, track_line_count: int, track_height: int, artist_x:int, artist_y: int) -> None:
        """
        Draws the artist name at the specified position on the image.

        The artist name is split into lines and drawn in a large, medium, or small format depending on its length.

        Parameters:
        artist_name (str): The name of the artist to be drawn.
        track_line_count (int): The number of lines the track name was split into.
        track_height (int): The height of the track name text.
        artist_x (int): The x-coordinate where the artist name should be drawn.
        artist_y (int): The y-coordinate where the artist name should be drawn.
        """
        # Large Text Format Check
        l_artist_split = artist_name.split(" ")
        l_artist_size = list(map(self.get_text_width, l_artist_split, [2] * len(l_artist_split)))
        if sum(l_artist_size) <= 366 and self.can_full_words_fit(l_artist_size) and len(l_artist_size) <= 2:
            if track_height == 55 and track_line_count + len(l_artist_size) <= 3 or track_height < 55 and track_line_count < 4:
                artist_lines = self.format_x_word(l_artist_size, l_artist_split, 2)
                artist_y -= (42 * len(artist_lines))  # y nudge to fit bottom constraint
                for line in artist_lines:
                    self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt64)
                    artist_y += 43
                return

        # Medium Text Format Check
        m_artist_split = artist_name.split(" ") if len(artist_name.split(" ")) > 1 else [artist_name]
        m_title_size = list(map(self.get_text_width, m_artist_split, [1] * len(m_artist_split)))
        artist_lines = self.format_x_word(m_title_size, m_artist_split, 1)
        artist_size = list(map(self.get_text_width, artist_lines, [1] * len(m_artist_split))) 
        if sum(artist_size) <= 760 and track_line_count + len(artist_lines) <= 6:
            artist_y -= (25 * len(artist_lines))  # y nudge to fit bottom constraint
            if not self.can_full_words_fit(m_title_size):
                artist_lines = self.hyphenate_words(str(m_artist_split)[2:-2], 1)
            for line in artist_lines:
                self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt32)
                artist_y += 26
            return

        # Small Text Format Check
        s_artist_split = artist_name.split(" ") if len(artist_name.split(" ")) > 1 else [artist_name]
        s_artist_size = list(map(self.get_text_width, s_artist_split, [0] * len(s_artist_split)))
        artist_lines = self.format_x_word(s_artist_size, s_artist_split, 0)
        artist_size = list(map(self.get_text_width, artist_lines, [0] * len(s_artist_split)))
        artist_y -= (12 * len(artist_lines))  # y nudge to fit bottom constraint
        if not self.can_full_words_fit(s_artist_size):
            artist_lines = self.hyphenate_words(str(s_artist_split)[2:-2], 1)
        for line in artist_lines:
            self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt16)
            artist_y += 12

    # ---- DRAW MISC FUNCs ----------------------------------------------------------------------------

    def dither_album_art(self) -> bool:
        """
        Dithers the album art image using the Floyd-Steinberg algorithm.

        The image is resized and the colors are remapped using a palette. The dithered image is then saved to a file.

        Returns:
        bool: True if the dithering was successful, False otherwise.
        """
        # Define the file paths
        palette_path = os.path.join(self.dir_path, 'palette.PNG')
        resize_paths = [os.path.join(self.dir_path, 'AlbumImage_thumbnail.PNG')]
        dither_paths = [os.path.join(self.dir_path, 'AlbumImage_thumbnail_dither.PNG')]

        if not self.weather_mode:
            resize_paths.append(os.path.join(self.dir_path, 'AlbumImage_resize.PNG'))
            dither_paths.append(os.path.join(self.dir_path, 'AlbumImage_dither.PNG'))

        for resize_path, dither_path in zip(resize_paths, dither_paths):
            # Check if the files exist
            if not os.path.exists(resize_path) or not os.path.exists(palette_path):
                logger.error("Error: File %s not found.", resize_path if not os.path.exists(resize_path) else palette_path)
                return False

            # Remap the colors in the image
            start_time = time()
            subprocess.run(['convert', resize_path, '-dither', 'Floyd-Steinberg', '-remap', palette_path, dither_path], check=True)
            end_time = time()
            logger.info("* Dithering %s took %.2f seconds *", os.path.basename(dither_path), end_time - start_time)

            if not os.path.exists(dither_path):
                logger.error("Error: File %s not found.", dither_path)
                return False

            self.album_image = Image.open(dither_path)

        return True

    def dark_mode_flip(self) -> None:
        """
        Used in clock.py to invert the entire image for sunset dark mode
        """
        self.image_obj.paste(ImageMath.eval('255-(a)', a=self.image_obj), (0, 0))


    def get_image_obj(self) -> Image:
        """
        Used in clock.py to be passed into EPD's getBuffer()
        """
        return self.image_obj
