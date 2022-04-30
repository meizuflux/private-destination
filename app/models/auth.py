# pylint: disable=missing-class-docstring
from marshmallow import Schema, fields, validate

from app.utils.time import TIME_UNITS


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Field(required=True, validate=validate.Length(min=5, max=1024))


class SignUpSchema(LoginSchema):
    invite_code = fields.UUID(required=True)


class UsersEditSchema(Schema):
    email = fields.Email(required=True)
    session_duration_amount = fields.Integer(required=True, validate=validate.Range(min=1, max=64))
    session_duration_unit = fields.String(
        required=True, validate=validate.OneOf(set(TIME_UNITS.keys()), error="Unit must be one of: {choices}")
    )


class SessionSchema(Schema):
    token = fields.UUID(required=True)


class UserIDSchema(Schema):
    user_id = fields.Integer(require=True)


class UsersFilterSchema(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"id", "email", "joined"}))
