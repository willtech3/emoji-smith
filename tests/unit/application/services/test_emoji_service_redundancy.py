from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import (
    EmojiGenerationPreferences,
    EmojiSharingPreferences,
    NumberOfImages,
)


@pytest.mark.asyncio()
async def test_subsequent_images_have_no_initial_comment():
    """Verify that when multiple images are generated, only the first gets a comment."""
    # Mock dependencies
    mock_slack_repo = AsyncMock()
    mock_image_generator = AsyncMock()

    mock_image_generator_factory = MagicMock()
    mock_image_generator_factory.create.return_value = mock_image_generator

    mock_image_processor = MagicMock()
    mock_image_processor.resize_for_emoji.side_effect = lambda data: data

    mock_emoji_validator = MagicMock()
    from emojismith.domain.entities.generated_emoji import GeneratedEmoji

    mock_emoji_validator.validate_and_create.side_effect = (
        lambda data, name: GeneratedEmoji(image_data=data, name=name)
    )

    mock_style_template_manager = MagicMock()
    mock_file_sharing_repo = AsyncMock()

    # Mock instruction service to return a known string
    mock_instruction_service = MagicMock()
    mock_instruction_service.build_initial_comment.return_value = (
        "Generated custom emoji: :test_emoji:"
    )
    mock_instruction_service.build_upload_instructions.return_value = "Instructions"

    mock_build_prompt_use_case = AsyncMock()
    mock_build_prompt_use_case.build_prompt.return_value = "prompt"

    emoji_service = EmojiCreationService(
        slack_repo=mock_slack_repo,
        build_prompt_use_case=mock_build_prompt_use_case,
        image_generator_factory=mock_image_generator_factory,
        image_processor=mock_image_processor,
        emoji_validator=mock_emoji_validator,
        style_template_manager=mock_style_template_manager,
        file_sharing_repo=mock_file_sharing_repo,
        instruction_service=mock_instruction_service,
    )

    # Job for 2 images
    job = EmojiGenerationJob.create_new(
        message_text="test",
        user_description="test",
        emoji_name="test_emoji",
        user_id="U1",
        channel_id="C1",
        timestamp="123",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
        generation_preferences=EmojiGenerationPreferences(
            num_images=NumberOfImages.TWO
        ),
    )

    # Mock file sharing
    mock_file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
        success=True,
        thread_ts="123",
        file_url="url",
    )

    # Mock image generation
    img = Image.new("RGBA", (10, 10), "red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    mock_image_generator.generate_image.return_value = [buf.getvalue(), buf.getvalue()]

    # Run
    await emoji_service.process_emoji_generation_job(job)

    # Assert
    assert mock_file_sharing_repo.share_emoji_file.call_count == 2

    call1 = mock_file_sharing_repo.share_emoji_file.call_args_list[0]
    call2 = mock_file_sharing_repo.share_emoji_file.call_args_list[1]

    # First call should have the comment
    assert call1.kwargs.get("initial_comment") == "Generated custom emoji: :test_emoji:"

    # Second call should NOT have the comment (should be None)
    # This assertion is expected to fail before the fix
    assert call2.kwargs.get("initial_comment") is None
