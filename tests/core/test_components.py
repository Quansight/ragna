import pytest

from ragna.core import Message


class TestMessage:
    def test_fixed_content(self):
        content = "content"
        message = Message(content)

        assert message.content == content
        assert str(message) == content

    @pytest.mark.asyncio
    async def test_fixed_content_read(self):
        content = "content"
        message = Message(content)

        assert (await message.read()) == content

    @pytest.mark.asyncio
    async def test_fixed_content_iter(self):
        content = "content"
        message = Message(content)

        chunks = []
        async for chunk in message:
            chunks.append(chunk)
        assert chunks == [content]

    def make_content_stream(self, *chunks):
        async def content_stream():
            for chunk in chunks:
                yield chunk

        return content_stream()

    @pytest.mark.parametrize(
        "content_access",
        [
            pytest.param(lambda message: message.content, id="property"),
            str,
            repr,
        ],
    )
    def test_stream_content_access_error(self, content_access):
        content = "content"
        message = Message(self.make_content_stream(*content))

        with pytest.raises(RuntimeError):
            content_access(message)

    @pytest.mark.asyncio
    async def test_stream_content_iter(self):
        content = "content"
        message = Message(self.make_content_stream(*content))

        chunks = []
        async for chunk in message:
            chunks.append(chunk)
        assert chunks == list(content)

        assert message.content == content

    @pytest.mark.asyncio
    async def test_stream_content_read(self):
        content = "content"
        message = Message(self.make_content_stream(*content))

        assert (await message.read()) == content

        assert message.content == content
