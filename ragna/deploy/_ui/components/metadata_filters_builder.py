from datetime import datetime

import panel as pn
import param

from ragna.core._metadata_filter import MetadataFilter, MetadataOperator

METADATA_FILTERS = {
    "document_name": {"type": str},
    "size": {"type": int},
    "extension": {"type": str},
    "section": {"type": str},
    # "creation_date": {"type": datetime},
}


FILTERS_PER_TYPE = {
    str: ["==", "!=", "in", "not in"],
    int: ["==", "!=", ">", "<", ">=", "<=", "in", "not in"],
    # datetime: ["==", "!=", ">", "<", ">=", "<="],
}

PLACEHOLDERS_PER_METADATA_KEY = {
    "document_name": "",
    "size": "",
    "extension": "",
    "section": "",
    # "creation_date": "YYYY-mm-dd HH:MM:SS",
}


class FilterRow(pn.viewable.Viewer):
    key = param.Selector(
        objects=[
            "",  # empty one for the first row
            *METADATA_FILTERS.keys(),
        ],
        default="",
    )
    operator = param.Selector(
        objects=[
            "",  # empty one for the first row
            # Filled later based on the key
            # "raw"
        ]
    )
    value = param.String()

    def __init__(self, on_delete_callback, **params):
        super().__init__(**params)

        self.key_select = pn.widgets.Select.from_param(
            self.param.key,
            name="",
            css_classes=["metadata-filter", "metadata-filter-key"],
        )

        self.operator_select = pn.widgets.Select.from_param(
            self.param.operator,
            name="",
            css_classes=["metadata-filter", "metadata-filter-operator"],
            disabled=True,
        )

        self.value_text_input = pn.widgets.TextInput.from_param(
            self.param.value,
            name="",
            placeholder="",
            css_classes=["metadata-filter", "metadata-filter-value"],
            disabled=True,
        )

        self.delete_button = pn.widgets.ButtonIcon(
            icon="trash",
            width=25,
            height=25,
            css_classes=["metadata-filter", "metadata-filter-delete"],
        )
        self.delete_button.on_click(on_delete_callback)

    @param.depends("key", watch=True)
    def key_did_change(self):
        if self.key == "":
            self.operator = ""
            self.value_text_input.disabled = True
            self.operator_select.disabled = True
            return

        self.value_text_input.disabled = False
        self.operator_select.disabled = False
        self.param.operator.objects = [""] + FILTERS_PER_TYPE[
            METADATA_FILTERS[self.key]["type"]
        ]

    @param.depends("key", watch=True)
    def value_text_input(self):
        placeholder = ""
        if self.key != "":
            placeholder = PLACEHOLDERS_PER_METADATA_KEY[self.key]

        self.value_text_input.placeholder = placeholder

    def __panel__(self):
        return pn.Row(
            self.key_select,
            self.operator_select,
            self.value_text_input,
            self.delete_button,
        )

    def is_empty(self):
        return self.key == "" and self.operator == "" and self.value == ""

    def validate_value(self, value):
        if value == "":
            return False

        if self.operator == "in" or self.operator == "not in":
            values = value.split(",")
            if len(values) > 1:
                for val in values:
                    if not self.validate_value(val.strip()):
                        return False
                return True
            else:
                value = values[0]

        if METADATA_FILTERS[self.key]["type"] == int:
            try:
                int(value)
            except ValueError:
                return False
        elif METADATA_FILTERS[self.key]["type"] == datetime:
            try:
                datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return False

        return True

    def validate(self):
        def change_valid_status(valid, widget):
            if valid:
                widget.css_classes = [
                    c for c in widget.css_classes if c != "metadata-filter-error"
                ]
            else:
                widget.css_classes = widget.css_classes + ["metadata-filter-error"]

        if self.key == "":
            change_valid_status(False, self.key_select)
            return False

        change_valid_status(True, self.key_select)

        result = True
        if self.operator == "":
            change_valid_status(False, self.operator_select)
            result = False
        else:
            change_valid_status(True, self.operator_select)

        if not self.validate_value(self.value):
            change_valid_status(False, self.value_text_input)
            result = False
        else:
            change_valid_status(True, self.value_text_input)

        return result

    def __str__(self):
        return f"{self.key} {self.operator} {self.value}"

    def __repr__(self):
        return f"[key:{self.key} \t op:{self.operator} \t val:{self.value}]"

    def convert_operator(self, operator):
        return {
            "==": MetadataOperator.EQ,
            "!=": MetadataOperator.NE,
            ">": MetadataOperator.GT,
            "<": MetadataOperator.LT,
            ">=": MetadataOperator.GE,
            "<=": MetadataOperator.LE,
            "in": MetadataOperator.IN,
            "not in": MetadataOperator.NOT_IN,
        }[operator]

    def convert_value(self, value):
        try:
            if METADATA_FILTERS[self.key]["type"] == int:
                return int(value)
            elif METADATA_FILTERS[self.key]["type"] == datetime:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value
        except ValueError:
            return value

    def get_metadata_filter(self):
        if self.key == "" or self.operator == "" or self.value == "":
            return None
        return MetadataFilter(
            operator=self.convert_operator(self.operator),
            key=self.key,
            value=self.convert_value(self.value),
        )


