# class ComponentMeta()
import abc
import inspect
from typing import Type

from pydantic import BaseModel, create_model


def unpack(method, to_unpack):
    def wrapper(*args, **kwargs):
        if "chat_config" in kwargs:
            if len(kwargs) > 1:
                raise RuntimeError()

            chat_config = kwargs["chat_config"]

            if not isinstance(chat_config, BaseModel):
                raise RuntimeError()

            kwargs = {name: getattr(chat_config, name) for name in to_unpack}

        return method(*args, **kwargs)

    return wrapper


class Component(abc.ABC):
    model: Type[BaseModel]

    def __init_subclass__(cls):
        if inspect.isabstract(cls):
            return

        for_models = {}
        for name in cls.__chat_config_unpacking__:
            method = getattr(cls, name)

            for_model = {
                parameter.name: (
                    parameter.annotation,
                    parameter.default
                    if parameter.default is not inspect.Parameter.empty
                    else ...,
                )
                for parameter in inspect.signature(method).parameters.values()
                if parameter.kind is inspect.Parameter.KEYWORD_ONLY
            }
            for_models.update(for_model)

            setattr(cls, name, unpack(method, for_models))

        setattr(
            cls,
            "model",
            property(
                lambda self, model=create_model("ComponentModel", **for_models): model
            ),
        )


class Llm(Component):
    __chat_config_unpacking__ = frozenset(["complete"])

    @abc.abstractmethod
    def complete(self, prompt: str, sources: list):
        ...


class MyLlm(Llm):
    def complete(
        self,
        prompt: str,
        sources: list,
        *,
        user: str,
        max_new_tokens: int = 256,
    ):
        print()


llm = MyLlm()


from pydantic import BaseModel


class CompleteModel(BaseModel):
    user: str
    max_new_tokens: int = 17
    foo: str = "bar"


llm.complete(
    "prompt", ["source"], chat_config=CompleteModel(max_new_tokens=13, user="user")
)

model = llm.model

# print(model)
# print(CompleteModel)
# print(CompleteModel(user="user"))

a = model(user="user")

print(model(user="user").dict())


# if the method takes pos args, plus a single chat_config, do nothing
# if the method takes pos args, plus chat_config and some other keywords, error
