#!/usr/bin/env python3
"""Associe uniquement les produits Transforverse identifiés sans ambiguïté."""
import json,re,urllib.request,datetime,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/'catalogue.json'
def norm(s):
    return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def get_products():
    products=[]
    for page in range(1,7):
        url=f'https://transforverse.eu/collections/blokees/products.json?limit=250&page={page}'
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 Catalogue collection personnel'})
        with urllib.request.urlopen(req,timeout=30) as r: data=json.load(r)
        batch=data.get('products',[])
        products.extend(batch)
        if len(batch)<250:break
    return products
def match(item,products):
    name=norm(item['name']);series=norm(item['series']);num=str(item.get('seriesNumber') or '').lstrip('0')
    candidates=[]
    for p in products:
        title=norm(p.get('title',''))
        if not all(w in title.split() for w in name.split()):continue
        if series=='classic class' and 'classic class' not in title:continue
        if series!='classic class' and series not in title:continue
        if num and not re.search(r'(?<!\d)0*'+re.escape(num)+r'(?!\d)',title):continue
        candidates.append(p)
    return candidates[0] if len(candidates)==1 else None

def main():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    products=get_products()
    updated=0
    for item in data['items']:
        p=match(item,products)
        if not p:continue
        images=p.get('images') or []
        src=images[0].get('src') if images else None
        if not src:continue
        if not src.startswith('https://'):continue
        item['image']=src
        item['productUrl']='https://transforverse.eu/products/'+p['handle']
        updated+=1
    data['imagesUpdatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    data['imagesMatched']=updated
    PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{updated} photos associées sur {len(data["items"])} fiches; les autres restent à vérifier')
if __name__=='__main__':main()
