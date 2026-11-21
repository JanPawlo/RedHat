from typing import Any, Callable, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.const.docs import OPENAPI_TAG_GROUPS, OPENAPI_TAG_GROUPS_KEY


def grouped_openapi(app: FastAPI) -> Callable[[], Dict[str, Any]]:
    """OpenAPI schema with tag groups, shown as sections in ReDoc (Swagger UI ignores them)."""

    def build() -> Dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema[OPENAPI_TAG_GROUPS_KEY] = OPENAPI_TAG_GROUPS
        app.openapi_schema = schema
        return schema

    return build
