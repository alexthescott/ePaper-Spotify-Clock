""" drawToEPD.py by Alex Scott 2020
Companion functions for spotifyEPD.py

Functions here rely on PIL to draw to an existing draw object
Draw context, date time temp, artist and track info, time since, and names

Made for the Waveshare 4.2inch e-Paper Module
https://www.waveshare.com/wiki/4.2inch_e-Paper_Module
"""

from PIL import Image, ImageFont
from random import randint

WIDTH, HEIGHT = 400, 300

# Used to get the pixel length of strings as they're built
sfDict = {' ': '2', '!': '2', '"': '4', '#': '8', '$': '6', '%': '8',
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
mfDict = {' ': '4', '!': '4', '"': '8', '#': '16', '$': '12', '%': '16',
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
lfDict = {' ': '9', '!': '9', '"': '17', '#': '33', '$': '25', '%': '33',
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

# Load local resources. Fonts and Icons from /ePaperFonts and /Icons
DSfnt16 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 16)
DSfnt32 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 32)
DSfnt64 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 64)

helveti16 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 16)
helveti32 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 32)
helveti64 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 64)

playlist_icon = Image.open('Icons/playlist.png')
artist_icon = Image.open('Icons/artist.png')
album_icon = Image.open('Icons/album.png')

# ---- FORMATTING FUNCs
def findTextWidth(text, size):
    """ Returns an int representing the size of a word
        
        Requires three dictionaries, defining the width of each char 
            for our given font, Nintendo-DS-BIOS.ttf 
    """
    if size == 2:
        return sum(int(lfDict.get(c, 25)) for c in text)
    elif size == 1:
        return sum(int(mfDict.get(c, 12)) for c in text)
    elif size == 0:
        return sum(int(sfDict.get(c, 6)) for c in text)

