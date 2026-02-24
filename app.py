from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from namekana import transliterate_name, UnknownCountryError

app = FastAPI(title="NameKana API", version="0.1.1")


class BulkIn(BaseModel):
    names: List[str]


@app.get("/healthz")
def healthz() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/transliterate")
def transliterate(name: str = Query(..., min_length=1, max_length=200)) -> Dict[str, Any]:
    try:
        return transliterate_name(name)
    except UnknownCountryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal_error:{type(e).__name__}")


@app.post("/bulk")
def bulk(payload: BulkIn) -> Dict[str, Any]:
    results = []
    for n in payload.names:
        try:
            results.append(transliterate_name(n))
        except Exception as e:
            results.append(
                {
                    "input": n,
                    "katakana": "",
                    "hiragana": "",
                    "source": "error",
                    "candidates": [],
                    "warning": f"internal_error:{type(e).__name__}",
                }
            )
    return {"count": len(results), "results": results}
