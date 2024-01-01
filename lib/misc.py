from requests import get as get_request
from PIL import Image, ImageFont, ImageDraw, ImageMath
from os.path import splitext

def save_image_from_URL(track_image_link, fileName):
    img_data = get_request(track_image_link).content
    with open(fileName, 'wb') as handler:
        handler.write(img_data)

def resize_image(imageName):
    size = 199, 199
    outfile = splitext(imageName)[0] + "_resize.PNG"
    if imageName != outfile:
        try:
            im = Image.open(imageName)
            im.thumbnail(size)
            im.save(outfile, "PNG")
        except IOError:
            print ("cannot create thumbnail for '%s'" % imageName)