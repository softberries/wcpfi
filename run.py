import shutil
import glob
import os
from woocommerce import API
from PIL import Image
from resizeimage import resizeimage
import ntpath
import boto3
from collections import defaultdict
import re
from decouple import config
import logging
import datetime

logging.basicConfig(level=logging.INFO)

inputFolder = config('IMAGES_INPUT')
outputFolder = config('IMAGES_OUTPUT')
size = config('IMG_WIDTH', default=350, cast=int), config('IMG_HEIGHT', default=350, cast=int)

# S3 Client
S3 = boto3.client('s3')
# Woocommerce client
wcapi = API(
    url=config('WC_URL'),
    consumer_key=config('WC_CONSUMER_KEY'),
    consumer_secret=config('WC_CONSUMER_SECRET'),
    version="wc/v3",
    query_string_auth=True #Force Basic Authentication as query string true and using under HTTPS
)

BUCKET_NAME = config('S3_BUCKET')
S3_BASE_URL = config('S3_BASE_IMG_URL')
DEFAULT_TAGS = [{'id': 73}, {'id': 74}]

# Clean the output directory
if os.path.isdir(outputFolder):
    shutil.rmtree(outputFolder)
os.mkdir(outputFolder)



# Resize Image
def resize(imageName):
    with open(os.path.join(inputFolder, imageName), 'r+b') as f:
        with Image.open(f) as image:
            cover = resizeimage.resize_cover(image, size)
            cover.save(os.path.join(outputFolder, imageName), image.format)


# Prepare data
def prepare_data(name, slug, urls):
    sku = get_sku(slug)
    tags = list(map(lambda x: get_tag(x), get_tags(slug)))
    tags.append({'id': 73})
    tags.append({'id': 74})
    color = get_color(slug)
    data = {'name': name, 'slug': slug, 'sku': sku, 'status': 'draft', 'stock_quantity': 1, 'sold_individually': 'true',
            'description': "Produkt nadaje się do mycia w zmywarce. Kolor może różnić się nieznacznie od tego na zdjęciach.",
            'categories': [
                get_category(slug)
            ],
            'images': list(map(lambda x: get_image_data(x, name), urls)),
            'tags': tags,
            'attributes': [{'id': 1, 'options': [color]}]
            }
    return data


def get_image_data(url, name):
    bn = ntpath.basename(url)
    data = {
        'src': url,
        'name': bn, 'alt': name + ':' + bn
    }
    return data

def get_tags(slug):
    return slug.split("_")

def get_tag(tag):
    data = {}
    if "granat" in tag or "jabłko" in tag or "jablko" in tag:
        data = {
            'id': 66
        }
    if "konik" in tag or "ryba" in tag:
        data = {
            'id': 71
        }
    if "liście" in tag or "liscie" in tag:
        data = {
            'id': 72
        }
    if "muszla" in tag or "chabry" in tag or "liść" in tag or "lisc" in tag or "muchomor" in tag or "rumianek" in tag:
        data = {
            'id': 72
        }
    return data

def get_color(slug):
    color = ""
    if "czerwona" in slug or "czerwony" in slug or "czerwone" in slug:
        color = "Czerwony"
    if "turkusowa" in slug or "turkusowe" in slug or "turkusowy" in slug:
        color = "Turkusowy"
    if "szmaragdowa" in slug or "szmaragdowe" in slug or "szmaragdowy" in slug:
        color = "Szmaragdowy"
    if "seledynowa" in slug or "seledynowe" in slug or "seledynowy" in slug:
        color = "Seledynowy"
    if "fioletowa" in slug or "fioletowe" in slug or "fioletowy" in slug:
        color = "Fioletowy"
    if "biała" in slug or "białe" in slug or "biały" in slug:
        color = "Biały"
    if "brązowa" in slug or "brązowe" in slug or "brązowy" in slug:
        color = "Brązowy"
    if "niebieska" in slug or "niebieskie" in slug or "niebieski" in slug:
        color = "Niebieski"
    if "pomarańczowa" in slug or "pomarańczowe" in slug or "pomarańczowy" in slug:
        color = "Pomarańczowy"
    if "szara" in slug or "szare" in slug or "szary" in slug:
        color = "Szary"
    if "zielona" in slug or "zielone" in slug or "zielony" in slug:
        color = "Zielony"
    return color

def get_category(slug):
    data = {}
    if "skarbonka" in slug:
        data = {
            'id': 70
        }
    if "patera" in slug or "paterka" in slug:
        data = {
            'id': 69
        }
    if "podstawka" in slug:
        data = {
            'id': 68
        }
    if "misa" in slug or "miska" in slug or "miseczka" in slug:
        data = {
            'id': 67
        }
    if "dekokracja" in slug or "ikebana" in slug:
        data = {
            'id': 63
        }
    if "plecionka" in slug:
        data = {
            'id': 77
        }
    return data


def get_trailing_number(s):
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else 0


def get_product_name(rawName):
    lst = rawName.split('_')
    return ' '.join([e.capitalize() for e in lst])


def get_product_slug(rawName):
    lst = rawName.split('_')
    return '_'.join(lst)

def get_sku(slug):
    lst = slug.split("_")
    letters = [word[0].upper() for word in lst]
    return "".join(letters) + f"{datetime.datetime.now():%Y%m%d-%s}"


# Iterate over the files
exts = ['*.JPG', '*.jpg', '*.jpeg', '*.JPEG', '*.png', '*.PNG']
files = [f for ext in exts for f in glob.glob(os.path.join(inputFolder, ext))]
groups = defaultdict(list)

# build groups of files
for f in files:
    fileName = ntpath.basename(f)
    basename, extension = os.path.splitext(fileName)
    trailingNr = get_trailing_number(basename)
    rawProductName = basename.rsplit('_', 1)[0]
    groups[rawProductName].append(fileName)
    resize(fileName)
    S3.upload_file(os.path.join(outputFolder, fileName), BUCKET_NAME, fileName, ExtraArgs={'ACL': 'public-read'})

# logging.info('Groups: ' + str(groups))

# Upload data to WC
for grp in groups:
    name = get_product_name(grp)
    slug = get_product_slug(grp)
    urls = list(map(lambda x: S3_BASE_URL + x, groups[grp]))
    urls.sort()
    dat = prepare_data(name, slug, urls)
    logging.info('WC Data: ' + str(dat))
    r = wcapi.post('products', data=dat)
    logging.info('Processed ' + str(grp) + ', status: ' + str(r.json()))