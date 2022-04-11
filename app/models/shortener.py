from marshmallow import Schema, ValidationError, fields, validate


def none_or_len(name: str, min: int, max: int):
    def validator(string: str):
        if string != "":  # it won't be None, it will be ""
            if len(string) < min:
                raise ValidationError(f"Length must be between {min} and {max} or empty")
            if len(string) > max:
                raise ValidationError(f"Length must be between {min} and {max} or empty")

    return validator


class ShortenerAliasSchema(Schema):
    alias = fields.Str(required=True)


class ShortenerFilterSchema(Schema):
    page = fields.Integer(validate=validate.Range(min=1, error="Page must be greater than or equal to 1"))
    direction = fields.String(validate=validate.OneOf({"desc", "asc"}))
    sortby = fields.String(validate=validate.OneOf({"alias", "destination", "clicks", "creation_date"}))


class ShortenerEditSchema(Schema):
    alias = fields.String(validate=none_or_len("alias", 3, 64))
    destination = fields.URL(required=True, schemes={"http", "https"})
    reset_clicks = fields.Boolean()


class ShortenerCreateSchema(Schema):
    alias = fields.String(validate=none_or_len("alias", 3, 64))
    destination = fields.URL(required=True, schemes={"http", "https"})
