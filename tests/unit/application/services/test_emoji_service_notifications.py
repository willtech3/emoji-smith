"""Users must hear back when their emoji will not arrive."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.errors import (
    ImageGenerationRejectedError,
    RateLimitExceededError,
)
from emojismith.domain.repositories.file_sharing_repository import FileSharingResult
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


def _png() -> bytes:
    buf = BytesIO()
    Image.new("RGBA", (128, 128), "red").save(buf, format="PNG")
    return buf.getvalue()


def _job() -> EmojiGenerationJob:
    return EmojiGenerationJob.create_new(
        user_description="facepalm",
        emoji_name="facepalm",
        message_text="deploy failed",
        user_id="U1",
        channel_id="C1",
        timestamp="1.2",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
        image_provider="openai",
    )


@pytest.fixture()
def notifier() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def file_sharing_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def service(notifier, file_sharing_repo) -> EmojiCreationService:
    generator = AsyncMock()
    generator.generate_image.return_value = [_png()]
    factory = MagicMock()
    factory.create.return_value = generator
    processor = MagicMock()
    processor.process.side_effect = lambda data: data
    validator = MagicMock()
    validator.validate_and_create_emoji.side_effect = lambda data, name: (
        GeneratedEmoji(image_data=data, name=name)
    )
    prompt_use_case = AsyncMock()
    prompt_use_case.build_prompt.return_value = "prompt"
    return EmojiCreationService(
        slack_repo=AsyncMock(),
        build_prompt_use_case=prompt_use_case,
        image_generator_factory=factory,
        image_processor=processor,
        emoji_validator=validator,
        style_template_manager=MagicMock(),
        file_sharing_repo=file_sharing_repo,
        user_notifier=notifier,
    )


def _text(notifier: AsyncMock) -> str:
    return notifier.notify_user.call_args.kwargs["text"]


@pytest.mark.unit()
class TestEmojiServiceNotifications:
    async def test_process_job_when_every_share_fails_tells_requester(
        self, service, notifier, file_sharing_repo
    ):
        file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=False, error="not_in_channel"
        )

        await service.process_emoji_generation_job(_job())

        notifier.notify_user.assert_awaited_once()
        assert notifier.notify_user.call_args.kwargs["user_id"] == "U1"
        assert "invite me" in _text(notifier)
        assert "not_in_channel" not in _text(notifier)

    async def test_process_job_when_share_succeeds_sends_no_notice(
        self, service, notifier, file_sharing_repo
    ):
        file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=True, thread_ts="1.2"
        )

        await service.process_emoji_generation_job(_job())

        notifier.notify_user.assert_not_awaited()

    async def test_notify_generation_failed_for_policy_refusal_suggests_rephrasing(
        self, service, notifier
    ):
        await service.notify_generation_failed(
            _job(), ImageGenerationRejectedError("moderation_blocked: internal detail")
        )

        assert ":facepalm:" in _text(notifier)
        assert "rephrasing" in _text(notifier)
        assert "internal detail" not in _text(notifier)

    async def test_notify_generation_failed_for_rate_limit_suggests_waiting(
        self, service, notifier
    ):
        await service.notify_generation_failed(_job(), RateLimitExceededError("429"))

        assert "few minutes" in _text(notifier)

    async def test_notify_generation_failed_for_unknown_error_hides_details(
        self, service, notifier
    ):
        await service.notify_generation_failed(_job(), RuntimeError("sk-secret"))

        assert "sk-secret" not in _text(notifier)
        assert "try again" in _text(notifier)

    async def test_notify_generation_failed_when_notifier_raises_does_not_propagate(
        self, service, notifier
    ):
        notifier.notify_user.side_effect = RuntimeError("slack down")

        await service.notify_generation_failed(_job(), RuntimeError("boom"))
