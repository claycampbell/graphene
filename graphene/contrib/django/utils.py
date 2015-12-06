import six
from django.db import models
from django.db.models.manager import Manager
from django.db.models.query import QuerySet

from graphene.utils import LazyList

from graphene import Argument, String

try:
    import django_filters  # noqa
    DJANGO_FILTER_INSTALLED = True
except ImportError:
    DJANGO_FILTER_INSTALLED = False


def get_type_for_model(schema, model):
    schema = schema
    types = schema.types.values()
    for _type in types:
        type_model = hasattr(_type, '_meta') and getattr(
            _type._meta, 'model', None)
        if model == type_model:
            return _type


def get_reverse_fields(model):
    for name, attr in model.__dict__.items():
        # Django =>1.9 uses 'rel', django <1.9 uses 'related'
        related = getattr(attr, 'rel', None) or \
            getattr(attr, 'related', None)
        if isinstance(related, models.ManyToOneRel):
            yield related


class WrappedQueryset(LazyList):

    def __len__(self):
        # Dont calculate the length using len(queryset), as this will
        # evaluate the whole queryset and return it's length.
        # Use .count() instead
        return self._origin.count()


def maybe_queryset(value):
    if isinstance(value, Manager):
        value = value.get_queryset()
    if isinstance(value, QuerySet):
        return WrappedQueryset(value)
    return value


def get_filtering_args_from_filterset(filterset_class, type):
    """ Inspect a FilterSet and produce the arguments to pass to
        a Graphene Field. These arguments will be available to
        filter against in the GraphQL
    """
    from graphene.contrib.django.form_converter import convert_form_field

    args = {}
    for name, filter_field in six.iteritems(filterset_class.base_filters):
        field_type = Argument(convert_form_field(filter_field.field))
        # Is this correct? I don't quite grok the 'parent' system yet
        field_type.mount(type)
        args[name] = field_type

    # Also add the 'order_by' field
    if filterset_class._meta.order_by:
        args[filterset_class.order_by_field] = Argument(String)
    return args


def import_single_dispatch():
    try:
        from functools import singledispatch
    except ImportError:
        singledispatch = None

    if not singledispatch:
        try:
            from singledispatch import singledispatch
        except ImportError:
            pass

    if not singledispatch:
        raise Exception(
            "It seems your python version does not include "
            "functools.singledispatch. Please install the 'singledispatch' "
            "package. More information here: "
            "https://pypi.python.org/pypi/singledispatch"
        )

    return singledispatch
