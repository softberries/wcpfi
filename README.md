# WCPFI
## WooCommerce Products From Images

This is a simple python script to convert a list of images into products in WooCommerce. 

### The Flow
1. Get images from a directory `IMAGES_INPUT` 
2. Resize images with `python-resize-image` and place them in the temporary folder `IMAGES_OUTPUT`
3. Upload the images to S3
4. Group images by name (more on that in the description below)
5. Create products with name and slug from the image name
6. Create new products in WooCommerce

### Image naming
The `wcpfi` script is using image names to generate the product name, slug and also uses the image name to group
 multiple images for a single product together.

Eg. if you have a list of images:

* product_with_fancy_property_1.jpg
* product_with_fancy_property_2.jpg
* product_with_fancy_property_3.jpg
* red_product_1.jpg

The script will create 2 products:

* Product 1: {name: 'Product With Fancy Property', slug: 'product_with_funcy_property', images: [ 3 images from above ]}
* Product 2: {name: 'Red Product', slug: 'red_product', images: [ 1 image from above ]}

You can add/modify the rest of the defaults sent to WooCommerce inside `prepare_data` method.

### Running the app

1. Install the requirements found in `requirements.txt`
2. Fill up the `settings.ini` file
3. Export the following env variables for your s3 access:
```$xslt
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_DEFAULT_REGION=
```
4. Run `python run.py`