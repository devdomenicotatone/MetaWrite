import os
import openai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils import perform_search, scrape_article

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY non impostata.")

openai.api_key = OPENAI_API_KEY

# Configurazione CORS per consentire richieste dal frontend ospitato su altro dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puoi limitare al dominio del tuo frontend se vuoi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI on Render!"}

@app.get("/search")
def search_endpoint(query: str):
    data = perform_search(query)
    return data

@app.post("/generate_article")
def generate_article(query: str):
    search_results = perform_search(query=query)
    items = search_results.get("items", [])

    if not items:
        raise HTTPException(status_code=404, detail="Nessun risultato trovato per la query.")

    first_url = items[0].get("link")
    if not first_url:
        raise HTTPException(status_code=404, detail="Nessun URL valido trovato.")

    original_text = scrape_article(first_url)
    if not original_text:
        raise HTTPException(status_code=500, detail="Non è stato possibile estrarre il contenuto dal sito.")

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

    return {
        "url_utilizzata": first_url,
        "articolo_generato": generated_article
    }
