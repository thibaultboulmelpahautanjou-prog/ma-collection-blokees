#!/usr/bin/env python3
"""Complète les photos du catalogue à partir des produits Transforverse vérifiés.

Ne remplace pas une photo existante et refuse les correspondances ambiguës.
"""
import datetime
import json
import pathlib
import re
import urllib.request
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / 'catalogue.json'
STORE = 'https://transforverse.eu'

ALIASES = {
    'rotf': 'revenge of the fallen',
    'dotm': 'dark of the moon',
    'tf one': 'transformers one',
}
STOP_WORDS = {'transformers', 'blokees', 'model', 'kit', 'figure', 'figurine', 'the'}


def norm(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    value = ''.join(c for c in value if not unicodedata.combining(c)).lower()
    value = re.sub(r'[^a-z0-9]+', ' ', value).strip()
    for short, full in ALIASES.items():
        value = re.sub(r'\b' + re.escape(short) + r'\b', full, value)
    return re.sub(r'\s+', ' ', value).strip()


def words(value):
    return set(norm(value).split()) - STOP_WORDS


def get_products():
    products = []
    for page in range(1, 7):
        url = f'{STORE}/collections/blokees/products.json?limit=250&page={page}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Catalogue collection personnel'})
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response).get('products', [])
        products.extend(batch)
        if len(batch) < 250:
            break
    return products


def match(item, products):
    name_words = words(item.get('name', ''))
    series_words = words(item.get('series', ''))
    number = str(item.get('seriesNumber') or '').strip().lstrip('0')
    if not name_words or not series_words:
        return None
    candidates = []
    for product in products:
        title = norm(product.get('title', ''))
        title_words = set(title.split())
        if not name_words.issubset(title_words):
            continue
        if not series_words.issubset(title_words):
            continue
        if number and not re.search(r'(?<!\d)0*' + re.escape(number) + r'(?!\d)', title):
            continue
        candidates.append(product)
    return candidates[0] if len(candidates) == 1 else None


def main():
    data = json.loads(PATH.read_text(encoding='utf-8'))
    products = get_products()
    updated = 0
    unresolved = []
    for item in data['items']:
        if item.get('image'):
            continue
        product = match(item, products)
        if not product:
            unresolved.append(item.get('name', 'Sans nom'))
            continue
        images = product.get('images') or []
        src = images[0].get('src') if images else None
        handle = product.get('handle')
        if not isinstance(src, str) or not src.startswith('https://') or not handle:
            unresolved.append(item.get('name', 'Sans nom'))
            continue
        item['image'] = src
        item['productUrl'] = f'{STORE}/products/{handle}'
        updated += 1
    data['imagesUpdatedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data['imagesMatched'] = sum(bool(item.get('image')) for item in data['items'])
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{updated} nouvelles photos ; {data["imagesMatched"]} fiches avec photo sur {len(data["items"])}')
    if unresolved:
        print('Photos non trouvées ou correspondances ambiguës : ' + ', '.join(unresolved))


if __name__ == '__main__':
    main()
