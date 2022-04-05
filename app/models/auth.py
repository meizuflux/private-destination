from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Field(require=True)


class SignUpSchema(LoginSchema):
    username = fields.String(validate=validate.Length(3, 32), required=True)


class UsersEditSchema(Schema):
    username = fields.String(required=True)
    email = fields.Email(required=True)
    authorized = fields.Boolean(required=True)


class SessionSchema(Schema):
    token = fields.UUID(required=True)


class UserIDSchema(Schema):
    user_id = fields.Integer(require=True)


class UsersFilterSchema(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"username", "id", "authorized", "email", "joined"}))
