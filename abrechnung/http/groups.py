from datetime import datetime, timezone

import schema
from aiohttp import web
from aiohttp.abc import Request
from schema import Schema

from abrechnung.application import NotFoundError
from abrechnung.http.serializers import (
    GroupSerializer,
    GroupMemberSerializer,
    GroupInviteSerializer,
    GroupPreviewSerializer,
)
from abrechnung.http.utils import validate, json_response

routes = web.RouteTableDef()


@routes.get("/groups")
async def list_groups(request):
    try:
        groups = await request.app["group_service"].list_groups(
            user_id=request["user"]["user_id"]
        )
    except NotFoundError:
        raise web.HTTPForbidden(reason="permission denied")

    serializer = GroupSerializer(groups)

    return json_response(data=serializer.to_repr())


@routes.post("/groups")
@validate(
    Schema({"name": str, "description": str, "currency_symbol": str, "terms": str})
)
async def create_group(request: Request, data):
    group_id = await request.app["group_service"].create_group(
        user_id=request["user"]["user_id"],
        name=data["name"],
        description=data["description"],
        currency_symbol=data["currency_symbol"],
        terms=data["terms"],
    )

    return json_response(data={"group_id": group_id})


@routes.get(r"/groups/{group_id:\d+}")
async def get_group(request: Request):
    try:
        group = await request.app["group_service"].get_group(
            user_id=request["user"]["user_id"],
            group_id=int(request.match_info["group_id"]),
        )
    except PermissionError:
        raise web.HTTPForbidden(reason="permission denied")

    serializer = GroupSerializer(group)

    return json_response(data=serializer.to_repr())


@routes.post(r"/groups/{group_id:\d+}")
@validate(
    Schema({"name": str, "description": str, "currency_symbol": str, "terms": str})
)
async def update_group(request: Request, data: dict):
    await request.app["group_service"].update_group(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
        name=data["name"],
        description=data["description"],
        currency_symbol=data["currency_symbol"],
        terms=data["terms"],
    )

    return web.Response(status=web.HTTPNoContent.status_code)


@routes.get(r"/groups/{group_id:\d+}/members")
async def list_members(request: web.Request):
    members = await request.app["group_service"].list_members(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
    )

    serializer = GroupMemberSerializer(members)

    return json_response(data=serializer.to_repr())


@routes.post(r"/groups/{group_id:\d+}/members")
@validate(Schema({"user_id": int, "can_write": bool, "is_owner": bool}))
async def update_member_permissions(request: web.Request, data: dict):
    await request.app["group_service"].update_member_permissions(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
        member_id=data["user_id"],
        can_write=data["can_write"],
        is_owner=data["is_owner"],
    )

    return web.Response(status=web.HTTPNoContent.status_code)


@routes.get(r"/groups/{group_id:\d+}/invites")
async def list_invites(request):
    invites = await request.app["group_service"].list_invites(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
    )

    serializer = GroupInviteSerializer(invites)

    return json_response(data=serializer.to_repr())


@routes.post(r"/groups/{group_id:\d+}/invites")
@validate(
    schema.Schema(
        {
            "description": str,
            "single_use": bool,
            "valid_until": schema.Use(datetime.fromisoformat),
        }
    )
)
async def create_invite(request: Request, data: dict):
    valid_until = datetime.fromisoformat(data["valid_until"])
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)

    await request.app["group_service"].create_invite(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
        description=data["description"],
        single_use=data["single_use"],
        valid_until=valid_until,
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/groups/{group_id:\d+}/invites/{invite_id:\d+}")
async def delete_invite(request: Request):
    await request.app["group_service"].delete_invite(
        user_id=request["user"]["user_id"],
        group_id=int(request.match_info["group_id"]),
        invite_id=int(request.match_info["invite_id"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/groups/preview")
@validate(schema.Schema({"invite_token": str}))
async def preview_group(request: Request, data: dict):
    group_preview = await request.app["group_service"].preview_group(
        invite_token=data["invite_token"],
    )

    serializer = GroupPreviewSerializer(group_preview)

    return json_response(data=serializer.to_repr())


@routes.post(r"/groups/join")
@validate(schema.Schema({"invite_token": str}))
async def join_group(request: Request, data: dict):
    await request.app["group_service"].join_group(
        user_id=request["user"]["user_id"],
        invite_token=data["invite_token"],
    )

    return json_response(status=web.HTTPNoContent.status_code)