#!/usr/bin/env python3
"""Met à jour le catalogue Blokees depuis la collection publique Transforverse.

Conserve les fiches existantes. Les nouveaux produits sont ajoutés uniquement si
leur identification comme produit Blokees Transformers est raisonnablement claire.
Les prix et promotions sont des instantanés de la boutique, pas une garantie.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.request
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / 'catalogue.json'
BASE = 'https://transforverse.eu'
COLLECTION = BASE + '/collections/blokees/products.json?limit=250&page={}'


def normaliser(texte):
    texte = unicodedata.normalize('NFKD', str(texte or ''))
    texte = ''.join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texte.lower()).strip()


def recuperer_produits():
    resultats = []
    for page in range(1, 7):
        req = urllib.request.Request(COLLECTION.format(page), headers={
            'User-Agent': 'Mozilla/5.0 (catalogue personnel Blokees)'
        })
        with urllib.request.urlopen(req, timeout=30) as reponse:
            donnees = json.load(reponse)
        lot = donnees.get('products', [])
        resultats.extend(lot)
        if len(lot) < 250:
            break
    return resultats


def correspondance(fiche, produit):
    titre = normaliser(produit.get('title'))
    nom = normaliser(fiche.get('name') or fiche.get('nom'))
    serie = normaliser(fiche.get('series') or fiche.get('série'))
    numero = str(fiche.get('seriesNumber') or fiche.get('numéro de série') or '').lstrip('0')
    if not nom or not all(mot in titre.split() for mot in nom.split()):
        return False
    if serie == 'classic class' and 'classic class' not in titre:
        return False
    if serie and serie != 'classic class' and serie not in titre:
        return False
    if numero and not re.search(r'(?<!\d)0*' + re.escape(numero) + r'(?!\d)', titre):
        return False
    return True


def prix_variante(produit):
    variantes = produit.get('variants') or []
    prix = []
    reductions = []
    for variante in variantes:
        try:
            montant = float(variante['price'])
            prix.append(montant)
            ancien = variante.get('compare_at_price')
            if ancien is not None and float(ancien) > montant:
                reductions.append(True)
        except (ValueError, TypeError, KeyError):
            continue
    # Prix non publié si plusieurs variantes ont des prix différents.
    return (prix[0] if prix and len(set(prix)) == 1 else None,
            bool(reductions) if prix else None)


def image_produit(produit):
    images = produit.get('images') or []
    url = images[0].get('src', '') if images else ''
    return url if url.startswith('https://') else None


def est_blokees_transformers(produit):
    titre = normaliser(produit.get('title'))
    tags = normaliser(produit.get('tags'))
    # Le catalogue source est la collection Blokees; exiger Transformers
    # dans le titre ou les étiquettes avant d'ajouter une nouvelle fiche.
    return 'transformers' in titre.split() or 'transformers' in tags.split()


def main():
    donnees = json.loads(CATALOGUE.read_text(encoding='utf-8'))
    cle = 'items' if isinstance(donnees.get('items'), list) else 'articles'
    fiches = donnees[cle]
    produits = recuperer_produits()
    aujourd_hui = dt.datetime.now(dt.timezone.utc).date().isoformat()
    existants = {str(f.get('productUrl') or f.get('productUrl', '')).rstrip('/') for f in fiches}
    nouveaux = 0
    mis_a_jour = 0

    for fiche in fiches:
        candidats = [p for p in produits if correspondance(fiche, p)]
        if len(candidats) != 1:
            continue
        produit = candidats[0]
        url = BASE + '/products/' + produit['handle']
        image = image_produit(produit)
        prix, promo = prix_variante(produit)
        if image:
            fiche['image'] = image
        fiche['productUrl'] = url
        if prix is not None:
            fiche['price'] = prix
            fiche['priceCheckedAt'] = aujourd_hui
            fiche['promo'] = promo
        existants.add(url.rstrip('/'))
        mis_a_jour += 1

    for produit in produits:
        url = BASE + '/products/' + produit.get('handle', '')
        if not produit.get('handle') or url.rstrip('/') in existants:
            continue
        if not est_blokees_transformers(produit):
            continue
        # Évite de créer des doublons sur les produits déjà présents sans URL.
        if any(correspondance(fiche, produit) for fiche in fiches):
            continue
        prix, promo = prix_variante(produit)
        titre = produit.get('title', '').strip()
        nouvelle = {
            'id': 'transforverse-' + str(produit['id']),
            'name': titre,
            'series': 'À classer',
            'seriesNumber': '',
            'sku': None,
            'price': prix,
            'priceCheckedAt': aujourd_hui if prix is not None else None,
            'availability': 'À vérifier',
            'new': True,
            'promo': promo if promo is not None else False,
            'image': image_produit(produit) or '',
            'productUrl': url,
            'alternateUrl': '',
            'alternatePrice': None,
        }
        fiches.append(nouvelle)
        existants.add(url.rstrip('/'))
        nouveaux += 1

    donnees['updatedAt'] = aujourd_hui
    donnees['sourceCheckedAt'] = dt.datetime.now(dt.timezone.utc).isoformat()
    CATALOGUE.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{mis_a_jour} fiches actualisées, {nouveaux} nouveaux produits, {len(fiches)} fiches au total')
    print('Les promotions sont déduites des prix barrés de la boutique; vérification humaine conseillée.')


if __name__ == '__main__':
    main()
