import { useState } from 'react';

export default function Home() {
  const [query, setQuery] = useState("");
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const backendUrl = "https://metawrite.onrender.com";

  const handleGenerateArticle = async () => {
    setLoading(true);
    setError(null);
    setArticle(null);

    try {
      const res = await fetch(`${backendUrl}/generate_article`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Errore nella generazione dell'articolo");
      }

      const data = await res.json();
      setArticle(data);
    } catch (err) {
      setError(err.message || "Errore sconosciuto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{padding: "20px", fontFamily: "Arial, sans-serif"}}>
      <h1>MetaWrite - Generatore di Articoli</h1>
      <p>Inserisci una query di ricerca e genera un articolo originale basato sulle informazioni trovate online.</p>

      <div style={{marginBottom: "20px"}}>
        <input 
          type="text" 
          value={query} 
          onChange={(e) => setQuery(e.target.value)} 
          placeholder="Ad es. 'Intelligenza Artificiale' " 
          style={{padding: "10px", width: "300px"}}
        />
        <button 
          onClick={handleGenerateArticle} 
          style={{padding: "10px 20px", marginLeft: "10px"}}
        >
          Genera Articolo
        </button>
      </div>

      {loading && <p>Generazione in corso...</p>}
      {error && <p style={{color: "red"}}>Errore: {error}</p>}
      {article && (
        <div style={{border: "1px solid #ccc", padding: "20px"}}>
          <h2>Articolo Generato</h2>
          <p><strong>Fonte utilizzata:</strong> <a href={article.url_utilizzata} target="_blank" rel="noreferrer">{article.url_utilizzata}</a></p>
          <div style={{whiteSpace: "pre-wrap"}}>{article.articolo_generato}</div>
        </div>
      )}
    </div>
  );
}