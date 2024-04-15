from datetime import datetime
from bs4 import BeautifulSoup, Tag
from fastapi import FastAPI, Response
import requests
import rfeed
import xml.etree.ElementTree as ET


def format_fap_date(date: str):
    date_list = date.split(" ")[0].split("/")
    date_list.reverse()

    return " ".join(["-".join(date_list), date.split(" ")[1].replace("h", ":")])


def format_enem_date(date: str):
    date_list = date.split("/")
    date_list.reverse()

    return "-".join(date_list) + " 00:00"


def get_fap_news():
    url = 'https://fap.curitiba2.unespar.edu.br/noticias/ultimas-noticias'
    res = requests.get(url)
    html_page = res.text

    soup = BeautifulSoup(html_page, 'html.parser')

    items = soup.select("#content-core > .item.visualIEFloatFix")

    _items = []

    item: Tag
    for item in items:
        pbat = item.select_one(
            '.documentPublished [property="rnews:datePublished"]').get_text()
        mbat = item.select_one(
            '.documentModified [property="rnews:dateModified"]').get_text()
        headline = item.select_one(".headline a")

        _items.append({
            "title": headline.get_text(),
            "link": headline['href'],
            "publishedAt": format_fap_date(pbat),
            "modifiedAt": format_fap_date(mbat)
        })

    return _items


def get_enem_news():
    url = 'https://www.gov.br/inep/pt-br/assuntos/noticias/enem'
    res = requests.get(url)
    html_page = res.text

    soup = BeautifulSoup(html_page, 'html.parser')

    items = soup.select(".noticias.listagem-noticias-com-foto > li")

    _items = []

    item: Tag
    for item in items:
        description = item.select_one(
            ".descricao").contents[4].get_text().replace("\n", "").strip()
        date = item.select_one(
            ".descricao span:nth-child(1)").get_text().replace("\n", "").strip()
        title = item.select_one(".conteudo .titulo a")

        _items.append({
            "title": title.get_text(),
            "description": description,
            "publishedAt": format_enem_date(date),
            "image": item.select_one(".imagem img")['src'].replace("/@@images/image/mini", ""),
            "link": title['href'],
        })

    return _items


def get_utfpr_news():
    url = 'https://www.utfpr.edu.br/++api++/noticias/geral/@search?b_size=15&fullobjects=true&portal_type:list=News%20Item&portal_type:list=Not%C3%ADcia&sort_on=effective&sort_order=reverse'
    res = requests.get(url, verify=False)
    data = res.json()

    _items = []

    for item in data['items']:
        _items.append({
            "title": item['title'],
            "description": item['description'],
            "publishedAt": item['effective'],
            "modifiedAt": item['modified'],
            "link": item['@id'],
            "image": item['image']['download']
        })

    return _items


def create_feed():
    _items = []

    for item in get_fap_news():
        _items.append(rfeed.Item(
            title=item['title'],
            link=item['link'],
            pubDate=datetime.fromisoformat(item['publishedAt']),
            author="FAP",
            guid=rfeed.Guid(item['link']),
        ))

    for item in get_enem_news():
        _items.append(rfeed.Item(
            title=item['title'],
            link=item['link'],
            description=item['description'],
            pubDate=datetime.fromisoformat(item['publishedAt']),
            author="ENEM",
            guid=rfeed.Guid(item['link']),
            enclosure=rfeed.Enclosure(url=item['image'], type=f"image/{"jpeg" if item['image'].endswith(
                ".jpg") else "png" if item['image'].endswith(".png") else item['image'].split('.')[-1]}", length=0)
        ))

    for item in get_utfpr_news():
        _items.append(rfeed.Item(
            title=item['title'],
            link=item['link'],
            description=item['description'],
            pubDate=datetime.fromisoformat(item['publishedAt']),
            author="UTFPR",
            guid=rfeed.Guid(item['link']),
            enclosure=rfeed.Enclosure(url=item['image'], type=f"image/{"jpeg" if item['image'].endswith(
                ".jpg") else "png" if item['image'].endswith(".png") else item['image'].split('.')[-1]}", length=0)
        ))

    feed = rfeed.Feed(title="Facul Noticias",
                      description="Noticias da UTFPR, FAP e Enem",
                      language="pt-BR",
                      items=_items,
                      link="https://fap.curitiba2.unespar.edu.br/"
                      )

    return feed.rss()


app = FastAPI()


@app.get("/")
async def root():
    return Response(content=ET.ElementTree(ET.fromstring(create_feed())), media_type="application/xml")
