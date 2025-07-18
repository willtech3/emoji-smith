"""Emoji creation service for orchestrating the workflow."""

import logging
from typing import Any

from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.repositories.file_sharing_repository import FileSharingRepository
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from emojismith.domain.repositories.slack_repository import SlackRepository
from emojismith.domain.services.emoji_sharing_service import (
    EmojiSharingContext,
    EmojiSharingService,
    WorkspaceType,
)
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
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
        emoji_generator: EmojiGenerationService,
        build_prompt_use_case: BuildPromptUseCase,
        job_queue: JobQueueRepository | None = None,
        file_sharing_repo: FileSharingRepository | None = None,
        sharing_service: EmojiSharingService | None = None,
    ) -> None:
        self._slack_repo = slack_repo
        self._emoji_generator = emoji_generator
        self._build_prompt_use_case = build_prompt_use_case
        self._job_queue = job_queue
        self._file_sharing_repo = file_sharing_repo
        self._sharing_service = sharing_service or EmojiSharingService()

    async def process_emoji_generation_job(self, job: EmojiGenerationJob) -> None:
        """Process emoji generation job from background worker."""
        self._logger.info(
            "Processing emoji generation job",
            extra={"job_id": job.job_id, "user_id": job.user_id},
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

        # Generate emoji using the enhanced prompt
        emoji = await self._emoji_generator.generate_from_prompt(enhanced_prompt, name)

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
        )

        # Process using the main method
        await self.process_emoji_generation_job(job)
