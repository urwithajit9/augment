#!flask/bin/python
# https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
from __future__ import division
from flask import Flask, jsonify
from flask import abort
from flask import request

from flask import make_response

app = Flask(__name__)
tasks = []
# @app.route('/todo/api/v1.0/tasks', methods=['GET'])
# def get_tasks():
#     return jsonify({'tasks': tasks})


from bs4 import BeautifulSoup
from bs4.element import Comment
from collections import Counter
import requests
from io import BytesIO
from PIL import Image
import justext
from goose import Goose


RANGE = 5000
def get_img_sources(img_tags):
    result = []
    for image in img_tags:
        result.append(image['src'])
    return result

# image size is only for a full url and not working with svg type
def get_image_size(src_url):

    req  = requests.get(src_url,headers={'User-Agent':'Mozilla5.0(Google spider)','Range':'bytes=0-{}'.format(RANGE)})
    im = Image.open(BytesIO(req.content))
    return im.size

def count_bigger_image(img_sources):
    BIG_IMAGE = 0
    for img_src in img_sources:
        try:
            width, height = get_image_size(img_src)
            if width >= 600 and height >= 400:
                BIG_IMAGE += 1
        except:
            continue
    return BIG_IMAGE

def get_text_in_links(soup):
    TOTAL_LINK_TEXT = 0
    for link in soup.find_all("a"):
        TOTAL_LINK_TEXT += len(link.text)
    return TOTAL_LINK_TEXT

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta','a', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    return u" ".join(t.strip() for t in visible_texts)

def calulate_link_to_text_ratio(soup,html):
    link_text = get_text_in_links(soup)
    text_length = len(text_from_html(html))
    return round(link_text / text_length,2)

def get_text_in_script(soup):
    TOTAL_SCRIPT_TEXT = 0
    for script in soup.find_all("script"):
        #print script.text
        TOTAL_SCRIPT_TEXT += len(script.text)
    return TOTAL_SCRIPT_TEXT

def calulate_text_to_script_ratio(soup,html):
    script_text = get_text_in_script(soup)
    text_length = len(text_from_html(html))
    return round( script_text/ text_length,2)

def get_body_text(input_url):
    g = Goose()
    article = g.extract(url=input_url)
    return len(article.cleaned_text)

def get_document_text(input_url_response):
    DOCUMENT_LENGTH = 0
    paragraphs = justext.justext(input_url_response.content, justext.get_stoplist("English"))
    for paragraph in paragraphs:
        DOCUMENT_LENGTH += len(paragraph.text)
    return DOCUMENT_LENGTH



def count_resources(in_url):
    response = requests.get(in_url)
    webpage = response.text
    soup = BeautifulSoup(webpage, "html.parser")
    foundUrls = Counter([link["href"] for link in soup.find_all("a", href=lambda href: href and not href.startswith("#"))])
    foundUrls = foundUrls.most_common()
    foundImgs = soup.find_all("img")
    img_srcs = get_img_sources(foundImgs)
    totalBigImages = count_bigger_image(img_srcs)
    foundAV = soup.find_all("audio") + soup.find_all("video")
    foundForm = soup.find_all("form")
    foundFormElements = soup.find_all("input") + soup.find_all("button")
    foundScripts = soup.find_all("script")
    totalLinkTextSize = get_text_in_links(soup)
    linkToTextRatio = calulate_link_to_text_ratio(soup,webpage)
    textToScriptRatio = calulate_text_to_script_ratio(soup,webpage)
    Ptext = get_document_text(response)
    MainText = get_body_text(in_url)
    P2M = round((Ptext - (Ptext - MainText)) / Ptext, 2)
    return {"Total_Urls":len(foundUrls),
            "Total_Images":len(foundImgs),
            "Total_AV": len(foundAV),
            "Total_Form":len(foundForm),
            "Total_Form_Elements": len(foundFormElements),
            "Total_Scripts": len(foundScripts),
            "Total_Big_img": totalBigImages,
            "Total_Link_Text_Size": totalLinkTextSize,
            "Link_to_Text_Ratio": linkToTextRatio,
            "Text_to_script_Ratio": textToScriptRatio,
            "P2M": P2M
            }



@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# @app.route('/augment/api/v1.0/pageclassification/<string:in_url>/<path:pathToFile>', methods=['GET'])
# def get_pageclassification(in_url,pathToFile):
#     print in_url, pathToFile
#     return jsonify({'url_length': calc_length(in_url,pathToFile)})
#
@app.route('/augment/api/v1.0/pageclassification', methods=['POST'])
def create_classification():
    if not request.json or not 'input_url' in request.json:
        abort(400)
    input_url = request.json['input_url']
    result = count_resources(input_url)
    return jsonify({'Url_length': len(input_url),
                    "Total links": result["Total_Urls"],
                    "Total images": result["Total_Images"],
                    "Total Audio Video": result["Total_AV"],
                    "Total Form": result["Total_Form"],
                    "Total Form Elements":result["Total_Form_Elements"],
                    "Total Scripts": result["Total_Scripts"],
                    "Total Big Images": result["Total_Big_img"],
                    "Text Size in Links": result["Total_Link_Text_Size"],
                    "Link to Text Ratio": result["Link_to_Text_Ratio"],
                    "Text to Script Ratio": result["Text_to_script_Ratio"],
                    "Page to Main Text Ratio": result["P2M"]
                    }), 201


if __name__ == '__main__':
    app.run(debug=True)
