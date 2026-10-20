from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.response import ApiResponse
from app.auth.jwt.context import TokenContext
from app.dependencies.auth import require_permission
from app.dependencies.rls import get_rls_db
from app.dependencies.service import get_service
from app.public.services.child_documents_create import CreateChildDocumentService
from app.public.services.child_documents_read import ReadChildDocumentService
from app.public.services.child_documents_update import UpdateChildDocumentService
from app.public.schemas.child_documents import (
    ChildDocumentDownloadResponse,
    ChildDocumentResponse,
    ChildDocumentUploadResponse,
    CreateChildDocumentRequest,
    ListChildDocumentsFilterRequest,
)


# Families add and remove their children's documents (child_documents
# c / d, customers only); families and staff read them (r).
router = APIRouter(
    prefix="/child-documents/v1",
    tags=["child-documents"],
)


@router.get("/")
def list_child_documents(
    filters: Annotated[ListChildDocumentsFilterRequest, Query()],
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_documents",
            action="r",
        )
    ),
    service: ReadChildDocumentService = Depends(
        get_service(
            ReadChildDocumentService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[list[ChildDocumentResponse]]:
    result = service.list_for_child(
        child_id=filters.child_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Documents",
        data=result,
    )


@router.post("/", status_code=201)
def start_child_document_upload(
    body: CreateChildDocumentRequest,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_documents",
            action="c",
        )
    ),
    service: CreateChildDocumentService = Depends(
        get_service(
            CreateChildDocumentService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildDocumentUploadResponse]:
    result = service.start(
        body=body,
        user_id=ctx.user_id,
    )

    return ApiResponse(
        ok=True,
        msg="Upload started",
        data=result,
    )


# Part of adding a document, so the same permission as starting it.
@router.post("/{document_id}/complete")
def complete_child_document_upload(
    document_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_documents",
            action="c",
        )
    ),
    service: CreateChildDocumentService = Depends(
        get_service(
            CreateChildDocumentService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildDocumentResponse]:
    result = service.complete(
        id=document_id,
        user_id=ctx.user_id,
        location_id=ctx.location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Document uploaded",
        data=result,
    )


@router.get("/{document_id}/download")
def get_child_document_download(
    document_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_documents",
            action="r",
        )
    ),
    service: ReadChildDocumentService = Depends(
        get_service(
            ReadChildDocumentService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildDocumentDownloadResponse]:
    result = service.create_download(
        id=document_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched Document Link",
        data=result,
    )


@router.post("/{document_id}/remove")
def remove_child_document(
    document_id: UUID,
    ctx: TokenContext = Depends(
        require_permission(
            resource="child_documents",
            action="d",
        )
    ),
    service: UpdateChildDocumentService = Depends(
        get_service(
            UpdateChildDocumentService,
            db_dependency=get_rls_db,
        )
    ),
) -> ApiResponse[ChildDocumentResponse]:
    result = service.remove(
        id=document_id,
    )

    return ApiResponse(
        ok=True,
        msg="Document removed",
        data=result,
    )
