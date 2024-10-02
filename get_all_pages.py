import os
import requests
import json
from PIL import Image, ImageDraw, ImageOps
from io import BytesIO

# Function to get all pages
def get_all_pages(wiki_name):
    url = f'https://{wiki_name}.fandom.com/api.php'
    
    params = {
        'action': 'query',
        'list': 'allpages',
        'aplimit': 'max',
        'format': 'json'
    }

    all_pages = []
    continue_token = None

    while True:
        if continue_token:
            params['apcontinue'] = continue_token

        response = requests.get(url, params=params)
        data = response.json()

        all_pages.extend(data['query']['allpages'])

        if 'continue' in data:
            continue_token = data['continue']['apcontinue']
        else:
            break

    return all_pages

# Function to fetch thumbnail and categories for a specific page
def get_page_info(wiki_name, pageid):
    url = f'https://{wiki_name}.fandom.com/api.php'
    
    params = {
        'action': 'query',
        'pageids': pageid,
        'prop': 'pageimages|categories',  # Fetch page images and categories
        'pithumbsize': 500,  # Fetch thumbnail at this size
        'format': 'json'
    }

    response = requests.get(url, params=params)
    data = response.json()

    page_data = data.get('query', {}).get('pages', {}).get(str(pageid), {})
    
    # Extract thumbnail URL if it exists
    thumbnail_url = page_data.get('thumbnail', {}).get('source')

    # Extract categories
    categories = [cat['title'] for cat in page_data.get('categories', [])]

    return thumbnail_url, categories

# Function to download an image, resize, crop to 256x256, and make it a squircle PNG
def download_and_process_image(image_url, filename, folder, wiki_name):  # Add wiki_name parameter
    base_filename, _ = os.path.splitext(filename) # Get filename without extension
    filename = f"{wiki_name}-{base_filename}.png"  # Include wiki name in filename
    file_path = os.path.join(folder, filename)
    
    # Check if the file already exists
    if os.path.exists(file_path):
        print(f"File {filename} already exists, skipping download.")
        return

    # Download the image
    response = requests.get(image_url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))

        # Resize and crop to 256x256
        image = resize_and_crop_image(image, (256, 256))

        # Convert the image to a squircle PNG
        squircled_image = make_squircle(image)

        # Save the processed image as PNG with transparency
        if not os.path.exists(folder):
            os.makedirs(folder)
        squircled_image.save(file_path, format='PNG')
        print(f"Downloaded and processed: {filename}")
    else:
        print(f"Failed to download image: {filename}")

# Function to resize and crop image to square (256x256)
def resize_and_crop_image(image, size):
    width, height = image.size
    aspect_ratio = width / height

    if aspect_ratio > 1:
        new_width = int(aspect_ratio * size[1])
        image = image.resize((new_width, size[1]), Image.Resampling.LANCZOS)
        left = (new_width - size[0]) / 2
        right = left + size[0]
        image = image.crop((left, 0, right, size[1]))
    else:
        new_height = int(size[0] / aspect_ratio)
        image = image.resize((size[0], new_height), Image.Resampling.LANCZOS)
        top = (new_height - size[1]) / 2
        bottom = top + size[1]
        image = image.crop((0, top, size[0], bottom))

    image = image.resize(size, Image.Resampling.LANCZOS)
    return image

# Function to make the image into a squircle with transparent background (radius: 30 pixels)
def make_squircle(image):
    size = image.size  # Assumes image is already 256x256 or the desired size

    # Create a mask for the squircle
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Create a rounded square (squircle) shape in the mask with a 30-pixel radius
    radius = 30  # Fixed radius of 30 pixels for the rounded corners
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius, fill=255)

    # Apply the mask to the image to get a squircle
    squircled_image = Image.new("RGBA", size)
    squircled_image.paste(image, (0, 0), mask)

    return squircled_image

# Function to save pages data to JSON
def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Main logic
def main():
    wiki_name = 'wiki1'  # Replace with the actual name of the fandom wiki
    folder_name = f'icons'  # Folder where thumbnails will be saved
    json_filename = f'{wiki_name}_pages.json'  # JSON file to save detailed page info

    # Step 1: Fetch all pages
    pages = get_all_pages(wiki_name)

    # Create a list to store detailed page information
    detailed_pages_info = []

    # Step 2: Download and process thumbnails, and gather categories for each page
    for page in pages:
        pageid = page['pageid']
        title = page['title']
        
        # Fetch thumbnail URL and categories
        thumbnail_url, categories = get_page_info(wiki_name, pageid)
        
        # Download the image if a thumbnail exists
        if thumbnail_url:
            filename = f"{pageid}.png" # Generate base filename from id
            download_and_process_image(thumbnail_url, filename, folder_name, wiki_name) # Pass filename, folder, and wiki_name
        else:
            print(f"No thumbnail for pageid: {pageid}")

        # Save the detailed info (page title, pageid, categories) in the list
        detailed_pages_info.append({
            'pageid': pageid,
            'title': title,
            'categories': categories,
            'thumbnail': f"{filename}" if thumbnail_url else None
        })

    # Step 3: Save all the detailed page info to a JSON file
    save_to_json(detailed_pages_info, json_filename)

    print(f"Finished processing {len(pages)} pages.")

# Run the script
if __name__ == "__main__":
    main()
