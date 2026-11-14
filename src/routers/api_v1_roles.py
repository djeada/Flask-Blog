from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from blog_engine import policy, repository
from blog_engine.auth import get_current_principal
from blog_engine.database import get_blog_db
from blog_engine.models import Role
from blog_engine.schemas import (
    CapabilityInfo,
    ErrorResponse,
    Principal,
    RoleInfo,
    RolePermissionsUpdate,
)

router = APIRouter(prefix="/api/v1")


def _role_info(
    role: Role, description: str, capabilities: frozenset[str]
) -> RoleInfo:
    return RoleInfo(
        role=role,
        description=description,
        capabilities=[
            key for key in policy.CAPABILITY_ORDER if key in capabilities
        ],
    )


def _load_role_info(db: Session, role: Role) -> RoleInfo:
    descriptions = repository.list_role_descriptions(db)
    capabilities = repository.list_role_capabilities(db)
    return _role_info(
        role,
        descriptions.get(role, policy.DEFAULT_ROLE_DESCRIPTIONS[role]),
        capabilities[role],
    )


@router.get(
    "/roles",
    response_model=list[RoleInfo],
    tags=["roles"],
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
    summary="List roles",
    description=(
        "Public. Returns each role with its description and currently assigned "
        "capabilities."
    ),
)
def list_roles(
    response: Response, db: Session = Depends(get_blog_db)
) -> list[RoleInfo]:
    response.headers["Cache-Control"] = "public, max-age=300"
    descriptions = repository.list_role_descriptions(db)
    capabilities = repository.list_role_capabilities(db)
    return [
        _role_info(
            role,
            descriptions.get(role, policy.DEFAULT_ROLE_DESCRIPTIONS[role]),
            capabilities[role],
        )
        for role in Role
    ]


@router.get(
    "/roles/{role}",
    response_model=RoleInfo,
    tags=["roles"],
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
    summary="Retrieve a role",
)
def get_role(
    role: Role, response: Response, db: Session = Depends(get_blog_db)
) -> RoleInfo:
    response.headers["Cache-Control"] = "public, max-age=300"
    return _load_role_info(db, role)


@router.put(
    "/roles/{role}",
    response_model=RoleInfo,
    tags=["roles"],
    responses={
        400: {"model": ErrorResponse, "description": "Unknown capability key"},
        401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
        403: {"model": ErrorResponse, "description": "users.manage capability required"},
        409: {"model": ErrorResponse, "description": "Admin role is immutable"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Update a role's description and capabilities (Admin)",
    description=(
        "Requires the users.manage capability. The Admin role is immutable. "
        "Capability changes take effect immediately for subsequent requests."
    ),
)
def update_role(
    role: Role,
    payload: RolePermissionsUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_blog_db),
) -> RoleInfo:
    if not policy.can_manage_users(principal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="users.manage capability required",
        )
    if role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin role is immutable",
        )

    capabilities = None
    if payload.capabilities is not None:
        requested = set(payload.capabilities)
        unknown = sorted(requested - set(policy.CAPABILITY_ORDER))
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown capabilities: {', '.join(unknown)}",
            )
        capabilities = [
            key for key in policy.CAPABILITY_ORDER if key in requested
        ]

    repository.update_role_settings(db, role, payload.description, capabilities)
    return _load_role_info(db, role)


@router.get(
    "/capabilities",
    response_model=list[CapabilityInfo],
    tags=["capabilities"],
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
    summary="List capabilities",
    description=(
        "Public. Returns the capability vocabulary used by role assignments. "
        "Capability keys are wired to enforcement code and are read-only."
    ),
)
def list_capabilities(response: Response) -> list[CapabilityInfo]:
    response.headers["Cache-Control"] = "public, max-age=300"
    return [
        CapabilityInfo(
            key=key,
            label=policy.CAPABILITY_DEFINITIONS[key][0],
            description=policy.CAPABILITY_DEFINITIONS[key][1],
        )
        for key in policy.CAPABILITY_ORDER
    ]
