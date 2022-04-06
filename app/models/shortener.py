from marshmallow import Schema, fields, validate


class ShortenerAliasSchema(Schema):
    alias = fields.Str(required=True)


class ShortenerFilterSchema(Schema):
    page = fields.Integer(validate=validate.Range(min=1, error="Page must be greater than or equal to 1"))
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"alias", "destination", "clicks", "creation_date"}))


class ShortenerEditSchema(Schema):
    alias = fields.String()
    destination = fields.URL(required=True)
    reset_clicks = fields.Boolean()


class ShortenerCreateSchema(Schema):
    alias = fields.String()
    destination = fields.URL(required=True, schemes={"http", "https"})
