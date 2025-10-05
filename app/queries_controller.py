# queries_controller.py
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, APIRouter
from datetime import datetime
from db_mongo import get_collection, get_collection_by
from models import QueryRequest, QueryResponse

router = APIRouter()

# ---- helpers (igual que ya tienes) ----
def _split_csv(s: Optional[str]) -> List[str]:
    if not isinstance(s, str):
        return []
    return [p.strip() for p in s.split(",") if p.strip()]

def _add_in(match: Dict[str, Any], field: str, csv: Optional[str]):
    vals = _split_csv(csv)
    if vals:
        match[field] = {"$in": vals}

def _add_range(match: Dict[str, Any], field: str, min_v: Optional[float], max_v: Optional[float]):
    cond = {}
    if min_v is not None: cond["$gte"] = min_v
    if max_v is not None: cond["$lte"] = max_v
    if cond:
        match[field] = cond

def _build_match_from_request(req: Dict[str, Any], id_field_name: str = "userId") -> Dict[str, Any]:
    match: Dict[str, Any] = {}
    if req.get(id_field_name) is not None:
        match[id_field_name] = req[id_field_name]
    _add_in(match, "postId", req.get("postId"))
    _add_in(match, "postURL", req.get("postURL"))
    _add_in(match, "usernameTiktokAccount", req.get("tiktokUsernames"))
    _add_in(match, "regionPost", req.get("regionPost"))
    _add_in(match, "soundId", req.get("soundId"))
    _add_in(match, "soundURL", req.get("soundURL"))
    if req.get("datePostedFrom"):
        match.setdefault("datePosted", {})["$gte"] = req["datePostedFrom"]
    if req.get("datePostedTo"):
        match.setdefault("datePosted", {})["$lte"] = req["datePostedTo"]
    tags = _split_csv(req.get("hashtags"))
    if tags:
        ors = []
        for t in tags:
            t_norm = t if t.startswith("#") else f"#{t}"
            ors.append({"hashtags": {"$regex": rf"(^|\s){t_norm}(\s|$)", "$options": "i"}})
        match["$or"] = ors
    _add_range(match, "views", req.get("minViews"), req.get("maxViews"))
    _add_range(match, "likes", req.get("minLikes"), req.get("maxLikes"))
    _add_range(match, "totalInteractions", req.get("minTotalInteractions"), req.get("maxTotalInteractions"))
    _add_range(match, "engagement", req.get("minEngagement"), req.get("maxEngagement"))
    return match

def _dto_strip_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "_id"}

_DOW_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

def _compute_dashboard(docs: List[Dict[str, Any]], req: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calcula métricas de dashboard básicas"""
    dash: List[Dict[str, Any]] = []
    if not docs:
        return dash
    
    # Métricas totales
    total_views = sum(d.get("views", 0) for d in docs)
    total_likes = sum(d.get("likes", 0) for d in docs)
    total_comments = sum(d.get("comments", 0) for d in docs)
    total_interactions = sum(d.get("totalInteractions", 0) for d in docs)
    avg_engagement = sum(d.get("engagement", 0) for d in docs) / len(docs) if docs else 0
    
    dash.append({
        "metric": "totals",
        "totalPosts": len(docs),
        "totalViews": total_views,
        "totalLikes": total_likes,
        "totalComments": total_comments,
        "totalInteractions": total_interactions,
        "avgEngagement": round(avg_engagement, 4)
    })
    
    return dash

@router.post("/dbquery/user",response_model=QueryResponse,
    summary="Consultar métricas de usuario",
    description="Consulta las métricas almacenadas en la base de datos para un usuario específico con múltiples filtros opcionales")
async def dbquery_user(req: QueryRequest):
    coll = get_collection()
    match = _build_match_from_request(req.model_dump(exclude_none=True), id_field_name="userId")

    pipeline = [
        {"$match": match},
        {"$sort": {"_id": -1}},
        {"$group": {"_id": "$postId", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"datePosted": -1, "hourPosted": -1}},
    ]
    items = await coll.aggregate(pipeline).to_list(10_000)
    items = [_dto_strip_id(d) for d in items]
    dashboard = _compute_dashboard(items, req.model_dump(exclude_none=True))
    return QueryResponse(
        items=items, 
        count=len(items), 
        dashboard=dashboard
    )

@router.post("/dbquery/admin",response_model=QueryResponse,
    summary="Consultar métricas de admin",
    description="Consulta las métricas almacenadas en la base de datos para un administrador con múltiples filtros opcionales")
async def dbquery_admin(req: QueryRequest):
    coll = get_collection_by("AdminTiktokMetrics")
    match = _build_match_from_request(req.model_dump(exclude_none=True), id_field_name="adminId")

    pipeline = [
        {"$match": match},
        {"$sort": {"_id": -1}},
        {"$group": {"_id": "$postId", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"datePosted": -1, "hourPosted": -1}},
    ]
    items = await coll.aggregate(pipeline).to_list(10_000)
    items = [_dto_strip_id(d) for d in items]
    dashboard = _compute_dashboard(items, req.model_dump(exclude_none=True))
    
    return QueryResponse(
        items=items, 
        count=len(items), 
        dashboard=dashboard
    )
