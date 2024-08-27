import panel as pn
import param

from ragna.core._metadata_filter import MetadataFilter, MetadataOperator

EXCLUDED_OPERATORS = ["RAW", "AND", "OR"]
ALLOWED_OPERATORS = [
    op
    for op in list(MetadataOperator.__members__.keys())
    if op not in EXCLUDED_OPERATORS
]


class FilterRow(pn.viewable.Viewer):
    key = param.Selector(objects=[""], default="")
    operator = param.Selector(objects=[""] + ALLOWED_OPERATORS, default="")
    value = param.Selector(objects=[""], default="")

    def __init__(self, on_delete_callback, valid_key_value_pairs=None, **params):
        super().__init__(**params)

        key_select_disabled = True
        if valid_key_value_pairs:
            key_select_disabled = False
            self.param.key.objects = [""] + list(valid_key_value_pairs.keys())
            self.valid_key_value_pairs = valid_key_value_pairs

        self.key_select = pn.widgets.Select.from_param(
            self.param.key,
            name="",
            css_classes=["metadata-filter-row", "metadata-filter-key"],
            disabled=key_select_disabled,
        )

        self.operator_select = pn.widgets.Select.from_param(
            self.param.operator,
            name="",
            css_classes=["metadata-filter-row", "metadata-filter-operator"],
            disabled=True,
        )

        self.value_select = pn.widgets.Select.from_param(
            self.param.value,
            name="",
            css_classes=["metadata-filter-row", "metadata-filter-value"],
            disabled=True,
        )

        self.delete_button = pn.widgets.ButtonIcon(
            icon="trash",
            width=25,
            height=25,
            css_classes=["metadata-filter-row", "metadata-filter-delete"],
        )
        self.delete_button.on_click(on_delete_callback)

    @staticmethod
    def set_css(widget, valid=True):
        if valid:
            widget.css_classes = [
                c for c in widget.css_classes if c != "metadata-filter-row-error"
            ]
        else:
            widget.css_classes = widget.css_classes + ["metadata-filter-row-error"]

    @param.depends("key", watch=True)
    def key_did_change(self):
        if self.key == "":
            self.value_select.disabled = True
            self.operator_select.disabled = True
            return

        self.value_select.disabled = False
        self.operator_select.disabled = False
        self.param.value.objects = [""] + self.valid_key_value_pairs[self.key][1]

    def is_empty(self):
        return self.key == "" and self.operator == "" and self.value == ""

    def validate(self):
        if self.key == "":
            self.set_css(self.key_select, valid=False)
        else:
            self.set_css(self.key_select)

        if self.operator == "":
            self.set_css(self.operator_select, valid=False)
        else:
            self.set_css(self.operator_select)

        if self.value == "":
            self.set_css(self.value_select, valid=False)
        else:
            self.set_css(self.value_select)

        # if any attribute is "" then return False
        return not (self.key == "" or self.operator == "" or self.value == "")

    def construct_metadata_filter(self):
        # probably not required, but just in case
        if self.key == "" or self.operator == "" or self.value == "":
            return None

        return MetadataFilter(MetadataOperator[self.operator], self.key, self.value)

    def __panel__(self):
        return pn.Row(
            self.key_select,
            self.operator_select,
            self.value_select,
            self.delete_button,
        )


class MetadataFiltersBuilder(pn.viewable.Viewer):
    filter_rows = param.List([])
    corpus_names = param.List([])

    def __init__(self, corpus_metadata, **params):
        super().__init__(**params)

        self.corpus_names_select = pn.widgets.Select(
            options=[""] + self.corpus_names,
            name="",
            css_classes=["metadata-filter-row", "metadata-filter-key"],
        )

        self.corpus_metadata = corpus_metadata

        self.add_filter_row_button = pn.widgets.ButtonIcon(
            icon="circle-plus", width=25, height=25
        )
        self.add_filter_row_button.on_click(self.did_click_add_filter_row_button)

        self.delete_buttons = []

        self.filter_rows = [
            FilterRow(
                key="",
                operator="",
                value="",
                on_delete_callback=self.delete_filter_row,
            )
        ]

        self.corpus_names_select.param.watch(self.activate_filter_rows, "value")

    def activate_filter_rows(self, event):
        if event.new != "":
            self.filter_rows = [
                FilterRow(
                    valid_key_value_pairs=self.corpus_metadata[
                        self.corpus_names_select.value
                    ],
                    key="",
                    operator="",
                    value="",
                    on_delete_callback=self.delete_filter_row,
                )
            ]

    def did_click_add_filter_row_button(self, event):
        if not self.filter_rows[-1].is_empty():
            new_filter_row = FilterRow(
                valid_key_value_pairs=self.corpus_metadata[
                    self.corpus_names_select.value
                ],
                key="",
                operator="",
                value="",
                on_delete_callback=self.delete_filter_row,
            )
            self.filter_rows = self.filter_rows + [new_filter_row]

    def delete_filter_row(self, event):
        filter_row_to_remove = None
        for filter_row in self.filter_rows:
            if event.obj == filter_row.delete_button:
                filter_row_to_remove = filter_row
                break

        if filter_row_to_remove is None:
            return

        new_filter_rows = [f for f in self.filter_rows if f != filter_row_to_remove]
        if len(new_filter_rows) == 0:
            new_filter_rows.append(
                FilterRow(
                    valid_key_value_pairs=self.corpus_metadata[
                        self.corpus_names_select.value
                    ],
                    key="",
                    operator="",
                    value="",
                    on_delete_callback=self.delete_filter_row,
                )
            )

        self.filter_rows = new_filter_rows

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
            if filter_row.construct_metadata_filter() is not None
        ]

        if not metadata_filters:
            return None
        return MetadataFilter.and_(metadata_filters).to_primitive()

    def validate(self):
        result = True
        for filter_row in self.filter_rows:
            # If the last filter is empty, we do not want to validate it.
            # This allows to have only one empty filter, to question on the whole corpus.
            if filter_row == self.filter_rows[-1] and filter_row.is_empty():
                continue

            if not filter_row.validate():
                result = False
                # Do not break, we want to call validate() on every filters

        return result

    def __panel__(self):
        return pn.Column(
            pn.pane.HTML("<b>Available Corpuses</b>"),
            self.corpus_names_select,
            pn.pane.HTML("<b>Metadata Filters</b>"),
            pn.Column(
                self.render_filters_rows,
                pn.Row(self.add_filter_row_button),
                max_height=160,
            ),
            sizing_mode="stretch_both",
            height_policy="max",
        )
