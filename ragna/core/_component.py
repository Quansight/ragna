import functools
import inspect

from pydantic import create_model

from ._requirement import RequirementMixin


class RagComponent(RequirementMixin):
    @classmethod
    def display_name(cls) -> str:
        return cls.__name__

    def __init__(self, config) -> None:
        self.config = config
        self.logger = config.get_logger(name=str(self))

    def __repr__(self) -> str:
        return self.display_name()

    __ragna_protocol_methods__: list[str]

    @classmethod
    @functools.cache
    def _models(cls):
        protocol_cls, protocol_methods = next(
            (cls_, cls_.__ragna_protocol_methods__)
            for cls_ in cls.__mro__
            if "__ragna_protocol_methods__" in cls_.__dict__
        )
        models = {}
        for method_name in protocol_methods:
            method = getattr(cls, method_name)
            concrete_params = inspect.signature(method).parameters
            protocol_params = inspect.signature(
                getattr(protocol_cls, method_name)
            ).parameters
            extra_param_names = concrete_params.keys() - protocol_params.keys()

            models[(cls, method_name)] = create_model(
                f"{cls.__name__}.{method_name}",
                **{
                    (param := concrete_params[param_name]).name: (
                        param.annotation,
                        param.default
                        if param.default is not inspect.Parameter.empty
                        else ...,
                    )
                    for param_name in extra_param_names
                },
            )
        return models
