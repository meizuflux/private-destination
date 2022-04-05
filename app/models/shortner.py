from marshmallow import Schema, fields, validate


class ShortnerKeySchema(Schema):
    key = fields.Str(required=True)


class ShortnerFilterSchema(Schema):
    page = fields.Integer(validate=validate.Range(min=1, error="Page must be greater than or equal to 1"))
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"key", "destination", "clicks", "creation_date"}))


class ShortnerEditSchema(Schema):
    key = fields.String()
    destination = fields.URL(required=True)
    reset_clicks = fields.Boolean()


class ShortnerCreateSchema(Schema):
    key = fields.String()
    destination = fields.URL(required=True, schemes={"http", "https"})
