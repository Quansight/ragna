import pydantic
import pytest

from ragna.core import MetadataFilter, MetadataOperator

metadata_filters = pytest.mark.parametrize(
    "metadata_filter",
    [
        pytest.param(MetadataFilter.raw("raw"), id="raw"),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.eq("key", "value"),
                ]
            ),
            id="and",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.eq("key", "value"),
                ]
            ),
            id="or",
        ),
        pytest.param(
            MetadataFilter.and_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.or_(
                        [
                            MetadataFilter.eq("key", "value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            id="and-nested",
        ),
        pytest.param(
            MetadataFilter.or_(
                [
                    MetadataFilter.raw("raw"),
                    MetadataFilter.and_(
                        [
                            MetadataFilter.eq("key", "value"),
                            MetadataFilter.ne("other_key", "other_value"),
                        ]
                    ),
                ]
            ),
            id="or-nested",
        ),
        pytest.param(MetadataFilter.eq("key", "value"), id="eq"),
        pytest.param(MetadataFilter.ne("key", "value"), id="ne"),
        pytest.param(MetadataFilter.lt("key", 1), id="lt"),
        pytest.param(MetadataFilter.le("key", 0), id="le"),
        pytest.param(MetadataFilter.gt("key", 1), id="gt"),
        pytest.param(MetadataFilter.ge("key", 0), id="ge"),
        pytest.param(MetadataFilter.in_("key", ["foo", "bar"]), id="in"),
        pytest.param(MetadataFilter.not_in("key", ["foo", "bar"]), id="not_in"),
    ],
)


@metadata_filters
def test_self_similarity(metadata_filter):
    assert metadata_filter == metadata_filter


@metadata_filters
def test_to_from_primitive_roundtrip(metadata_filter):
    assert (
        MetadataFilter.from_primitive(metadata_filter.to_primitive()) == metadata_filter
    )


@metadata_filters
def test_pydantic(metadata_filter):
    class Model(pydantic.BaseModel):
        mf: MetadataFilter

    assert Model(mf=metadata_filter).mf == metadata_filter
    assert Model(mf=metadata_filter.to_primitive()).mf == metadata_filter
    assert Model(mf=metadata_filter).model_dump(mode="json") == {
        "mf": metadata_filter.to_primitive()
    }


@metadata_filters
def test_repr_smoke(metadata_filter):
    repr(metadata_filter)


def test_raw():
    value = "SENTINEL"
    metadata_filter = MetadataFilter.raw(value)
    assert metadata_filter.operator is MetadataOperator.RAW
    assert metadata_filter.value == value


def test_and():
    children = [MetadataFilter.raw("SENTINEL1"), MetadataFilter.raw("SENTINEL2")]
    metadata_filter = MetadataFilter.and_(children)
    assert metadata_filter.operator is MetadataOperator.AND
    assert metadata_filter.value == children


def test_or():
    children = [MetadataFilter.raw("SENTINEL1"), MetadataFilter.raw("SENTINEL2")]
    metadata_filter = MetadataFilter.or_(children)
    assert metadata_filter.operator is MetadataOperator.OR
    assert metadata_filter.value == children


@pytest.mark.parametrize(
    "fn",
    [
        pytest.param(MetadataFilter.and_, id="and"),
        pytest.param(MetadataFilter.or_, id="or"),
    ],
)
def test_flatten(fn):
    children = [MetadataFilter.raw(f"SENTINEL{idx}") for idx in range(3)]
    assert fn([children[0], fn(children[1:])]) == fn(children)


def test_eq():
    key = "KEY_SENTINEL"
    value = "VALUE_SENTINEL"
    metadata_filter = MetadataFilter.eq(key, value)
    assert metadata_filter.operator is MetadataOperator.EQ
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_ne():
    key = "KEY_SENTINEL"
    value = "VALUE_SENTINEL"
    metadata_filter = MetadataFilter.ne(key, value)
    assert metadata_filter.operator is MetadataOperator.NE
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_lt():
    key = "KEY_SENTINEL"
    value = 31476
    metadata_filter = MetadataFilter.lt(key, value)
    assert metadata_filter.operator is MetadataOperator.LT
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_le():
    key = "KEY_SENTINEL"
    value = 31476
    metadata_filter = MetadataFilter.le(key, value)
    assert metadata_filter.operator is MetadataOperator.LE
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_gt():
    key = "KEY_SENTINEL"
    value = 31476
    metadata_filter = MetadataFilter.gt(key, value)
    assert metadata_filter.operator is MetadataOperator.GT
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_ge():
    key = "KEY_SENTINEL"
    value = 31476
    metadata_filter = MetadataFilter.ge(key, value)
    assert metadata_filter.operator is MetadataOperator.GE
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_in():
    key = "KEY_SENTINEL"
    value = ["foo", "bar"]
    metadata_filter = MetadataFilter.in_(key, value)
    assert metadata_filter.operator is MetadataOperator.IN
    assert metadata_filter.key == key
    assert metadata_filter.value == value


def test_not_in():
    key = "KEY_SENTINEL"
    value = ["foo", "bar"]
    metadata_filter = MetadataFilter.not_in(key, value)
    assert metadata_filter.operator is MetadataOperator.NOT_IN
    assert metadata_filter.key == key
    assert metadata_filter.value == value
