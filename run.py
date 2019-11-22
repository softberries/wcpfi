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
    version="wc/v3"
)

BUCKET_NAME = config('S3_BUCKET')
S3_BASE_URL = config('S3_BASE_IMG_URL')

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
    data = {'name': name, 'slug': slug, 'status': 'draft', 'stock_quantity': 1, 'sold_individually': 'true',
            'categories': [
                {
                    'id': config('DEFAULT_WC_GROUP_ID', cast=int)
                }
            ], 'images': list(map(lambda x: get_image_data(x, name), urls))}
    return data


def get_image_data(url, name):
    bn = ntpath.basename(url)
    data = {
        'src': url,
        'name': bn, 'alt': name + ':' + bn
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


# Iterate over the files
exts = ['*.JPG', '*.jpg', '*.png', '*.PNG']
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

logging.info('Groups: ' + str(groups))

# Upload data to WC
for grp in groups:
    name = get_product_name(grp)
    slug = get_product_slug(grp)
    urls = list(map(lambda x: S3_BASE_URL + x, groups[grp]))
    dat = prepare_data(name, slug, urls)
    logging.debug('WC Data: ' + str(dat))
    r = wcapi.post('products', data=dat)
    logging.info('Processed ' + str(grp) + ', status: ' + str(r.json()))
