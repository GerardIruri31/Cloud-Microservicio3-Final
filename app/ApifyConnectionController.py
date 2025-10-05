import apify_client
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List,Dict, Any
from tiktok_metrics_processor import transform_items
# al inicio de tus imports
from db_mongo import ensure_indexes
from contextlib import asynccontextmanager
from db_mongo import get_collection
from db_mongo import get_collection_by
from queries_controller import router as queries_router
from models import ApifyRequest, InsertResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    yield

app = FastAPI(lifespan=lifespan,
    title="TikTok Metrics API",
    description="API para obtener y consultar métricas de TikTok usando Apify",
    version="1.0.0")

# Habilitar CORS en FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queries_router)


async def fetch_data(run_input):
    try:
        print(run_input)
        run_input.pop("userId", None)
        run_input.pop("adminId", None)
        client = apify_client.ApifyClient(run_input["apifyToken"])
        run_input.pop("apifyToken",None)
        loop = asyncio.get_event_loop()
        run = await loop.run_in_executor(None, lambda: client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input))
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return {"onError": {"error": "datasetId not found on the Apify response"}}
        data = await loop.run_in_executor(None, lambda: list(client.dataset(dataset_id).iterate_items()))
        return {"Success": data}
    except Exception as ApifyApiError:
        print("Error: " + str(ApifyApiError))
        # Pasa cuando no hay ningún post que hagan match con filtros envíados 
        return {"Error": str(ApifyApiError)}
    


@app.post("/apify-connection/normalized",response_model=InsertResponse,
    summary="Obtener métricas de TikTok para usuario",
    description="Obtiene métricas de TikTok desde Apify por username y las guarda en la colección de usuario")
async def fetch_and_save_tiktok_data(request: ApifyRequest):
    raw = await fetch_data(request.model_dump(exclude_none=True))
    if "Success" not in raw:
        raise HTTPException(status_code=502, detail=raw)
    normalized: List[Dict[str, Any]] = transform_items(
        raw,
        username_fallback=request.profiles[0] if request.profiles else None,
        user_id=request.userId
    )
    if not normalized:
        return InsertResponse(inserted=0, data=[])
    coll = get_collection()
    docs_to_insert = [doc.copy() for doc in normalized]
    result = await coll.insert_many(docs_to_insert)
    return InsertResponse(
        inserted=len(result.inserted_ids),
        data=normalized
    )



@app.post("/apify-connection/admin/normalized",response_model=InsertResponse,
    summary="Obtener métricas de TikTok para admin",
    description="Obtiene métricas de TikTok desde Apify (username, hashtags o keywords) y las guarda en la colección de admin. Retorna Top 5 por hashtag ordenado por views.")
async def fetch_and_save_tiktok_data_admin(request: ApifyRequest):
    # 1) trae datos crudos de Apify
    raw = await fetch_data(request.model_dump(exclude_none=True))
    if "Success" not in raw:
        raise HTTPException(status_code=502, detail=raw)

    # 2) normaliza (sin userId)
    normalized: List[Dict[str, Any]] = transform_items(
        raw,
        username_fallback=request.profiles[0] if request.profiles else None,
        user_id=None
    )

    # 3) setea adminId y limpia userId
    admin_id = request.adminId
    for doc in normalized:
        doc["adminId"] = admin_id if admin_id is not None else "N/A"
        doc.pop("userId", None)

    # 4) inserta en AdminTiktokMetrics SIN contaminar la respuesta con ObjectId
    if not normalized:
        return InsertResponse(inserted=0, data=[])
    coll = get_collection_by("AdminTiktokMetrics")
    docs_to_insert = [d.copy() for d in normalized]
    result = await coll.insert_many(docs_to_insert)

    # ======== ORDEN ÚNICO: Top 5 por cada hashtag del body, concatenado ========
    TOP_N = 5

    def _split_csv(s: Any) -> List[str]:
        if not isinstance(s, str):
            return []
        return [p.strip() for p in s.split(",") if p.strip()]

    def _norm_tag(t: str) -> str:
        t = t.strip().lower()
        return t if t.startswith("#") else f"#{t}"

    def _has_hashtag(doc: Dict[str, Any], tag: str) -> bool:
        # hashtags viene como string con espacios: "#a #b #c"
        hs = (doc.get("hashtags") or "").lower().split()
        return tag in hs

    ordered: List[Dict[str, Any]] = []
    hashtags_param = request.hashtags
    if hashtags_param:
        if isinstance(hashtags_param, list):
            hashtags_str = ",".join(hashtags_param)
        else:
            hashtags_str = hashtags_param
        tags_req = _split_csv(hashtags_str)
    else:
        tags_req = []

    if tags_req:
        tags_norm = [_norm_tag(t) for t in tags_req]
        seen_post_ids: set[str] = set()
        for tag in tags_norm:
            subset = [
                d for d in normalized
                if _has_hashtag(d, tag) and str(d.get("postId")) not in seen_post_ids
            ]
            subset.sort(key=lambda x: int(x.get("views") or 0), reverse=True)
            top = subset[:TOP_N]
            ordered.extend(top)
            for d in top:
                pid = str(d.get("postId"))
                if pid:
                    seen_post_ids.add(pid)
    else:
        # si no mandan hashtags, devolvemos todo ordenado por views desc
        ordered = sorted(normalized, key=lambda x: int(x.get("views") or 0), reverse=True)

    # 5) Respuesta ÚNICA: inserted + data (lista única ya ordenada)
    return InsertResponse(
        inserted=len(result.inserted_ids),
        data=ordered
    )

@app.get("/") 
async def healthy():
    return {"status":"up"}
