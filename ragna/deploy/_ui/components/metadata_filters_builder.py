import panel as pn
import param

from ragna.core._metadata_filter import MetadataFilter


class FilterRow(pn.viewable.Viewer):
    key = param.Selector(
        objects=[
            "",  # empty one for the first row
            # hardcoded list for now
            "document_name",
            "document_size",
            "document_last_modified",
            "document_extension",
            "document_created",
            "ingestion_date",
            # "path"
        ],
        default="",
    )
    operator = param.Selector(
        objects=[
            "",  # empty one for the first row
            "==",
            "!=",
            ">",
            "<",
            ">=",
            "<=",
            "in",
            "not in",
            # "raw"
        ]
    )
    value = param.String()

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        return pn.Row(
            pn.widgets.Select.from_param(self.param.key, name=""),
            pn.widgets.Select.from_param(self.param.operator, name=""),
            pn.widgets.TextInput.from_param(self.param.value, name=""),
            # sizing_mode="stretch_width",
        )

    def is_empty(self):
        return self.key == "" and self.operator == "" and self.value == ""

    def __str__(self):
        return f"{self.key} {self.operator} {self.value}"

    def __repr__(self):
        return f"[key:{self.key} \t op:{self.operator} \t val:{self.value}]"

    def convert_operator(self, operator):
        if operator == "==":
            return MetadataFilter.eq
        if operator == "!=":
            return MetadataFilter.ne
        if operator == ">":
            return MetadataFilter.gt
        if operator == "<":
            return MetadataFilter.lt
        if operator == ">=":
            return MetadataFilter.ge
        if operator == "<=":
            return MetadataFilter.le
        if operator == "in":
            return MetadataFilter.in_
        if operator == "not in":
            return MetadataFilter.not_in

        # if operator == "raw":
        #    return MetadataFilter.RAW

    def get_metadata_filter(self):
        if self.key == "" or self.operator == "" or self.value == "":
            return None
        return self.convert_operator(self.operator)(key=self.key, value=self.value)


class MetadataFiltersBuilder(pn.viewable.Viewer):
    metadata_filters = param.List(
        [
            # FilterRow(key="", operator="", value="")
            FilterRow(key="document_name", operator="==", value="applications.md")
        ]
    )

    def __init__(self, **params):
        super().__init__(**params)

        self.add_filter_button = pn.widgets.ButtonIcon(
            icon="circle-plus", width=25, height=25, description="New metadata filter"
        )
        self.add_filter_button.on_click(self.did_click_add_filter_button)

        self.delete_buttons = []

        # dummy_row = FilterRow(key="document_name", operator="==", value="applications.md")
        # self.metadata_filters.append(dummy_row)

    def did_click_add_filter_button(self, event):
        if len(self.metadata_filters) > 0 and not self.metadata_filters[-1].is_empty():
            new_metadata_filter_row = FilterRow(key="", operator="", value="")
            self.metadata_filters = self.metadata_filters + [new_metadata_filter_row]

    def delete_metadata_filter(self, event):
        print("should delete filter : ", event)

        idx = self.delete_buttons.index(event.obj)
        filter = self.metadata_filters[idx]

        new_metadata_filters = [f for f in self.metadata_filters if f != filter]
        if len(new_metadata_filters) == 0:
            new_metadata_filters.append(FilterRow(key="", operator="", value=""))

        self.metadata_filters = new_metadata_filters

    @pn.depends("metadata_filters")
    def render_metadata_filters_row(self):
        self.delete_buttons = []
        for _ in self.metadata_filters:
            delete_button = pn.widgets.ButtonIcon(
                icon="trash", width=25, height=25, description="Delete metadata filter"
            )
            delete_button.on_click(self.delete_metadata_filter)

            self.delete_buttons.append(delete_button)

        rows_with_delete_buttons = [
            pn.Row(f, delete_button)
            for f, delete_button in zip(self.metadata_filters, self.delete_buttons)
        ]
        return pn.Column(*rows_with_delete_buttons)

    def get_metadata_filters(self):
        if len(self.metadata_filters) == 0:
            return None
        elif len(self.metadata_filters) == 1:
            return self.metadata_filters[0].get_metadata_filter().to_primitive()
        else:
            return MetadataFilter.and_(
                *[
                    f.get_metadata_filter()
                    for f in self.metadata_filters
                    if f.get_metadata_filter() is not None
                ]
            ).to_primitive()

    def __panel__(self):
        return pn.Column(
            pn.pane.Markdown("### Metadata Filters"),
            self.render_metadata_filters_row,
            pn.Row(self.add_filter_button),
            sizing_mode="stretch_both",
            height_policy="max",
        )