def combineWords(text_size_list, text_list, size):
    """ Returns a list of 'squished' words to fit exact width dimensions
        Parameters:
            text_size_list: a list of ints representing the width of each word
            text_list: a list of strs to be combined as to print neater words
            size: {0, 1, 2} to denote DS font sizes {16, 32, 64} 
        Returns:
            new text_list: a list of strs, occasionally combined if possible
    """
    temp_text_list = []
    phrase_width, floor_index = 0, 0
    # Correlation between size{0, 1, 2} and the pixel count of a ' ' char
    space_size = (1 + size // .6) * 2

    for i, word_width in enumerate(text_size_list):
        # Not our last word
        if i != len(text_size_list) - 1:
            # Can fit word in last row
            if phrase_width + word_width + space_size < 189:
                phrase_width += word_width + space_size
            # Cannot fit word in last row
            else:
                temp_text_list.append(" ".join(text_list[floor_index:i]))
                floor_index, phrase_width = i, word_width
        else:
            # Can fit last word in last row
            if phrase_width + word_width + space_size < 189:
                temp_text_list.append(" ".join(text_list[floor_index:i+1]))
            # Cannot fit last word in last row
            else:
                # If we have more than one word, seperate prior to current
                if len(text_list) != 1:
                    temp_text_list.append(" ".join(text_list[floor_index:i]))
                    temp_text_list.append(text_list[i])
                # Only one word, return whole word to be hypenated later
                else:
                    temp_text_list.append(text_list[i])
    temp_text_list[:] = [word for word in temp_text_list if word != '']
    return temp_text_list

def hyphenWords(word, size):
    """ Returns a list of 'spliced' word segments to fit exact width dimensions
        Parameters:
            word: our string to hyphenate
            size: {0, 1, 2} to denote DS font sizes {16, 32, 64} 
        Returns:
            new text_list: a list of split strs from our word
    """
    temp_text_list = []
    phrase_width, floor_index = 0, 0
    char_size = 0
    # Iterate over every character in the word
    for i, c in enumerate(word): 
        # Find relative char width. Will never hyphenate Large text
        if size == 1:
            char_size = int(mfDict.get(c, 12))
        elif size == 0: 
            char_size = int(sfDict.get(c, 25))

        # Our last character
        if len(word) - 1 == i:
            temp_text_list.append(word[floor_index:i+1])
        # We can add more characters to our split string
        elif phrase_width + char_size < 177:
            phrase_width += char_size
        # Attach hyphen and start building new split string
        else:
            temp_text_list.append(word[floor_index:i] + "-")
            floor_index, phrase_width = i, char_size
    return temp_text_list

def canFullWordsFit(text_size_list):
    return all(word_len < 189 for word_len in text_size_list)

# ---- DRAWING FUNCs
def drawBorderLines(img_draw_obj):
    # draw vertical and horizontal lines of width 3
    for i in range(3):
        img_draw_obj.line([(0, 224 + i), (400, 224 + i)], fill = 0)
        img_draw_obj.line([(199 + i, 0), (199 + i, 225)], fill = 0)

def drawName(img_draw_obj, text, name_x, name_y):
    # move_x and move_y are here to slightly adjust the position of the text
    # maybe this might stop 'burn in' on the epd?
    move_x, move_y = randint(-1, 1), randint(-1, 1)
    name_width, name_height = img_draw_obj.textsize(text, font = helveti32)
    img_draw_obj.text((name_x + move_x, name_y + move_y), text, font = helveti32)
    img_draw_obj.line([(name_x - 1 + move_x, name_y + name_height + 3 + move_y), (name_x + name_width - 1 + move_x, name_y + name_height + 3 + move_y)], fill = 0)
    return name_width, name_height

def drawUserTimeAgo(img_draw_obj, text, time_x, time_y):
    # draw text next to name displaying time since last played track
    move_x, move_y = randint(-2, 1), randint(-2, 1)
    time_width, time_height = img_draw_obj.textsize(text, font = DSfnt16)
    img_draw_obj.text((time_x + move_x, time_y + move_y), text, font = DSfnt16)

def drawSpotContext(img_draw_obj, Himage, context_type, context_text, context_x, context_y):
    # Draws both icon {playlist, album, artist} and context text in the bottom of Spot box
    moveLine = randint(-1, 1)
    if context_type != None:
        context_width, temp_context = 0, ""
        # make sure we don't run past context width requirements
        for c in context_text:
            char_width = int(sfDict.get(c, 6))
            if context_width + char_width < 168:
                context_width += char_width
                temp_context += c
            else:
                temp_context += "..."
                break
        img_draw_obj.text((context_x, context_y), temp_context, font = DSfnt16)
        
        # ATTACH ICONS
        if context_type == 'playlist':
            Himage.paste(playlist_icon, (context_x - 21, context_y - 1))
        elif context_type == 'album':
            Himage.paste(album_icon, (context_x - 24, context_y - 4))
        elif context_type == 'artist':
            Himage.paste(artist_icon, (context_x - 22, context_y - 1))

def drawAlbumImage(Himage, imageFileName):
    albumImage = Image.open(imageFileName)
    Himage.paste(albumImage,(0,0))

def drawDateTimeTemp(img_draw_obj, military_time, date_str, temp_tuple, metric_units):
    temp, temp_high, temp_low, other_temp = temp_tuple
    temperature_type = "C" if metric_units else "F"

    temp_x, temp_y = 292, 240
    # CHECK for triple digit weather :( and adjust temp print location
    if temp >= 100: temp_x -= 10 

    # Draw "upper temp" next to name of right user
    high_temp_x = 387 - findTextWidth(str(other_temp), 1)
    img_draw_obj.text((high_temp_x, 0), str(other_temp), font = DSfnt32)
    img_draw_obj.text((high_temp_x + 2 + findTextWidth(str(other_temp), 1), 2), temperature_type, font = DSfnt16)
    
    # Draw main temp
    img_draw_obj.text((temp_x, 240), str(temp), font = DSfnt64)
    img_draw_obj.text((temp_x + findTextWidth(str(temp), 2), 244), temperature_type, font = DSfnt32)
    if temp >= 100: temp_x += 10 

    # Draw high and low temp
    high_temp_x = temp_x + 96 - findTextWidth(str(temp_high), 1)
    img_draw_obj.text((high_temp_x, 240), str(temp_high), font = DSfnt32)
    img_draw_obj.text((high_temp_x + 2 + findTextWidth(str(temp_high), 1), 242), temperature_type, font = DSfnt16)
    low_temp_x = temp_x + 96 - findTextWidth(str(temp_low), 1)
    img_draw_obj.text((low_temp_x, 264), str(temp_low), font = DSfnt32)
    img_draw_obj.text((low_temp_x + 2 + findTextWidth(str(temp_low), 1), 266), temperature_type, font = DSfnt16)
 
    # Draw date and time
    # Draw date and time
    if "am" in military_time or "pm" in military_time:
        am_pm = military_time[-2:]
        current_time = military_time[:-2]
        current_time_width, _ = img_draw_obj.textsize(current_time, DSfnt64)
        img_draw_obj.text((10, 240), current_time, font = DSfnt64)
        current_am_pm_width, _ = img_draw_obj.textsize(am_pm, DSfnt32)
        img_draw_obj.text((current_time_width + 10, 262), am_pm, font = DSfnt32)
        time_width = current_time_width + current_am_pm_width
    else:
        time_width, time_height = img_draw_obj.textsize(military_time, DSfnt64)
        img_draw_obj.text((10, 240), military_time, font = DSfnt64)
    date_width, date_height = img_draw_obj.textsize(date_str, DSfnt32)
    date_x, date_y = ((10 + time_width + temp_x) // 2) - (date_width // 2), 240 + date_height // 1.05
    img_draw_obj.text((date_x, date_y), date_str, font = DSfnt32)

def drawTrackText(img_draw_obj, track_name, track_x, track_y):
    # After deciding the size of text, split words into lines, and draw to img_draw_obj

    # Large Text Format Check
    l_title_split = track_name.split(" ")
    l_title_size = list(map(findTextWidth, l_title_split, [2] * len(l_title_split)))
    track_lines = combineWords(l_title_size, l_title_split, 2)
    track_size = list(map(findTextWidth, track_lines, [2] * len(l_title_split)))
    if sum(track_size) <= 378 and canFullWordsFit(track_size) and len(track_size) <= 2:
        for line in track_lines:
            img_draw_obj.text((track_x, track_y), line, font = DSfnt64)
            track_y += 43
        return len(track_lines), 55

    # Medium Text Format Check
    m_title_split = []
    if len(track_name.split(" ")) > 1:
        m_title_split = track_name.split(" ")
    else:
        m_title_split.append(track_name)
    m_title_size = list(map(findTextWidth, m_title_split, [1] * len(m_title_split)))
    track_lines = combineWords(m_title_size, m_title_split, 1)
    track_size = list(map(findTextWidth, track_lines, [1] * len(track_lines)))
    if sum(track_size) <= 945:
        if not canFullWordsFit(track_size):
            track_lines = hyphenWords(str(m_title_split)[2:-2], 1)
        for line in track_lines:
            img_draw_obj.text((track_x, track_y), line, font = DSfnt32)
            track_y += 26
        return len(track_lines), 26

    # Small Text Format Check
    s_title_split = []
    if len(track_name.split(" ")) > 1:
        s_title_split = track_name.split(" ")
    else:
        s_title_split.append(track_name)
    s_title_size = list(map(findTextWidth, s_title_split, [0] * len(s_title_split)))
    track_lines = combineWords(s_title_size, s_title_split, 0)
    track_size = list(map(findTextWidth, track_lines, [1] * len(s_title_split)))
    track_y += 5
    if not canFullWordsFit(s_title_size):
        track_lines = hyphenWords(str(s_title_split)[2:-2], 1)
    for line in track_lines:
        img_draw_obj.text((track_x, track_y), line, font = DSfnt16)
        track_y += 12
    return len(track_lines), 13

def drawArtistText(img_draw_obj, artist_name, track_line_count, track_height, artist_x, artist_y):
    # Always ensure bottom of text is always at 190 pixels after draw height

    # Large Text Format Check
    l_artist_split = artist_name.split(" ")
    l_artist_size = list(map(findTextWidth, l_artist_split, [2] * len(l_artist_split)))
    if sum(l_artist_size) <= 366 and canFullWordsFit(l_artist_size) and len(l_artist_size) <= 2:
        if track_height == 55 and track_line_count + len(l_artist_size) <= 3 or track_height < 55 and track_line_count < 4:
            artist_lines = combineWords(l_artist_size, l_artist_split, 2)
            artist_y = 190 - (42 * len(artist_lines)) # y nudge to fit bottom constraint
            for line in artist_lines:
                img_draw_obj.text((artist_x, artist_y), line, font = DSfnt64)
                artist_y += 43
            return 

    # Medium Text Format Check
    m_artist_split = []
    if len(artist_name.split(" ")) > 1:
        m_artist_split = artist_name.split(" ")
    else:
        m_artist_split.append(artist_name)
    m_title_size = list(map(findTextWidth, m_artist_split, [1] * len(m_artist_split)))
    artist_lines = combineWords(m_title_size, m_artist_split, 1)
    artist_size = list(map(findTextWidth, artist_lines, [1] * len(m_artist_split))) 
    if sum(artist_size) <= 760 and track_line_count + len(artist_lines) <= 6:
        artist_y = 190 - (25 * len(artist_lines)) # y nudge to fit bottom constraint
        if not canFullWordsFit(m_title_size):
            artist_lines = hyphenWords(str(m_artist_split)[2:-2], 1)
        for line in artist_lines:
            img_draw_obj.text((artist_x, artist_y), line, font = DSfnt32)
            artist_y += 26
        return

    # Small Text Format Check
    s_artist_split = []
    if len(artist_name.split(" ")) > 1:
        s_artist_split = artist_name.split(" ")
    else:
        s_artist_split.append(artist_name)
    s_artist_size = list(map(findTextWidth, s_artist_split, [0] * len(s_artist_split)))
    artist_lines = combineWords(s_artist_size, s_artist_split, 0)
    artist_size = list(map(findTextWidth, artist_lines, [0] * len(s_artist_split)))
    artist_y = 190 - (12 * len(artist_lines)) # y nudge to fit bottom constraint
    if not canFullWordsFit(s_artist_size):
        artist_lines = hyphenWords(str(s_artist_split)[2:-2], 1)
    for line in artist_lines:
        img_draw_obj.text((artist_x, artist_y), line, font = DSfnt16)
        artist_y += 12
