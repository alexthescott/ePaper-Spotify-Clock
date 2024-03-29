import os
import json
import subprocess
from time import time
from datetime import timedelta, datetime as dt
from PIL import Image, ImageFont, ImageDraw, ImageMath

from lib.clock_logging import logger

class Draw():
    """ Draw to EPaper - Alex Scott 2024
    Companion functions for mainSpotifyClock.py

    Functions here rely on PIL to draw to an existing draw object
    Draw context, date time temp, artist and track info, time since, and names

    Made for the Waveshare 4.2inch e-Paper Module
    https://www.waveshare.com/wiki/4.2inch_e-Paper_Module
    """
    def __init__(self, local_run=False):
        self.local_run = local_run
        self.width, self.height = 400, 300
        self.set_dictionaries()
        self.load_display_settings()
        self.load_resources()
        self.album_image = None
        self.dt = None
        self.time_str = None

        # Make and get the full path to the 'album_art' directory
        os.makedirs("album_art", exist_ok=True)
        self.dir_path = os.path.abspath('album_art')

        if self.four_gray_scale:
            # Create four grayscale color palette
            self.image_mode = 'L'
            subprocess.run([
            'convert', '-size', '1x4', 
            'xc:#FFFFFF', 
            'xc:#C0C0C0', 
            'xc:#808080', 
            'xc:#000000', 
            '+append', 
            os.path.join(self.dir_path, 'palette.PNG')
            ], check=True)
        else:
            self.image_mode = '1'
        
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
        - playlist_icon: Icon for playlist.
        - artist_icon: Icon for artist.
        - album_icon: Icon for album.
        - dj_icon: Icon for DJ.
        - collection_icon: Icon for collection.
        """
        self.DSfnt16 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 16)
        self.DSfnt32 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 32)
        self.DSfnt64 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 64)
        self.helveti16 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 16)
        self.helveti32 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 32)
        self.helveti64 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 64)

        self.playlist_icon = Image.open('Icons/playlist.png')
        self.artist_icon = Image.open('Icons/artist.png')
        self.album_icon = Image.open('Icons/album.png')
        self.dj_icon = Image.open('Icons/dj.png')
        self.collection_icon = Image.open('Icons/collection.png')
        self.failure_icon = Image.open('Icons/failure.png')

    def load_display_settings(self):
        """
        Load display settings from config/display_settings.json
        """
        # EPD Settings imported from config/display_settings.json ---------------------------------------------------
        with open('config/display_settings.json', 'r', encoding='utf-8') as display_settings:
            display_settings = json.load(display_settings)
            main_settings = display_settings["main_settings"]
            single_user_settings = display_settings["single_user_settings"]
            self.metric_units = main_settings["metric_units"]             # (True -> C°, False -> F°)
            self.twenty_four_hour_clock =   main_settings["twenty_four_hour_clock"] # (True -> 22:53, False -> 10:53pm) 
            self.time_on_right = main_settings["time_on_right"]           # (True -> time is displayed on the right, False -> time is displayed on the left)
            self.hide_other_weather = main_settings["hide_other_weather"] # (True -> weather not shown in top right, False -> weather is shown in top right)
            self.four_gray_scale = main_settings["four_gray_scale"]       # (True -> 4 gray scale, False -> Black and White)
            self.album_art_right_side = single_user_settings["album_art_right_side"]       # (True -> 4 gray scale, False -> Black and White)

    def set_dictionaries(self):
        """
        This method initializes three dictionaries: sf_dict, mf_dict, and lf_dict. Each dictionary represents a mapping
        from characters to their corresponding pixel lengths in different font sizes. his method is used to get the 
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

    def clear_image(self):
        """
        This method clears the current image by creating a new blank image filled with the color white (255)
        """
        self.image_obj = Image.new(self.image_mode, (self.width, self.height), 255)
        self.image_draw = ImageDraw.Draw(self.image_obj)

    def save_png(self, file_name: str):
        """
        Saves the image object as a PNG file.
        """
        os.makedirs("test_output", exist_ok=True)
        self.image_obj.save(os.path.join("test_output", f"{file_name}.png"))

    # ---- Formatting Funcs ----------------------------------------------------------------------------
    def get_text_width(self, text: str, size: int):
        """ Return an int representing the size of a word

            Requires three dictionaries, defining the width of each char
            for our given font, Nintendo-DS-BIOS.ttf
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

    def format_x_word(self, text_size_list: list, text_list: list, size: int):
        """ Return a list of 'squished' words to fit exact width dimensions

            Parameters:
                text_size_list: a list of ints representing the width of each word
                text_list: a list of strs to be combined as to print neater words
                size: {0, 1, 2} to denote DS font sizes {16, 32, 64}
            Returns:
                new text_list: a list of strs, occasionally combined if possible
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        max_width = 189  # Widest width we will allow as we build word by word
        # Correlation between size{0, 1, 2} and the pixel count of a ' ' char
        space_size = (1 + size // .6) * 2

        for i, word_width in enumerate(text_size_list):
            # Not our last word
            if i != len(text_size_list) - 1:
                # Can fit word in last row
                if phrase_width + word_width + space_size < max_width:
                    phrase_width += word_width + space_size
                # Cannot fit word in last row
                else:
                    temp_text_list.append(" ".join(text_list[floor_index:i]))
                    floor_index, phrase_width = i, word_width
            else:
                # Can fit last word in last row
                if phrase_width + word_width + space_size < max_width:
                    temp_text_list.append(" ".join(text_list[floor_index:i + 1]))
                # Cannot fit last word in last row
                else:
                    # If we have more than one word, separate prior to current
                    if len(text_list) != 1:
                        temp_text_list.append(" ".join(text_list[floor_index:i]))
                        temp_text_list.append(text_list[i])
                    # Only one word, return whole word to be hyphenated later
                    else:
                        temp_text_list.append(text_list[i])
        temp_text_list[:] = [word for word in temp_text_list if word != '']
        return temp_text_list

    def hyphenate_words(self, word: str, size: int):
        """ Return a list of 'spliced' word segments to fit exact width dimensions

            Parameters:
                word: our string to hyphenate
                size: {0, 1, 2} to denote DS font sizes {16, 32, 64}
            Returns:
                new text_list: a list of split strs from our word
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        char_size = 0
        max_width = 177  # Widest width we will allow as we build char by char
        # Iterate over every character in the word
        for i, c in enumerate(word):
            # Find relative char width. Will never hyphenate Large text
            if size == 1:
                char_size = int(self.mf_dict.get(c, 12))
            elif size == 0:
                char_size = int(self.sf_dict.get(c, 25))

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

    def can_full_words_fit(self, text_size_list: list):
        return all(word_len < 189 for word_len in text_size_list)

    # ---- DRAWING FUNCs ----------------------------------------------------------------------------
    def draw_border_lines(self):
        # draw vertical and horizontal lines of width 3
        for i in range(3):
            self.image_draw.line([(0, 224 + i), (400, 224 + i)], fill=0)
            self.image_draw.line([(199 + i, 0), (199 + i, 225)], fill=0)

    def draw_name(self, text: str, name_x: int, name_y: int):
        name_width, name_height = self.image_draw.textlength(text, font=self.helveti32), self.helveti32.size/1.3
        self.image_draw.text((name_x, name_y), text, font=self.helveti32)
        line_start_x, line_start_y = name_x - 1, name_y + name_height + 3
        line_end_x, line_end_y = name_x + name_width - 1, name_y + name_height + 3
        self.image_draw.line([(line_start_x, line_start_y), (line_end_x, line_end_y)], fill=0)
        return name_width, name_height

    def draw_user_time_ago(self, text: str, time_x: int, time_y: int):
        # draw text next to name displaying time since last played track
        self.image_draw.text((time_x, time_y), text, font=self.DSfnt16)

    def draw_spot_context(self, context_type: str, context_text: str, context_x: int, context_y: int):
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
        # make sure we don't run past context width requirements
        for c in context_text:
            char_width = int(self.sf_dict.get(c, 6))
            if context_width + char_width < 168:
                context_width += char_width
                temp_context += c
            else:
                temp_context += "..."
                break
        self.image_draw.text((context_x, context_y), temp_context, font=self.DSfnt16)

        # ATTACH ICONS
        if context_text == 'DJ':
            self.image_obj.paste(self.dj_icon, (context_x - 24, context_y - 4))
        elif context_type == 'playlist':
            self.image_obj.paste(self.playlist_icon, (context_x - 21, context_y - 1))
        elif context_type == 'album':
            self.image_obj.paste(self.album_icon, (context_x - 24, context_y - 4))
        elif context_type == 'artist':
            self.image_obj.paste(self.artist_icon, (context_x - 22, context_y - 1))
        elif context_type == 'collection':
            self.image_obj.paste(self.collection_icon, (context_x - 24, context_y - 4))
        else:
            self.image_obj.paste(self.failure_icon, (context_x - 24, context_y - 4))

    def draw_album_image(self, dark_mode: bool, image_file_name: str="AlbumImage_resize.PNG", pos: tuple=(0, 0), convert_image: bool=True):
        """
        Draws the album image on the ePaper display.

        Parameters:
        dark_mode (bool): Flag indicating whether to apply dark mode to the album image.
        image_file_name (str, optional): The name of the album image file. Defaults to "AlbumImage_resize.PNG".
        pos (tuple, optional): The position (x, y) where the album image should be pasted on the display. Defaults to (0, 0).
        convert_image (bool, optional): Flag indicating whether to convert the image to the specified image mode. Defaults to True.
        """
        if convert_image or self.album_image is None:
            self.album_image = Image.open(f"album_art/{image_file_name}")
            self.album_image = self.album_image.convert(self.image_mode)
            
            if self.four_gray_scale and image_file_name!="NA.png":
                before_dither = time()
                self.dither_album_art()
                after_dither = time()
                logger.info("* Dithering took %.2f seconds *", after_dither - before_dither)

            if dark_mode:
                self.album_image = ImageMath.eval('255-(a)', a=self.album_image)
        self.image_obj.paste(self.album_image, pos)

    def draw_weather(self, pos: tuple, weather_info: tuple):
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
            temp, temp_high, temp_low, _ = weather_info
            temp_degrees = "C" if self.metric_units else "F"

        # main temp pos calculations
        temp_start_x, temp_width = pos[0], self.image_draw.textlength(str(temp), font=self.DSfnt64)

        # forecast temp pos calculations
        temp_high_width, temp_low_width = self.get_text_width(str(temp_high), 1), self.get_text_width(str(temp_low), 1)
        forcast_temp_x = temp_start_x + temp_width + 18 + max(temp_low_width, temp_high_width)

        # fixes negative temperature formatting issue
        if (isinstance(temp_high, int) and isinstance(temp_low, int)) and (temp_high < 0 or temp_low < 0):
            forcast_temp_x -= 5

        # draw main temp
        self.image_draw.text(pos, str(temp), font=self.DSfnt64)
        self.image_draw.text((temp_start_x + temp_width, 245), temp_degrees, font=self.DSfnt32)

        # draw forecast temp
        self.image_draw.text((forcast_temp_x - temp_high_width, 242), str(temp_high), font=self.DSfnt32)
        self.image_draw.text((forcast_temp_x + 2, 244), temp_degrees, font=self.DSfnt16)
        self.image_draw.text((forcast_temp_x - temp_low_width, 266), str(temp_low), font=self.DSfnt32)
        self.image_draw.text((forcast_temp_x + 2, 268), temp_degrees, font=self.DSfnt16)

    def draw_time(self, pos: tuple, time_str: str=""):
        """
        Draws the given time at the specified position on the image.

        If the time includes "am" or "pm", it separates these from the main time and draws them separately.

        Parameters:
        pos (tuple): A tuple containing the x and y coordinates where the time should be drawn.
        time (str): The time to be drawn. This should be a string in the format "HH:MM" or "HH:MM am/pm".
        """
        if not time_str:
            date = dt.now()
            time_str = date.strftime("%-H:%M") if self.twenty_four_hour_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()
        am_pm = time_str[-2:] if "am" in time_str or "pm" in time_str else ""
        current_time = time_str[:-2] if am_pm else time_str
        text_width, text_height = self.image_draw.textlength(current_time, font=self.DSfnt64), self.DSfnt64.size/1.3
        if am_pm:
            text_width += self.image_draw.textlength(am_pm, font=self.DSfnt32)
        # Draw a white rectangle over the old date
        self.image_draw.rectangle([pos[0]-15, pos[1]-10, (pos[0]+text_width+20, pos[1]+text_height)], fill="white", outline="white")
        self.image_draw.text(pos, current_time, font=self.DSfnt64)

        if am_pm:
            am_pm_x = pos[0] + self.image_draw.textlength(current_time, font=self.DSfnt64)
            self.image_draw.text((am_pm_x, pos[1] + 22), am_pm, font=self.DSfnt32)

    def draw_date_time_temp(self, weather_info: tuple, time_str: str):
        """
        This function draws the date, time, and temperature on the display. 
        """
        if not weather_info:
            temp, temp_high, temp_low, other_temp = 0, 0, 0, 0
        else:
            temp, temp_high, temp_low, other_temp = weather_info
        temp_degrees = "C" if self.metric_units else "F"
        left_elem_x = 10
        bar_height = 74  # the height of the bottom bar
        self.time_str = time_str

        # Calculate common elements
        temp_width, temp_height = self.image_draw.textlength(str(temp), font=self.DSfnt64), self.DSfnt64.size/1.3
        time_width, time_height = self.calculate_time_dimensions()

        if self.time_on_right:
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

        # Draw "upper temp" next to name of right user
        if not self.hide_other_weather:
            high_temp_x = 387 - self.get_text_width(str(other_temp), 1)
            self.image_draw.text((high_temp_x, 0), str(other_temp), font=self.DSfnt32)
            self.image_draw.text((high_temp_x + 2 + self.get_text_width(str(other_temp), 1), 2), temp_degrees, font=self.DSfnt16)

    def calculate_time_dimensions(self):
        if "am" in self.time_str or "pm" in self.time_str:
            time_width, time_height = self.image_draw.textlength(str(self.time_str[:-2]), font=self.DSfnt64), self.DSfnt64.size/1.3
            time_width += self.image_draw.textlength(str(self.time_str[-2:]), font=self.DSfnt32)
        else:
            time_width, time_height = self.image_draw.textlength(self.time_str, font=self.DSfnt64), self.DSfnt64.size/1.3
        return time_width, time_height

    def draw_track_text(self, track_name: str, track_x: int, track_y: int):
        # After deciding the size of text, split words into lines, and draw to self.image_obj

        # Large Text Format Check
        l_title_split = track_name.split(" ")
        l_title_size = list(map(self.get_text_width, l_title_split, [2] * len(l_title_split)))
        track_lines = self.format_x_word(l_title_size, l_title_split, 2)
        track_size = list(map(self.get_text_width, track_lines, [2] * len(l_title_split)))
        if sum(track_size) <= 378 and self.can_full_words_fit(track_size) and len(track_size) <= 2:
            for line in track_lines:
                self.image_draw.text((track_x, track_y), line, font=self.DSfnt64)
                track_y += 43
            return len(track_lines), 55

        # Medium Text Format Check
        m_title_split = []
        if len(track_name.split(" ")) > 1:
            m_title_split = track_name.split(" ")
        else:
            m_title_split.append(track_name)
        m_title_size = list(map(self.get_text_width, m_title_split, [1] * len(m_title_split)))
        track_lines = self.format_x_word(m_title_size, m_title_split, 1)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(track_lines)))
        if sum(track_size) <= 945:
            if not self.can_full_words_fit(track_size):
                track_lines = self.hyphenate_words(str(m_title_split)[2:-2], 1)
            for line in track_lines:
                self.image_draw.text((track_x, track_y), line, font=self.DSfnt32)
                track_y += 26
            return len(track_lines), 26

        # Small Text Format Check
        s_title_split = []
        if len(track_name.split(" ")) > 1:
            s_title_split = track_name.split(" ")
        else:
            s_title_split.append(track_name)
        s_title_size = list(map(self.get_text_width, s_title_split, [0] * len(s_title_split)))
        track_lines = self.format_x_word(s_title_size, s_title_split, 0)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(s_title_split)))
        track_y += 5
        if not self.can_full_words_fit(s_title_size):
            track_lines = self.hyphenate_words(str(s_title_split)[2:-2], 1)
        for line in track_lines:
            self.image_draw.text((track_x, track_y), line, font=self.DSfnt16)
            track_y += 12
        return len(track_lines), 13

    def draw_artist_text(self, artist_name: str, track_line_count: int, track_height: int, artist_x:int, artist_y: int):
        # Always ensure bottom of text is always at 190 pixels after draw height
        # Large Text Format Check
        l_artist_split = artist_name.split(" ")
        l_artist_size = list(map(self.get_text_width, l_artist_split, [2] * len(l_artist_split)))
        if sum(l_artist_size) <= 366 and self.can_full_words_fit(l_artist_size) and len(l_artist_size) <= 2:
            if track_height == 55 and track_line_count + len(l_artist_size) <= 3 or track_height < 55 and track_line_count < 4:
                artist_lines = self.format_x_word(l_artist_size, l_artist_split, 2)
                artist_y = 190 - (42 * len(artist_lines))  # y nudge to fit bottom constraint
                for line in artist_lines:
                    self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt64)
                    artist_y += 43
                return

        # Medium Text Format Check
        m_artist_split = []
        if len(artist_name.split(" ")) > 1:
            m_artist_split = artist_name.split(" ")
        else:
            m_artist_split.append(artist_name)
        m_title_size = list(map(self.get_text_width, m_artist_split, [1] * len(m_artist_split)))
        artist_lines = self.format_x_word(m_title_size, m_artist_split, 1)
        artist_size = list(map(self.get_text_width, artist_lines, [1] * len(m_artist_split))) 
        if sum(artist_size) <= 760 and track_line_count + len(artist_lines) <= 6:
            artist_y = 190 - (25 * len(artist_lines))  # y nudge to fit bottom constraint
            if not self.can_full_words_fit(m_title_size):
                artist_lines = self.hyphenate_words(str(m_artist_split)[2:-2], 1)
            for line in artist_lines:
                self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt32)
                artist_y += 26
            return

        # Small Text Format Check
        s_artist_split = []
        if len(artist_name.split(" ")) > 1:
            s_artist_split = artist_name.split(" ")
        else:
            s_artist_split.append(artist_name)
        s_artist_size = list(map(self.get_text_width, s_artist_split, [0] * len(s_artist_split)))
        artist_lines = self.format_x_word(s_artist_size, s_artist_split, 0)
        artist_size = list(map(self.get_text_width, artist_lines, [0] * len(s_artist_split)))
        artist_y = 190 - (12 * len(artist_lines))  # y nudge to fit bottom constraint
        if not self.can_full_words_fit(s_artist_size):
            artist_lines = self.hyphenate_words(str(s_artist_split)[2:-2], 1)
        for line in artist_lines:
            self.image_draw.text((artist_x, artist_y), line, font=self.DSfnt16)
            artist_y += 12

    # ---- DRAW MISC FUNCs ----------------------------------------------------------------------------
    
    def dither_album_art(self):
        # Remap the colors in the image
        subprocess.run(['convert', os.path.join(self.dir_path, 'AlbumImage_resize.PNG'), '-dither', 'Floyd-Steinberg', '-remap', os.path.join(self.dir_path, 'palette.PNG'), os.path.join(self.dir_path, 'AlbumImage_dither.PNG')], check=True)
        self.album_image = Image.open("album_art/AlbumImage_dither.PNG")

    def dark_mode_flip(self):
        self.image_obj.paste(ImageMath.eval('255-(a)', a=self.image_obj), (0, 0))

    def get_image_obj(self):
        return self.image_obj