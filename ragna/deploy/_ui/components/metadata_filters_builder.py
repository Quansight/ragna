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
        if valid_key_value_pairs:
            self.valid_key_value_pairs = valid_key_value_pairs

        self.key_select = pn.widgets.Select.from_param(
            self.param.key,
            name="",
            css_classes=["metadata-filter", "metadata-filter-key"],
            disabled=key_select_disabled,
        )

        self.operator_select = pn.widgets.Select.from_param(
            self.param.operator,
            name="",
            css_classes=["metadata-filter", "metadata-filter-operator"],
            disabled=True,
        )

        self.value_select = pn.widgets.Select.from_param(
            self.param.value,
            name="",
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

    @staticmethod
    def set_css(widget, valid=True):
        if valid:
            widget.css_classes = [
                c for c in widget.css_classes if c != "metadata-filter-error"
            ]
        else:
            widget.css_classes = widget.css_classes + ["metadata-filter-error"]

    @param.depends("key", watch=True)
    def key_did_change(self):
        if self.key == "":
            self.value_select.disabled = True
            self.operator_select.disabled = True
            return

        self.value_select.disabled = False
        self.operator_select.disabled = False
        self.param.value.objects = [""] + self.valid_key_value_pairs[self.key]

    def __panel__(self):
        return pn.Row(
            self.key_select,
            self.operator_select,
            self.value_select,
            self.delete_button,
        )

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
        if self.key == "" or self.operator == "" or self.value == "":
            return None
        return MetadataFilter(self.operator, self.key, self.value)


class MetadataFiltersBuilder(pn.viewable.Viewer):
    metadata_filters = param.List([])
    corpus_names = param.List([])

    def __init__(self, corpus_metadata, **params):
        super().__init__(**params)

        self.corpus_names_select = pn.widgets.Select(
            options=[""] + self.corpus_names,
            name="",
            css_classes=["metadata-filter", "metadata-filter-key"],
        )

        self.corpus_metadata = corpus_metadata

        self.add_filter_button = pn.widgets.ButtonIcon(
            icon="circle-plus", width=25, height=25
        )
        self.add_filter_button.on_click(self.did_click_add_filter_button)

        self.delete_buttons = []

        self.metadata_filters = [
            FilterRow(
                key="",
                operator="",
                value="",
                on_delete_callback=self.delete_metadata_filter,
            )
        ]

        self.corpus_names_select.param.watch(self.activate_filter_rows, "value")

    def activate_filter_rows(self, event):
        if event.new != "":
            self.metadata_filters = [
                FilterRow(
                    valid_key_value_pairs=self.corpus_metadata[
                        self.corpus_names_select.value
                    ],
                    key="",
                    operator="",
                    value="",
                    on_delete_callback=self.delete_metadata_filter,
                )
            ]

    def did_click_add_filter_button(self, event):
        if not self.metadata_filters[-1].is_empty():
            new_metadata_filter_row = FilterRow(
                valid_key_value_pairs=self.corpus_metadata[
                    self.corpus_names_select.value
                ],
                key="",
                operator="",
                value="",
                on_delete_callback=self.delete_metadata_filter,
            )
            self.metadata_filters = self.metadata_filters + [new_metadata_filter_row]

    def delete_metadata_filter(self, event):
        filter_row_to_remove = None
        for filter_row in self.metadata_filters:
            if event.obj == filter_row.delete_button:
                filter_row_to_remove = filter_row
                break

        if filter_row_to_remove is None:
            return

        new_filter_rows = [
            f for f in self.metadata_filters if f != filter_row_to_remove
        ]
        if len(new_filter_rows) == 0:
            new_filter_rows.append(
                FilterRow(
                    valid_key_value_pairs=self.corpus_metadata[
                        self.corpus_names_select.value
                    ],
                    key="",
                    operator="",
                    value="",
                    on_delete_callback=self.delete_metadata_filter,
                )
            )

        self.metadata_filters = new_filter_rows

    @pn.depends("metadata_filters")
    def render_metadata_filters_rows(self):
        return pn.Column(
            *self.metadata_filters,
            css_classes=["metadata-filters"],
        )

    def construct_metadata_filters(self):
        metadata_filters = [
            filter_row.construct_metadata_filter()
            for filter_row in self.metadata_filters
            if filter_row.construct_metadata_filter() is not None
        ]

        combined_metadata_filters = MetadataFilter.and_(metadata_filters).to_primitive()

        if not combined_metadata_filters:
            return None
        else:
            return combined_metadata_filters

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
            pn.pane.Markdown("#### Available Corpuses"),
            self.corpus_names_select,
            pn.pane.Markdown("#### Metadata Filters"),
            pn.Column(
                self.render_metadata_filters_rows,
                pn.Row(self.add_filter_button),
                max_height=80,
                height_policy="min",
            ),
            sizing_mode="stretch_both",
            height_policy="max",
        )
