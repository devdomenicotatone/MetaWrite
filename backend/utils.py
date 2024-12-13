import os
import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def perform_search(query: str):
    """
    Effettua una ricerca su Google Custom Search API.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise RuntimeError("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
    }

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Errore nella ricerca")

    data = resp.json()
    return data

def scrape_article(url: str) -> str:
    """
    Effettua lo scraping del contenuto testuale di un articolo da un URL.
    """
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(e)
        return ""

    soup = BeautifulSoup(r.text, 'html.parser')
    paragraphs = soup.find_all('p')
    text = " ".join(p.get_text() for p in paragraphs if p.get_text().strip())
    return text
