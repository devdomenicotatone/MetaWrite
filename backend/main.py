import os
import requests
import logging
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import perform_search, scrape_article
import openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY non impostata.")
    raise RuntimeError("OPENAI_API_KEY non impostata.")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    logger.error("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")
    raise RuntimeError("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")

openai.api_key = OPENAI_API_KEY

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateArticleRequest(BaseModel):
    query: str

def summarize_text(full_text: str, query: str) -> str:
    """Riassume il testo estratto in ~300 token per ridurre il contesto."""
    if len(full_text) > 2000:
        full_text = full_text[:2000]
    prompt_summary = (
        f"Riassumi in modo completo, chiaro e conciso il seguente testo relativo a '{query}'. "
        "Fornisci un riassunto dettagliato in non più di 300 token, includendo le informazioni chiave "
        "ma senza citare fonti o URL. Deve essere un testo informativo che coglie i punti salienti.\n\n"
        f"Testo:\n{full_text}\n\nRiassunto:"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", # Usa gpt-4 se disponibile
            messages=[
                {"role": "system", "content": "Sei un assistente che riassume testi."},
                {"role": "user", "content": prompt_summary}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        summary = response.choices[0].message.content
        return summary.strip()
    except Exception as e:
        logger.error(f"Error during summary generation: {e}")
        return ""

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World from FastAPI!"}

@app.get("/search")
def search_endpoint(query: str):
    if not query.strip():
        logger.warning("Empty query received in /search endpoint")
        raise HTTPException(status_code=400, detail="La query di ricerca non può essere vuota.")

    logger.info(f"Search endpoint called with query: {query}")
    try:
        data = perform_search(query)
        return data
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la ricerca")

@app.post("/generate_article")
def generate_article(payload: GenerateArticleRequest):
    query = payload.query.strip()
    if not query:
        logger.warning("Empty query received")
        raise HTTPException(status_code=400, detail="La query di ricerca non può essere vuota.")

    logger.info(f"generate_article endpoint called with query: {query}")

    try:
        search_results = perform_search(query=query)
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la ricerca")

    items = search_results.get("items", [])
    if not items:
        logger.warning("No results found for the query")
        raise HTTPException(status_code=404, detail="Nessun risultato trovato per la query.")

    top_items = items[:5]
    logger.info(f"Processing top {len(top_items)} results")

    summaries = []
    for index, item in enumerate(top_items, start=1):
        link = item.get("link")
        if not link:
            logger.warning(f"Result {index} has no valid link, skipping")
            continue
        logger.info(f"Scraping result {index}: {link}")
        article_text = scrape_article(link)
        if article_text:
            logger.info(f"Summarizing article {index} text of length {len(article_text)}")
            summary = summarize_text(article_text, query)
            if summary:
                summaries.append(summary)
            else:
                logger.warning(f"No summary generated for article {index}")
        else:
            logger.warning(f"No relevant text extracted from article {index}")

    if not summaries:
        logger.error("No summaries could be generated from the top results")
        raise HTTPException(status_code=500, detail="Non è stato possibile estrarre contenuti rilevanti.")

    combined_summary = "\n\n".join(summaries)
    logger.info(f"Total combined summary length: {len(combined_summary)} chars")

    prompt_message = (
        f"Sei un esperto redattore di articoli professionali. "
        f"Utilizzando le informazioni riassunte dai seguenti testi riguardanti '{query}', "
        "crea un articolo originale, molto completo, ben organizzato, con titoli e sottotitoli chiari. "
        "Descrivi dettagliatamente le caratteristiche del luogo, le differenze tra le diverse aree, "
        "le normative di comportamento o le consuetudini, consigli pratici per i visitatori, il clima, "
        "il contesto culturale e geografico, e qualsiasi altra informazione utile. "
        "Non citare fonti, URL o siti specifici. Il testo deve essere lungo e approfondito, "
        "con un tono informativo e coerente. Ecco i riassunti analizzati:\n"
        f"{combined_summary}\n\n"
        "Ora produci un articolo finale coerente, dettagliato e ben strutturato, "
        "senza menzionare alcun riferimento a siti o fonti, ma integrando tutte le informazioni."
    )

    try:
        logger.info("Sending request to OpenAI for article generation with summarized content")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un assistente che crea contenuti informativi e ben strutturati."},
                {"role": "user", "content": prompt_message}
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        generated_article = response.choices[0].message.content
        logger.info("Article generation completed successfully")
    except Exception as e:
        logger.error(f"Error generating article: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella generazione dell'articolo: {e}")

    return {
        "articolo_generato": generated_article
    }
