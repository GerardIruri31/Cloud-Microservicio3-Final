from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ApifyRequest(BaseModel):
    apifyToken: str = Field(..., description="Token de Apify")
    profiles: Optional[List[str]] = Field(None, description="Usernames de TikTok")
    searchQueries: Optional[List[str]] = Field(None, description="Keywords para buscar")
    hashtags: Optional[List[str]] = Field(None, description="Hashtags para buscar")
    resultsPerPage: Optional[int] = Field(100, description="Número de resultados por página")
    excludePinnedPosts: Optional[bool] = Field(True, description="Excluir posts fijados")
    newestPostDate: Optional[str] = Field(None, description="Fecha más reciente (YYYY-MM-DD)")
    oldestPostDate: Optional[str] = Field(None, description="Fecha más antigua (YYYY-MM-DD)")
    profileSorting: Optional[str] = Field(None, description="Ordenamiento de perfiles (e.g., 'latest')")
    userId: Optional[int] = Field(None, description="ID del usuario (para endpoint /normalized)")
    adminId: Optional[int] = Field(None, description="ID del admin (para endpoint /admin/normalized)")


class MetricOut(BaseModel):
    postId: str
    datePosted: str
    hourPosted: str
    usernameTiktokAccount: str
    postURL: str
    views: int
    likes: int
    comments: int
    saves: int
    reposts: int
    totalInteractions: int
    engagement: float
    numberHashtags: int
    hashtags: str
    soundId: str
    soundURL: str
    regionPost: str
    dateTracking: str
    timeTracking: str
    userId: Optional[int] = None
    adminId: Optional[int] = None


class InsertResponse(BaseModel):
    inserted: int = Field(..., description="Número de documentos insertados")
    data: List[MetricOut] = Field(..., description="Lista de métricas de TikTok")


class QueryRequest(BaseModel):
    """Request para consultar métricas almacenadas en la base de datos"""
    
    # Identificadores (usa UNO: userId para /user, adminId para /admin)
    userId: Optional[int] = Field(None, description="Id del usuario (para /dbquery/user)")
    adminId: Optional[int] = Field(None, description="Id del admin (para /dbquery/admin)")

    # Filtros CSV (separados por coma)
    postId: Optional[str] = Field(None, description="IDs de post separados por coma")
    postURL: Optional[str] = Field(None, description="URLs de post separados por coma")
    tiktokUsernames: Optional[str] = Field(None, description="Usernames separados por coma")
    regionPost: Optional[str] = Field(None, description="Regiones separadas por coma")
    soundId: Optional[str] = Field(None, description="IDs de sonido separados por coma")
    soundURL: Optional[str] = Field(None, description="URLs de sonido separadas por coma")
    hashtags: Optional[str] = Field(None, description="Hashtags separados por coma (con o sin #)")

    # Rango de fecha (string YYYY-MM-DD)
    datePostedFrom: Optional[str] = Field(None, description="Fecha desde (YYYY-MM-DD)")
    datePostedTo: Optional[str] = Field(None, description="Fecha hasta (YYYY-MM-DD)")

    # Rangos numéricos
    minViews: Optional[int] = Field(None, description="Mínimo de vistas")
    maxViews: Optional[int] = Field(None, description="Máximo de vistas")
    minLikes: Optional[int] = Field(None, description="Mínimo de likes")
    maxLikes: Optional[int] = Field(None, description="Máximo de likes")
    minTotalInteractions: Optional[int] = Field(None, description="Mínimo de interacciones totales")
    maxTotalInteractions: Optional[int] = Field(None, description="Máximo de interacciones totales")
    minEngagement: Optional[float] = Field(None, description="Mínimo de engagement")
    maxEngagement: Optional[float] = Field(None, description="Máximo de engagement")


class QueryResponse(BaseModel):
    """Response con métricas y dashboard"""
    items: List[MetricOut] = Field(..., description="Lista de métricas encontradas")
    count: int = Field(..., description="Número total de items")
    dashboard: List[Dict[str, Any]] = Field(..., description="Datos del dashboard/estadísticas")