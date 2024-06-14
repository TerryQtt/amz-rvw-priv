from flask import Flask, request, render_template
import selectorlib
import requests
import json
from dateutil import parser as dateparser
import random

app = Flask(__name__, template_folder="templates")
extractor = selectorlib.Extractor.from_yaml_file('selectors.yml')
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
        "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edge/88.0.705.50"
    ]
    return random.choice(user_agents)
    
def scrape(url):
    headers = {
        'authority': 'www.amazon.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': get_random_user_agent(),
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    }

    # Download the page using requests
    print("Downloading %s" % url)
    r = requests.get(url, headers=headers)
    # Simple check to check if page was blocked (Usually 503)
    if r.status_code > 500:
        if "To discuss automated access to Amazon data please contact" in r.text:
            raise Exception("Page %s was blocked by Amazon. Please try using better proxies\n" % url)
        else:
            raise Exception("Page %s must have been blocked by Amazon as the status code was %d" % (url, r.status_code))

    # Pass the HTML of the page and create
    data = extractor.extract(r.text, base_url=url)

    # check if the extracted data is empty
    if data['reviews'] is None:
        raise Exception("ERROR: No data extracted. Check selector config")

    reviews = []
    for r in data['reviews']:
        r['rating'] = int(float(r['title'].split(' out of')[0]))
        r['title'] = r['title'].split(' out of 5 stars ')[-1]
        r['product'] = data['product_title']
        r['url'] = url
        if r['found_helpful'] is None:
            r['found_helpful'] = 0
        elif 'One person found this helpful' in r['found_helpful']:
            r['found_helpful'] = 1
        elif 'people found this helpful' in r['found_helpful']:
            r['found_helpful'] = int(r['found_helpful'].split()[0])
        else:
            r['found_helpful'] = 0
        if 'verified_purchase' in r and r['verified_purchase'] is not None:
            if 'Verified Purchase' in r['verified_purchase']:
                r['verified_purchase'] = True
            else:
                r['verified_purchase'] = False
        date_posted = r['date'].split('on ')[-1]
        if r['images']:
            r['images'] = "\n".join(r['images'])
        r['date'] = dateparser.parse(date_posted).strftime('%d %b %Y')
        reviews.append(r)
    data['reviews'] = reviews
    histogram = {}
    for h in data['histogram']:
        histogram[h['key']] = h['value']
    data['histogram'] = histogram
    data['average_rating'] = float(data['average_rating'].split(' out')[0])
    data['number_of_reviews'] = int(data['number_of_reviews'].split(' global ratings')[0].replace(',', ''))
    return data


def to_json(data, status=200):
    return json.dumps(data, indent=2), status, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/find', methods=["GET", "POST"])
def api():
    url = request.form["url"]
    pages = request.form["pages"]
    list = []
    for x in range(int(pages)):
        y=x+1
        newurl = url+"&pageNumber="+str(y)
        try:
            data = scrape(newurl)
            list.append(data)
        except Exception as e:
            return to_json({'error': str(e)}, 400)
    return to_json(list)
    

@app.route('/')
def home():
    return render_template("home.html")