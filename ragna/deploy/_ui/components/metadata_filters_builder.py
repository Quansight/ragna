import panel as pn
import param

from ragna.core._metadata_filter import MetadataFilter, MetadataOperator

EXCLUDED_OPERATORS = ["RAW", "AND", "OR"]
ALLOWED_OPERATORS = [
    op
    for op in list(MetadataOperator.__members__.keys())
    if op not in EXCLUDED_OPERATORS
]

NO_CORPUS_KEY = "No corpuses available"
NO_FILTER_KEY = ""


class FilterRow(pn.viewable.Viewer):
    key = param.Selector(objects=[NO_FILTER_KEY], default=NO_FILTER_KEY)
    operator = param.Selector(objects=[""], default="")
    value = param.Selector(objects=[""], default="")
    multi_value = param.ListSelector(objects=[""], default=[])

    def __init__(self, on_delete_callback, key_value_pairs=None, **params):
        super().__init__(**params)

        if key_value_pairs:
            self.key_value_pairs = key_value_pairs
            self.param.key.objects.extend(list(key_value_pairs.keys()))
            key_select_disabled = False
        else:
            key_select_disabled = True

        self.key_select = pn.widgets.Select.from_param(
            self.param.key,
            name="",
            css_classes=["metadata-filter-key"],
            disabled=key_select_disabled,
        )

        self.operator_select = pn.widgets.Select.from_param(
            self.param.operator,
            name="",
            css_classes=["metadata-filter-operator"],
            disabled=True,
        )

        self.value_select = pn.widgets.Select.from_param(
            self.param.value,
            name="",
            css_classes=["metadata-filter-value"],
            disabled=True,
        )

        self.multi_value_select = pn.widgets.MultiChoice.from_param(
            self.param.multi_value,
            name="",
            css_classes=["metadata-filter-value"],
            option_limit=3,
            delete_button=False,
        )

        self.delete_button = pn.widgets.ButtonIcon(
            icon="trash",
            width=25,
            height=25,
            css_classes=["metadata-filter-row", "metadata-filter-delete"],
        )
        self.delete_button.on_click(on_delete_callback)

    @param.depends("key", watch=True)
    def key_did_change(self):
        if self.key == NO_FILTER_KEY:
            self.value_select.disabled = True
            self.operator_select.disabled = True
            return

        self.value_select.disabled = False
        self.operator_select.disabled = False

        # the keys are a tuple of (type_str, values)
        type_str, values = self.key_value_pairs[self.key]
        self.param.operator.objects = self.compute_valid_operator_options(type_str)
        self.operator_select.value = "EQ"  # default operator as easy to handle
        self.param.value.objects = values

    def compute_valid_operator_options(self, type_str):
        if type_str == "bool":
            return ["EQ", "NE"]
        elif type_str == "str":
            return ["EQ", "NE", "IN", "NOT_IN"]
        else:
            return ALLOWED_OPERATORS

    def construct_metadata_filter(self):
        if self.key_select.value == NO_FILTER_KEY:
            return None

        if self.operator_select.value in ["IN", "NOT_IN"]:
            return MetadataFilter(
                MetadataOperator[self.operator_select.value],
                self.key_select.value,
                self.multi_value_select.value,
            )
        else:
            return MetadataFilter(
                MetadataOperator[self.operator_select.value],
                self.key_select.value,
                self.value_select.value,
            )

    @param.depends("operator")
    def display(self):
        if self.operator == "IN" or self.operator == "NOT_IN":
            _, self.param.multi_value.objects = self.key_value_pairs[self.key]
            return pn.Row(
                self.key_select,
                self.operator_select,
                self.multi_value_select,
                self.delete_button,
                css_classes=["metadata-filter-row"],
            )
        else:
            return pn.Row(
                self.key_select,
                self.operator_select,
                self.value_select,
                self.delete_button,
                css_classes=["metadata-filter-row"],
            )

    def __panel__(self):
        return self.display


class MetadataFiltersBuilder(pn.viewable.Viewer):
    filter_rows = param.List([])
    corpus_names = param.List([])

    def __init__(self, corpus_metadata, **params):
        super().__init__(**params)

        if self.corpus_names:
            self.corpus_names_select = pn.widgets.Select(
                options=self.corpus_names,
                value=self.corpus_names[0],
                name="",
                css_classes=["metadata-filter-row", "metadata-filter-key"],
            )
        else:
            self.corpus_names_select = pn.widgets.Select(
                options=[NO_CORPUS_KEY],
                name="",
                css_classes=["metadata-filter-row", "metadata-filter-key"],
                disabled=True,
            )

        self.corpus_metadata = corpus_metadata

        self.add_filter_row_button = pn.widgets.ButtonIcon(
            icon="circle-plus", width=25, height=25
        )
        self.add_filter_row_button.on_click(self.add_filter_row)

    def create_filter_row(self):
        return [
            FilterRow(
                key_value_pairs=(
                    self.corpus_metadata[self.corpus_names_select.value]
                    if self.corpus_names_select.value != NO_CORPUS_KEY
                    else {}
                ),
                on_delete_callback=self.delete_filter_row,
            )
        ]

    def add_filter_row(self, event):
        self.filter_rows = self.filter_rows + self.create_filter_row()

    def delete_filter_row(self, event):
        filter_row_to_remove = None
        for filter_row in self.filter_rows:
            if event.obj == filter_row.delete_button:
                filter_row_to_remove = filter_row
                break
        if filter_row_to_remove is None:
            return

        self.filter_rows = [f for f in self.filter_rows if f != filter_row_to_remove]

    @pn.depends("filter_rows")
    def render_filters_rows(self):
        return pn.Column(
            *self.filter_rows,
            css_classes=["metadata-filter-row-collection"],
        )

    def construct_metadata_filters(self):
        metadata_filters = [
            filter_row.construct_metadata_filter()
            for filter_row in self.filter_rows
            if filter_row.key != NO_FILTER_KEY
        ]

        if not metadata_filters:
            return None

        return MetadataFilter.and_(metadata_filters).to_primitive()

    def __panel__(self):
        if len(self.corpus_names) == 0:
            return pn.Column(
                pn.pane.HTML("<b>No corpus available for selected source storage</b>"),
                sizing_mode="stretch_both",
                height_policy="max",
            )

        return pn.Column(
            self.corpus_names_select,
            pn.pane.HTML("<b>Metadata Filters</b>"),
            pn.Column(
                self.render_filters_rows,
                pn.Row(self.add_filter_row_button),
                max_height=125,
            ),
            sizing_mode="stretch_both",
            height_policy="max",
        )
