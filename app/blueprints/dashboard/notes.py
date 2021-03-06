import asyncio
import base64
import binascii
import os
import uuid
from math import ceil

from aiohttp import web
from aiohttp_apispec import match_info_schema, querystring_schema
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from marshmallow import Schema, ValidationError, fields, validate

from app.routing import Blueprint
from app.templating import render_template
from app.utils.auth import requires_auth, verify_user
from app.utils.db import get_db, select_notes, select_notes_count, select_user
from app.utils.forms import parser


class NoteSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=256))
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    password = fields.String()
    share_email = fields.Boolean(load_default=False)
    private = fields.Boolean(load_default=False)


class NotesFilterSchema(Schema):
    page = fields.Integer(validate=validate.Range(min=1, error="Page must be greater than or equal to 1"))
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(
        validate=validate.OneOf({"id", "name", "has_password", "share_email", "private", "clicks", "creation_date"})
    )


class ViewNoteSchema(Schema):
    password = fields.Str()


class IdSchema(Schema):
    note_id = fields.Str(required=True)


class PasswordIncorrectSchema(Schema):
    incorrect_password = fields.Boolean()


def create_fernet(salt: bytes, password: bytes) -> Fernet:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    return Fernet(base64.urlsafe_b64encode(kdf.derive(password)))


def derive_salt_and_content(stored: bytes) -> tuple[bytes, bytes]:
    return stored[:32], stored[32:]


sub_bp = Blueprint("/notes", name="notes")


@sub_bp.get("/{note_id}", name="view")
@match_info_schema(IdSchema())
@querystring_schema(PasswordIncorrectSchema())
async def view_note(request: web.Request) -> web.Response:
    note_id = request["match_info"]["note_id"]
    try:
        as_uuid = uuid.UUID(base64.urlsafe_b64decode(note_id).decode("utf-8"))
    except (ValueError, binascii.Error):
        return web.Response(text="Invalid Note ID", status=400)

    has_pw = await get_db(request).fetchval("SELECT has_password FROM notes WHERE id = $1", as_uuid)

    return await render_template(
        "dashboard/notes/view",
        request,
        {
            "id": note_id,
            "has_pw": has_pw,
            "password_error": ["This password is incorrect"]
            if request["querystring"].get("incorrect_password") is True
            else None,
        },
    )


@sub_bp.post("/{note_id}")
@match_info_schema(IdSchema())
async def view_note_form(request: web.Request) -> web.Response:
    try:
        args = await parser.parse(ViewNoteSchema(), request, locations=["form"])
    except ValidationError as error:
        return web.json_response({"error": error.messages}, status=400)

    note_id = request["match_info"]["note_id"]
    try:
        as_uuid = uuid.UUID(base64.urlsafe_b64decode(note_id).decode("utf-8"))
    except (ValueError, binascii.Error):
        return web.Response(text="Invalid Note ID", status=400)

    note = await get_db(request).fetchrow(
        "SELECT has_password, content, owner, name, share_email, private FROM notes WHERE id = $1", as_uuid
    )
    if note is None:
        return web.Response(text="Note not found", status=404)

    if note["private"] is True:
        try:
            user = await verify_user(
                request,
                redirect=False,
                scopes=["id"],
            )
        except web.HTTPException:
            return web.Response(text="Note is private", status=403)
        if user["id"] != note["owner"]:
            return web.Response(text="Note is private", status=403)

    if note["has_password"] is True:
        password = args.get("password")
        if password is None:
            return web.Response(text="Password required", status=401)
        salt, encrypted_content = derive_salt_and_content(note["content"])
        fernet = create_fernet(salt, password.encode())
        try:
            decoded = fernet.decrypt(encrypted_content).decode("utf-8")
        except InvalidToken:
            return web.HTTPFound(f"/notes/{note_id}?incorrect_password=True")
    else:
        decoded = note["content"].decode("utf-8")

    email = None
    if note["share_email"] is True:
        email = (await select_user(get_db(request), user_id=note["owner"])).get("email")

    asyncio.get_event_loop().create_task(
        get_db(request).execute("UPDATE notes SET clicks = clicks + 1 WHERE id = $1", as_uuid)
    )

    return await render_template(
        "dashboard/notes/view_stylized", request, {"name": note["name"], "email": email, "content": decoded}
    )


bp = Blueprint("/dashboard/notes", name="notes", subblueprints=[sub_bp])


@bp.get("", name="index")
@querystring_schema(NotesFilterSchema())
@requires_auth(scopes=["id", "admin"])
async def index(request: web.Request) -> web.Response:
    current_page = request["querystring"].get("page", 1) - 1
    direction = request["querystring"].get("direction", "desc")
    sortby = request["querystring"].get("sortby", "creation_date")

    async with get_db(request).acquire() as conn:
        notes = await select_notes(
            conn,
            sortby=sortby,
            direction=direction.upper(),
            owner=request["user"]["id"],
            offset=current_page * 50,
        )
        notes_count = await select_notes_count(conn, owner=request["user"]["id"])

    max_pages = ceil(notes_count / 50)

    if max_pages == 0:
        max_pages = 1
    return await render_template(
        "dashboard/notes/index",
        request,
        {
            "current_page": current_page + 1,
            "max_pages": max_pages,
            "values": notes,
            "sortby": sortby,
            "direction": direction,
        },
    )


@bp.get("/create", name="create")
@requires_auth(scopes=["id", "admin"])
async def create_note(_: web.Request) -> web.Response:
    return await render_template("dashboard/notes/create", _)


@bp.post("/create")
@requires_auth(scopes=["id", "admin"])
async def create_note_form(request: web.Request) -> web.Response:
    try:
        args = await parser.parse(NoteSchema(), request, locations=["form"])
    except ValidationError as error:
        return await render_template(
            "/dashboard/notes/create", request, {"errors": error.normalized_messages()}, status=400
        )

    name = args["name"]
    content = args["content"]
    password = args["password"]

    has_pw = False
    if password != "":
        salt = os.urandom(32)
        fernet = create_fernet(salt, password.encode())
        stored = salt + fernet.encrypt(content.encode())
        has_pw = True
    else:
        stored = content.encode()

    query = """
INSERT INTO notes (owner, name, content, has_password, share_email, private)
VALUES ($1, $2, $3, $4, $5, $6) returning id
    """
    args = (
        request["user"]["id"],
        name,
        stored,
        has_pw,
        args["share_email"],
        args["private"],
    )
    id_ = await get_db(request).fetchval(query, *args)

    id_ = base64.urlsafe_b64encode(str(id_).encode())

    return web.HTTPFound("/dashboard/notes")