class MetadataFiltersBuilder(pn.viewable.Viewer):
    metadata_filters = param.List([])

    def __init__(self, **params):
        super().__init__(**params)

        self.add_filter_button = pn.widgets.ButtonIcon(
            icon="circle-plus", width=25, height=25
        )
        self.add_filter_button.on_click(self.did_click_add_filter_button)

        self.delete_buttons = []

        # dummy_row = FilterRow(key="document_name", operator="==", value="applications.md")
        self.metadata_filters.append(self.empty_filter())

    def empty_filter(self):
        return FilterRow(
            key="",
            operator="",
            value="",
            on_delete_callback=self.delete_metadata_filter,
        )

    def did_click_add_filter_button(self, event):
        if len(self.metadata_filters) > 0 and not self.metadata_filters[-1].is_empty():
            new_metadata_filter_row = self.empty_filter()
            self.metadata_filters = self.metadata_filters + [new_metadata_filter_row]

    def delete_metadata_filter(self, event):
        print("should delete filter : ", event)

        filter_to_remove = None
        for filter in self.metadata_filters:
            if event.obj == filter.delete_button:
                filter_to_remove = filter
                break

        if filter_to_remove is None:
            return

        new_metadata_filters = [f for f in self.metadata_filters if f != filter]
        if len(new_metadata_filters) == 0:
            new_metadata_filters.append(self.empty_filter())

        self.metadata_filters = new_metadata_filters

    @pn.depends("metadata_filters")
    def render_metadata_filters_rows(self):
        return pn.Column(*self.metadata_filters)

    def get_metadata_filters(self):
        if len(self.metadata_filters) == 0:
            return None
        elif len(self.metadata_filters) == 1:
            if self.metadata_filters[0].is_empty():
                return None
            return self.metadata_filters[0].get_metadata_filter().to_primitive()
        else:
            return MetadataFilter.and_(
                [
                    f.get_metadata_filter()
                    for f in self.metadata_filters
                    if f.get_metadata_filter() is not None
                ]
            ).to_primitive()

    def validate(self):
        result = True
        for filter in self.metadata_filters:
            # If the last filter is empty, we do not want to validate it.
            # This allows to have only one empty filter, to question on the whole corpus.
            if filter == self.metadata_filters[-1] and filter.is_empty():
                continue

            if not filter.validate():
                result = False
                # Do not break, we want to call validate() on every filters

        return result

    def __panel__(self):
        return pn.Column(
            pn.pane.Markdown("### Metadata Filters"),
            pn.Column(
                self.render_metadata_filters_rows,
                pn.Row(self.add_filter_button),
                css_classes=["metadata-filters"],
            ),
            sizing_mode="stretch_both",
            height_policy="max",
        )
