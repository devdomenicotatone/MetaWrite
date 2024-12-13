import os
import requests
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import openai

app = FastAPI()

# Leggiamo le variabili d'ambiente
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID or not OPENAI_API_KEY:
    raise RuntimeError("Mancano le variabili d'ambiente: GOOGLE_API_KEY, GOOGLE_CSE_ID o OPENAI_API_KEY non impostate.")

openai.api_key = OPENAI_API_KEY

@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI with Google CSE and OpenAI!"}

@app.get("/search")
def perform_search(query: str):
    """
    Effettua una ricerca su Google Custom Search API.
    Parametro: query (string)
    Ritorna: risultati della ricerca in JSON
    """
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
    Ritorna il testo estratto come stringa.
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

@app.get("/first_result_url")
def get_first_result_url(query: str):
    """
    Ritorna l'URL del primo risultato della ricerca.
    Utile per testare se la ricerca funziona e se estrai correttamente il primo link.
    """
    search_results = perform_search(query=query)
    items = search_results.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Nessun risultato trovato per la query.")
    first_url = items[0].get("link")
    if not first_url:
        raise HTTPException(status_code=404, detail="Nessun URL valido trovato nel primo risultato.")
    return {"first_url": first_url}

@app.get("/scrape")
def scrape_endpoint(url: str):
    """
    Endpoint per testare lo scraping.
    Passa un URL e verrà restituito il testo estratto.
    """
    text = scrape_article(url)
    if not text:
        raise HTTPException(status_code=500, detail="Non è stato possibile estrarre il contenuto dal sito.")
    return {"url": url, "scraped_text": text[:500] + "..."}  # Limito a 500 caratteri per brevità

@app.post("/generate_article")
def generate_article(query: str):
    """
    Usa la query per cercare un articolo, ne effettua lo scraping del primo risultato
    e poi invia il contenuto a OpenAI per generare un nuovo articolo.
    """
    # 1. Faccio una ricerca
    search_results = perform_search(query=query)
    items = search_results.get("items", [])

    if not items:
        raise HTTPException(status_code=404, detail="Nessun risultato trovato per la query.")

    # Prendiamo il primo risultato come esempio
    first_url = items[0].get("link")
    if not first_url:
        raise HTTPException(status_code=404, detail="Nessun URL valido trovato.")

    # 2. Scraping del contenuto
    original_text = scrape_article(first_url)
    if not original_text:
        raise HTTPException(status_code=500, detail="Non è stato possibile estrarre il contenuto dal sito.")

    # 3. Generazione dell'articolo con OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sei un assistente che crea articoli chiari e veritieri."},
                {"role": "user", "content": f"Genera un nuovo articolo basato su queste informazioni:\n{original_text}\nCrea un testo originale e ben strutturato."}
            ]
        )
        generated_article = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione dell'articolo: {e}")

    return {"url_utilizzata": first_url, "articolo_generato": generated_article}

@app.get("/test_openai")
def test_openai():
    """
    Test semplice per verificare la connessione con OpenAI.
    Invia un semplice prompt e riceve una risposta.
    """
    prompt = "Dimmi qualcosa di interessante sull'Italia."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sei un assistente informativo."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella richiesta a OpenAI: {e}")

    return {"prompt": prompt, "response": answer}
