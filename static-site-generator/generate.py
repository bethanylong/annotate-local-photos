#!/usr/bin/env python3.10

from PIL import Image, ExifTags
import collections
from datetime import datetime
from exif import Image as ExifImage
from jinja2 import Environment, FileSystemLoader
import itertools
import json
import requests
import os
import shutil
import subprocess
import sys

CSS_FILE = "site.css"
INDEX_HTML = "index.html"
TEMPLATE_DIR = "templates/"

TOPICS = {
    "animals": {
        "name": "animals",
        "slug": "animals",
        "image": "paradise-marmot-on-rock-2022-09.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/paradise-marmot-on-rock-2022-09.jpg')",
    },
    "engineering": {
        "name": "engineering",
        "slug": "engineering",
        "image": "carbon-river-suspension-bridge-tower-cables.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/carbon-river-suspension-bridge-tower-cables.jpg')",
    },
    "erosion": {
        "name": "erosion",
        "slug": "erosion",
        "image": "burroughs-sign-erosion-windward.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/burroughs-sign-erosion-windward.jpg')",
    },
    "glacier": {
        "name": "glacier",
        "slug": "glacier",
        "image": "paradise-nisqually-river-headwaters.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/paradise-nisqually-river-headwaters.jpg')",
    },
    "river": {
        "name": "river",
        "slug": "river",
        "image": "carbon-river-boulders.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/carbon-river-boulders.jpg')",
    },
    "subalpine meadow": {
        "name": "subalpine meadow",
        "slug": "subalpine-meadow",
        "image": "indian-henry-wildflowers-and-cabin.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/indian-henry-wildflowers-and-cabin.jpg')",
    },
    "temperate rainforest": {
        "name": "temperate rainforest",
        "slug": "temperate-rainforest",
        "image": "carbon-river-tree-ferns.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/carbon-river-tree-ferns.jpg')",
    },
    "tundra": {
        "name": "tundra",
        "slug": "tundra",
        "image": "panhandle-gap-tundra.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/panhandle-gap-tundra.jpg')",
    },
    "volcanism": {
        "name": "volcanism",
        "slug": "volcanism",
        "image": "south-puyallup-columns-wide-view.jpg",
        "style": "background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url('../thumbnails/south-puyallup-columns-wide-view.jpg')",
    },
}


def find_pictures_for_each_tag(pictures):
    count = collections.Counter()
    by_tag = collections.defaultdict(list)

    for picture in sorted(pictures.keys()):
        details = pictures[picture]
        if "tags" in details:
            tags = details["tags"].split(", ")

            if not any(tag in tags for tag in ("photo", "panorama")):
                raise ValueError("Item has no type like photo or panorama")

            if "panorama" in tags:
                # Skip panoramas for now
                continue

            for tag in TOPICS.keys():
                if tag in tags:
                    by_tag[tag].append(picture)

            details["tags"] = tags
            count.update(tags)
        else:
            # Untagged pictures are skipped (maybe they suck)
            pass

    return by_tag


def write_to_path(parent_dir, filename, new_file_contents):
    os.makedirs(parent_dir, exist_ok=True)
    full_path = os.path.join(parent_dir, filename)
    with open(full_path, "w") as fh:
        fh.write(new_file_contents)


def render_main_explore_page(topics=TOPICS):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("explore_all.html")
    content = tpl.render(topics=topics)
    return content


def render_explore_topic_page(lowercase_topic, picture_filenames, annotator_metadata):
    topic = lowercase_topic.title()
    pictures = []
    for picture_filename in picture_filenames:
        picture_info = annotator_metadata[picture_filename]
        picture_info["slug"] = picture_filename.split(".")[0]
        picture_info["style"] = f'background-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0), rgba(0, 0, 0, 0)), url(\'../../thumbnails/{picture_filename}\')'
        pictures.append(picture_info)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("explore_topic.html")
    content = tpl.render(
        topic=topic,
        pictures=pictures,
    )
    return content


def write_all_topic_pages(root, annotator_metadata, by_tag):
    for lowercase_topic, picture_filenames in by_tag.items():
        content = render_explore_topic_page(lowercase_topic, picture_filenames, annotator_metadata)
        slug = "-".join(lowercase_topic.split())
        topic_dir_path = os.path.join(root, "explore", slug)
        write_to_path(topic_dir_path, INDEX_HTML, content)


# https://medium.com/spatial-data-science/how-to-extract-gps-coordinates-from-images-in-python-e66e542af354
def decimal_coords(coords, ref):
    decimal_degrees = coords[0] + coords[1] / 60 + coords[2] / 3600
    if ref == "S" or ref == "W":
        decimal_degrees = -decimal_degrees
    return decimal_degrees


def write_map_file(root, picture_filename, latitude, longitude):
    base = "https://maps.googleapis.com/maps/api/staticmap"
    size = "500x400"
    scale = "2"
    markers = f"{latitude},{longitude}"
    center = "47.0514,-122.1044"  # near Orting
    visible = "Tacoma"
    # Only fetch from API if we haven't loaded this one before
    map_dir_path = os.path.join(root, "maps")
    map_filename = f"{picture_filename}_map.png"  # ugly but whatever
    map_path = os.path.join(map_dir_path, map_filename)
    if not os.path.isfile(map_path):
        key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not key:
            # I'm super duper tempted to make this a KeyError
            raise Exception("Must have GOOGLE_MAPS_API_KEY env var")
        url = f"{base}?key={key}&size={size}&scale={scale}&markers={markers}&center={center}&visible={visible}"

        os.makedirs(map_dir_path, exist_ok=True)
        response = requests.get(url)
        with open(map_path, "wb") as fh:
            fh.write(response.content)


