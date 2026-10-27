from fastapi import APIRouter


api_router = APIRouter()

# Import each domain's resource routers here and register them with
# api_router.include_router(resource_router). Mount api_router at /api.
