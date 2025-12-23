"""Emoji creation service for orchestrating the workflow."""

import logging
from typing import Any

from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.factories.image_generator_factory import ImageGeneratorFactory
from emojismith.domain.repositories.file_sharing_repository import FileSharingRepository
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from emojismith.domain.repositories.slack_repository import SlackRepository
from emojismith.domain.services.emoji_sharing_service import (
    EmojiSharingContext,
    EmojiSharingService,
    WorkspaceType,
)
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.services.style_template_manager import StyleTemplateManager
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.value_objects.image_provider import ImageProvider
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    EmojiStylePreferences,
)


class EmojiCreationService:
    """Service for orchestrating emoji creation workflow."""

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        slack_repo: SlackRepository,
        build_prompt_use_case: BuildPromptUseCase,
        image_generator_factory: ImageGeneratorFactory,
        image_processor: ImageProcessor,
        emoji_validator: EmojiValidationService,
        style_template_manager: StyleTemplateManager,
        job_queue: JobQueueRepository | None = None,
        file_sharing_repo: FileSharingRepository | None = None,
        sharing_service: EmojiSharingService | None = None,
    ) -> None:
        self._slack_repo = slack_repo
        self._build_prompt_use_case = build_prompt_use_case
        self._image_generator_factory = image_generator_factory
        self._image_processor = image_processor
        self._emoji_validator = emoji_validator
        self._style_template_manager = style_template_manager
        self._job_queue = job_queue
        self._file_sharing_repo = file_sharing_repo
        self._sharing_service = sharing_service or EmojiSharingService()

    async def process_emoji_generation_job(self, job: EmojiGenerationJob) -> None:
        """Process emoji generation job from background worker."""
        # Select provider based on job configuration
        provider = ImageProvider.from_string(job.image_provider)
        self._logger.info(
            "Processing emoji generation job",
            extra={
                "job_id": job.job_id,
                "user_id": job.user_id,
                "image_provider": provider.value,
            },
        )

        spec = EmojiSpecification(
            description=job.user_description,
            context=job.message_text,
            style=job.style_preferences,
        )

        # Build and enhance prompt using the use case
        enhanced_prompt = await self._build_prompt_use_case.build_prompt(
            spec=spec,
            enhance=True,  # Enable AI enhancement
        )

        # Use provided emoji name, sanitize for Slack (max 32 chars)
        name = job.emoji_name.replace(" ", "_").lower()[:32]

        # Create image generator for the selected provider
        image_generator = self._image_generator_factory.create(provider)

        # Create emoji generation service with the selected provider
        emoji_generation_service = EmojiGenerationService(
            image_generator=image_generator,
            image_processor=self._image_processor,
            emoji_validator=self._emoji_validator,
            style_template_manager=self._style_template_manager,
        )

        # Generate emoji using the enhanced prompt
        emoji = await emoji_generation_service.generate_from_prompt(
            enhanced_prompt, name
        )

        # Get workspace type from sharing service
        workspace_type = self._sharing_service.workspace_type

        # Create sharing context
        from shared.domain.entities.slack_message import SlackMessage

        original_message = SlackMessage(
            text=job.message_text,
            user_id=job.user_id,
            channel_id=job.channel_id,
            timestamp=job.timestamp,
            team_id=job.team_id,
        )

        context = EmojiSharingContext(
            emoji=emoji,
            original_message=original_message,
            preferences=job.sharing_preferences
            or EmojiSharingPreferences.default_for_context(
                is_in_thread=bool(
                    job.sharing_preferences and job.sharing_preferences.thread_ts
                ),
                thread_ts=(
                    job.sharing_preferences.thread_ts
                    if job.sharing_preferences
                    else None
                ),
            ),
            workspace_type=workspace_type,
        )

        if workspace_type == WorkspaceType.ENTERPRISE_GRID:
            # Try direct upload for Enterprise Grid
            uploaded = await self._slack_repo.upload_emoji(
                name=name, image_data=emoji.image_data
            )
            if uploaded:
                # Add reaction if upload succeeded
                try:
                    await self._slack_repo.add_emoji_reaction(
                        emoji_name=name,
                        channel_id=job.channel_id,
                        timestamp=job.timestamp,
                    )
                except Exception as e:
                    self._logger.error(f"Failed to add emoji reaction: {e}")
        else:
            # Use file sharing for non-Enterprise workspaces
            if self._file_sharing_repo:
                result = await self._file_sharing_repo.share_emoji_file(
                    emoji=emoji,
                    channel_id=job.channel_id,
                    preferences=context.preferences,
                    requester_user_id=job.user_id,
                    original_message_ts=job.timestamp,
                )
                if result.success:
                    self._logger.info(
                        "Successfully shared emoji file",
                        extra={
                            "emoji_name": name,
                            "thread_ts": result.thread_ts,
                            "file_url": result.file_url,
                        },
                    )
                else:
                    self._logger.error(f"Failed to share emoji file: {result.error}")

        self._logger.info(
            "Successfully processed emoji generation job",
            extra={"job_id": job.job_id, "emoji_name": name},
        )

    async def process_emoji_generation_job_dict(self, job_data: dict[str, Any]) -> None:
        """Generate emoji using dict payload, upload to Slack, and add reaction."""
        # Convert dict to job entity for consistent processing
        job = EmojiGenerationJob.create_new(
            message_text=job_data["message_text"],
            user_description=job_data["user_description"],
            user_id=job_data["user_id"],
            channel_id=job_data["channel_id"],
            timestamp=job_data["timestamp"],
            team_id=job_data["team_id"],
            sharing_preferences=(
                EmojiSharingPreferences.from_dict(job_data["sharing_preferences"])
                if job_data.get("sharing_preferences")
                else EmojiSharingPreferences.default_for_context()
            ),
            style_preferences=(
                EmojiStylePreferences.from_dict(job_data["style_preferences"])
                if job_data.get("style_preferences")
                else EmojiStylePreferences()
            ),
            thread_ts=job_data.get("thread_ts"),
            emoji_name=job_data["emoji_name"],
            image_provider=job_data.get("image_provider", "openai"),
        )

        # Process using the main method
        await self.process_emoji_generation_job(job)