def render_view_page(root, slug, picture_filename, picture_metadata):
    headline = picture_metadata["headline"]

    try:
        description = picture_metadata["description"].split("\n\n")
    except KeyError:
        description = [""]

    try:
        location = picture_metadata["locate"]
    except KeyError:
        # We do actually want to enforce that each picture has a location
        raise

    # Assume we've copied it over already
    full_picture_path = os.path.join(root, "images", picture_filename)
    with Image.open(full_picture_path) as image_obj:
        exif_timestamp_key = 306
        assert ExifTags.TAGS[exif_timestamp_key] == "DateTime"
        exif_timestamp_str = image_obj.getexif()[exif_timestamp_key]
        timestamp = exif_timestamp_str
        exif_timestamp_fmt = "%Y:%m:%d %H:%M:%S"
        dt_obj = datetime.strptime(exif_timestamp_str, exif_timestamp_fmt)
        # grumble grumble
        #nicer_fmt = "%B %d, %Y at %I:%M %p"
        before_day = dt_obj.strftime("%B ")
        no_zero_padded_day = str(int(dt_obj.strftime("%d")))
        between_day_and_hour = dt_obj.strftime(", %Y at ")
        no_zero_padded_hour = str(int(dt_obj.strftime("%I")))
        after_hour = dt_obj.strftime(":%M %p")
        timestamp = before_day + no_zero_padded_day + between_day_and_hour + no_zero_padded_hour + after_hour

    # I'm puking
    with open(full_picture_path, "rb") as image_bytes:
        image_obj = ExifImage(image_bytes)
        try:
            latitude = decimal_coords(image_obj.gps_latitude, image_obj.gps_latitude_ref)
            longitude = decimal_coords(image_obj.gps_longitude, image_obj.gps_longitude_ref)

            # https://xkcd.com/2170/
            latitude = round(latitude, 4)
            longitude = round(longitude, 4)

            write_map_file(root, picture_filename, latitude, longitude)
            map_ = f"../../maps/{picture_filename}_map.png"
        except AttributeError:
            # No GPS info in this image
            map_ = None

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("view.html")
    content = tpl.render(
        headline=headline,
        filename=picture_filename,
        description=description,
        location=location,
        timestamp=timestamp,
        map_ = map_,
    )
    return content


def write_all_view_pages(root, annotator_metadata, all_used_pictures):
    for picture_filename in all_used_pictures:
        slug = picture_filename.split(".")[0]
        picture_metadata = annotator_metadata[picture_filename]
        content = render_view_page(root, slug, picture_filename, picture_metadata)
        view_dir_path = os.path.join(root, "view", slug)
        write_to_path(view_dir_path, INDEX_HTML, content)


def generate_thumbnail(orig_picture_path, thumbnail_path):
    cmd = ("convert", orig_picture_path, "-resize", "400x400>", "-quality", "80%", thumbnail_path)
    subprocess.run(cmd)


if __name__ == "__main__":
    # Figure out which tag(s) each picture belongs to
    annotator_json_path = sys.argv[1]
    with open(annotator_json_path) as fh:
        metadata = json.load(fh)
    by_tag = find_pictures_for_each_tag(metadata)

    # Generate the "Explore - pick a topic" page
    static_site_root_path = sys.argv[2]
    explore_dir = os.path.join(static_site_root_path, "explore")
    main_explore_page = render_main_explore_page()
    write_to_path(explore_dir, INDEX_HTML, main_explore_page)

    # Generate the "Engineering", "Erosion", etc pages
    write_all_topic_pages(static_site_root_path, metadata, by_tag)

    # Write CSS file
    css_path = os.path.join(static_site_root_path, CSS_FILE)
    shutil.copyfile(CSS_FILE, css_path)

    # Make images dir
    orig_picture_dir_path = sys.argv[3]
    new_picture_dir_path = os.path.join(static_site_root_path, "images")
    os.makedirs(new_picture_dir_path, exist_ok=True)

    # Copy over all used pictures and generate thumbnails
    all_used_pictures = set(list(itertools.chain(*list(by_tag.values()))))
    thumbnail_dir_path = os.path.join(static_site_root_path, "thumbnails")
    os.makedirs(thumbnail_dir_path, exist_ok=True)
    for picture in all_used_pictures:
        orig_picture_path = os.path.join(orig_picture_dir_path, picture)
        new_picture_path = os.path.join(new_picture_dir_path, picture)
        thumbnail_path = os.path.join(thumbnail_dir_path, picture)
        shutil.copyfile(orig_picture_path, new_picture_path)
        if not os.path.isfile(thumbnail_path):
            generate_thumbnail(orig_picture_path, thumbnail_path)

    # Generate the individual picture pages for all used pictures
    write_all_view_pages(static_site_root_path, metadata, all_used_pictures)

    # Copy over landing page
    landing_page_index_path = os.path.join(static_site_root_path, INDEX_HTML)
    shutil.copyfile("landing_page.html", landing_page_index_path)
