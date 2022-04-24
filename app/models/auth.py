from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Field(required=True, validate=validate.Length(min=5, max=1024))


class SignUpSchema(LoginSchema):
    invite_code = fields.UUID(required=True)


class UsersEditSchema(Schema):
    email = fields.Email(required=True)


class SessionSchema(Schema):
    token = fields.UUID(required=True)


class UserIDSchema(Schema):
    user_id = fields.Integer(require=True)


class UsersFilterSchema(Schema):
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"id", "email", "joined"}))
