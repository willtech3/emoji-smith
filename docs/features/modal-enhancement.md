# Modal Enhancement Specification: Maximum Capability with Progressive Disclosure

> **Generate the highest quality Slack reaction emojis with a frictionless UX**

### Implementation Status (Audited 2025-12-25)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Model Upgrades | ✅ Complete | gpt-image-1.5, imagen-4.0-ultra fallback |
| Phase 2: Domain Value Objects | ✅ Complete | BackgroundType, QualityLevel, NumberOfImages, EmojiGenerationPreferences |
| Phase 3: Modal Builder | ✅ Complete | Moved to application layer (architectural fix) |
| Phase 4: Infrastructure Updates | ✅ Complete | Multi-image support in both providers |
| Phase 5: Webhook Handler | ⚠️ Partial | 5.1 ✅, 5.2 ❌ (multi-image response not implemented) |
| Phase 6: Prompt Enhancement | ✅ Complete | Background suffix + image processor |
| Phase 7: Verification | ⚠️ Partial | Unit tests pass (262), integration/manual tests not verified |

## Overview

This specification details the implementation of advanced emoji customization options in the emoji-smith Slack modal. The design prioritizes:

1. **Frictionless simple mode** — Non-technical users can describe an emoji and get results with minimal friction
2. **Maximum capability** — Advanced users can access all model parameters for full control
3. **Best defaults** — Simple mode uses optimal settings for high-quality emoji generation
4. **Progressive disclosure** — Advanced options are hidden until requested

---

## Verified API Reference

> [!IMPORTANT]
> All parameters below have been verified against official API documentation (December 2025).

### OpenAI gpt-image-1.5 API

**Source:** [OpenAI Image Generation API](https://platform.openai.com/docs/api-reference/images)

| Parameter | Type | Values | Default | Notes |
|-----------|------|--------|---------|-------|
| `model` | string | `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini` | Required | |
| `prompt` | string | Max 32,000 chars | Required | |
| `n` | integer | 1-10 | 1 | gpt-image models only |
| `size` | string | `1024x1024`, `1536x1024`, `1024x1536`, `auto` | `auto` | |
| `quality` | string | `auto`, `high`, `medium`, `low` | `auto` | |
| `background` | string | `transparent`, `opaque`, `auto` | `auto` | gpt-image only |
| `output_format` | string | `png`, `jpeg`, `webp` | `png` | Use `png`/`webp` for transparency |

**Response:** Returns `b64_json` encoded image data.

---

### Google Gemini Image Generation API (Nano Banana)

**Source:** [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)

| Parameter | Type | Values | Default | Notes |
|-----------|------|--------|---------|-------|
| `model` | string | `gemini-3-pro-image-preview`, `gemini-2.5-flash-image` | Required | |
| `response_modalities` | list | `['IMAGE']`, `['TEXT', 'IMAGE']` | `['TEXT', 'IMAGE']` | Set to `['IMAGE']` for images only |
| `aspect_ratio` | string | `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` | `1:1` | Via `ImageConfig` |
| `image_size` | string | `1K`, `2K`, `4K` | `1K` | gemini-3-pro only supports higher sizes |

**Python SDK:**
```python
response = await client.aio.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
        ),
    ),
)
```

> [!WARNING]  
> **No transparent background parameter.** Transparency must be requested in the prompt text:
> "...with a transparent background, optimized for 128x128 Slack emoji"

---

### Google Imagen 4 API

**Source:** [Imagen API](https://ai.google.dev/gemini-api/docs/imagen)

| Model ID | Quality | Use Case |
|----------|---------|----------|
| `imagen-4.0-ultra-generate-001` | Highest | Professional assets |
| `imagen-4.0-generate-001` | Standard | General use |
| `imagen-4.0-fast-generate-001` | Fast | Low latency |

| Parameter | Type | Values | Default | Notes |
|-----------|------|--------|---------|-------|
| `number_of_images` | integer | 1-4 | 4 | |
| `aspect_ratio` | string | `1:1`, `3:4`, `4:3`, `9:16`, `16:9` | `1:1` | |
| `image_size` | string | `1K`, `2K` | `1K` | Ultra only for 2K |
| `person_generation` | string | `dont_allow`, `allow_adult`, `allow_all` | | |

**Python SDK:**
```python
response = await client.aio.models.generate_images(
    model="imagen-4.0-ultra-generate-001",
    prompt=prompt,
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
    ),
)

# Access image bytes:
image_bytes = response.generated_images[0].image.image_bytes
```

> [!WARNING]  
> **No transparent background parameter.** Transparency must be requested in prompt text.

---

### Slack Custom Emoji Requirements

**Source:** [Slack Help - Add custom emoji](https://slack.com/help/articles/206870177) (Verified December 2025)

| Constraint | Requirement | Notes |
|------------|-------------|-------|
| **File Size** | **< 128 KB** | Hard limit, images larger will be rejected |
| **Formats** | PNG, JPG, GIF | PNG recommended for transparency |
| **Dimensions** | **128 × 128 px** recommended | Larger images are auto-resized |
| **Aspect Ratio** | **1:1 (square)** | Non-square images will be cropped |
| **GIF Frames** | Max 50 frames | For animated emojis |

> [!IMPORTANT]
> **Display Size:** Emojis display at **20-32px** in messages. Generate at 128x128px minimum for Retina displays, but optimize for small-size readability (bold shapes, high contrast).

**Implications for Image Generation:**

1. **Generate at 1024×1024** (native API size) then **compress to < 128KB** during post-processing
2. **Always use 1:1 aspect ratio** for both Google and OpenAI APIs
3. **Output format:** PNG for transparency support
4. **Prompt optimization:** Include "bold shapes, high contrast, readable at small sizes"

---

## Model Configuration


| Provider | Primary Model | Fallback Model | Use Case |
|----------|--------------|----------------|----------|
| **OpenAI** | `gpt-image-1.5` | `gpt-image-1-mini` | Highest quality, native transparent bg |
| **Google** | `gemini-3-pro-image-preview` | `imagen-4.0-ultra-generate-001` | Professional assets, "Thinking" feature |

### Default Settings (Simple Mode)

| Setting | Default Value | Rationale |
|---------|--------------|-----------|
| Number of images | 1 | Fast feedback, opt-in for more |
| Background | Transparent | Critical for Slack emoji display |
| Quality | High | Best visual fidelity |
| Aspect Ratio | 1:1 | Required for Slack emojis |
| Model | Nano Banana Pro | Best quality with reasoning |

---

## UX Design

### Simple Mode (Collapsed - Default)

```
┌─────────────────────────────────────────────────────────────────┐
│  Create Emoji                                           [Cancel]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Describe your emoji                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ A happy dancing banana wearing sunglasses                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [▼ Show Advanced Options]                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                            [✨ Generate Emoji] │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Emoji name auto-generated from description (e.g., `happy_dancing_banana`)
- Uses best defaults: transparent background, high quality, 1 image, Pro model
- For Google models: prompt automatically appends "transparent background" requirement

---

### Advanced Mode (Expanded)

```
┌─────────────────────────────────────────────────────────────────┐
│  Create Emoji                                           [Cancel]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Describe your emoji                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ A happy dancing banana wearing sunglasses                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Emoji name (optional)                                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ dancing_banana                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│  Will become :dancing_banana:                                   │
│                                                                 │
│  ─────────────── Advanced Options ──────────────────────────── │
│                                                                 │
│  Image Model              Quality                               │
│  ┌──────────────────────┐ ┌──────────────────────┐              │
│  │ Nano Banana Pro    ▼ │ │ High               ▼ │              │
│  └──────────────────────┘ └──────────────────────┘              │
│                                                                 │
│  Background               Number of Options                     │
│  ┌──────────────────────┐ ┌──────────────────────┐              │
│  │ Transparent        ▼ │ │ 1 image            ▼ │              │
│  └──────────────────────┘ └──────────────────────┘              │
│                                                                 │
│  Style (optional)                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ cartoon, pixel art, minimalist, 3D, watercolor...          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [▲ Hide Advanced Options]                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                            [✨ Generate Emoji] │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Model Upgrades

- [✅] **1.1** Upgrade OpenAI primary model to `gpt-image-1.5`
  - File: **[MODIFY]** `src/emojismith/infrastructure/openai/openai_api.py`
  - Line ~131, change model name:
  
  ```python
  model="gpt-image-1.5",  # Was: gpt-image-1
  ```

- [✅] **1.2** Update Google fallback to Imagen 4 Ultra
  - File: **[MODIFY]** `src/emojismith/infrastructure/google/gemini_api.py`
  - Line ~31, change fallback model:
  
  ```python
  fallback_model: str = "imagen-4.0-ultra-generate-001",  # Was: gemini-2.5-flash-image
  ```

---

### Phase 2: Domain Value Objects

- [✅] **2.1** Add new enums to `value_objects.py`
  - File: **[MODIFY]** `src/shared/domain/value_objects.py`
  - Add after `Tone` class (around line 197):

  ```python
  class BackgroundType(Enum):
      """Background transparency for generated emoji."""
      TRANSPARENT = "transparent"
      OPAQUE = "opaque"
      AUTO = "auto"

      @classmethod
      def from_form_value(cls, value: str) -> "BackgroundType":
          mapping = {
              "transparent": cls.TRANSPARENT,
              "opaque": cls.OPAQUE,
              "auto": cls.AUTO,
          }
          return mapping.get(value, cls.TRANSPARENT)


  class QualityLevel(Enum):
      """Quality level for image generation."""
      AUTO = "auto"      # Model decides
      LOW = "low"        # Fastest, ~2s
      MEDIUM = "medium"  # Balanced
      HIGH = "high"      # Best quality, ~5s

      @classmethod
      def from_form_value(cls, value: str) -> "QualityLevel":
          mapping = {
              "auto": cls.AUTO,
              "low": cls.LOW,
              "medium": cls.MEDIUM,
              "high": cls.HIGH,
          }
          return mapping.get(value, cls.HIGH)


  class NumberOfImages(Enum):
      """Number of image variations to generate."""
      ONE = 1
      TWO = 2
      FOUR = 4

      @classmethod
      def from_form_value(cls, value: str) -> "NumberOfImages":
          mapping = {"1": cls.ONE, "2": cls.TWO, "4": cls.FOUR}
          return mapping.get(value, cls.ONE)
  ```

- [✅] **2.2** Update `EmojiStylePreferences` dataclass
  - File: **[MODIFIED]** `src/shared/domain/value_objects.py`
  - **Note:** Class is named `EmojiGenerationPreferences` in implementation (not `EmojiStylePreferences`)

  ```python
  @dataclass(frozen=True)
  class EmojiStylePreferences:
      """User preferences for emoji generation."""
      background: BackgroundType = BackgroundType.TRANSPARENT
      quality: QualityLevel = QualityLevel.HIGH
      num_images: NumberOfImages = NumberOfImages.ONE
      style_text: str = ""  # Free-form style input (e.g., "cartoon", "pixel art")

      def to_prompt_fragment(self) -> str:
          """Generate prompt fragment for style."""
          parts = []
          if self.style_text:
              parts.append(self.style_text.strip())
          return ", ".join(parts) if parts else ""

      def get_background_prompt_suffix(self) -> str:
          """Get prompt suffix for Slack emoji optimization (for Google APIs).
          
          Includes transparency and small-size readability guidance per Slack requirements.
          """
          base = ", bold shapes, high contrast, optimized for 128x128 Slack emoji display at 20-32px"
          if self.background == BackgroundType.TRANSPARENT:
              return f", transparent background{base}"
          return base

      @classmethod
      def from_form_values(
          cls,
          background: str = "transparent",
          quality: str = "high",
          num_images: str = "1",
          style_text: str = "",
      ) -> "EmojiStylePreferences":
          return cls(
              background=BackgroundType.from_form_value(background),
              quality=QualityLevel.from_form_value(quality),
              num_images=NumberOfImages.from_form_value(num_images),
              style_text=style_text,
          )

      def to_dict(self) -> dict[str, str]:
          return {
              "background": self.background.value,
              "quality": self.quality.value,
              "num_images": str(self.num_images.value),
              "style_text": self.style_text,
          }

      @classmethod
      def from_dict(cls, data: dict[str, str]) -> "EmojiStylePreferences":
          import logging
          try:
              return cls(
                  background=BackgroundType(data.get("background", "transparent")),
                  quality=QualityLevel(data.get("quality", "high")),
                  num_images=NumberOfImages(int(data.get("num_images", "1"))),
                  style_text=data.get("style_text", ""),
              )
          except (ValueError, KeyError) as e:
              logging.getLogger(__name__).warning(f"Invalid style preferences: {e}")
              return cls()
  ```

---

### Phase 3: Modal Builder

- [✅] **3.1** Create `ModalBuilder` class
  - File: **[CREATED]** `src/emojismith/application/modal_builder.py`
  - **Note:** Location changed from spec — moved to application layer to fix architectural layering (application components shouldn't import from presentation layer)

  ```python
  """Slack modal builder for emoji creation.

  Implements progressive disclosure for maximum capability with minimal friction.
  """

  from __future__ import annotations

  import json
  from typing import Any


  class EmojiCreationModalBuilder:
      """Builds Slack modal views with progressive disclosure.

      Simple mode: Just description input + generate button
      Advanced mode: Full control over model, quality, background, count, style
      """

      # Block IDs - must match extraction in submission handler
      DESCRIPTION_BLOCK = "emoji_description"
      EMOJI_NAME_BLOCK = "emoji_name"
      IMAGE_PROVIDER_BLOCK = "image_provider_block"
      QUALITY_BLOCK = "quality_block"
      BACKGROUND_BLOCK = "background_block"
      NUM_IMAGES_BLOCK = "num_images_block"
      STYLE_TEXT_BLOCK = "style_text_block"
      STYLE_TOGGLE_BLOCK = "style_toggle_block"

      # Action IDs - must match extraction in submission handler
      DESCRIPTION_ACTION = "description"
      NAME_ACTION = "name"
      PROVIDER_ACTION = "image_provider_select"
      QUALITY_ACTION = "quality_select"
      BACKGROUND_ACTION = "background_select"
      NUM_IMAGES_ACTION = "num_images_select"
      STYLE_TEXT_ACTION = "style_text_input"
      STYLE_TOGGLE_ACTION = "toggle_style_options"

      MODAL_CALLBACK_ID = "emoji_creation_modal"

      def build_collapsed_view(self, metadata: dict[str, Any]) -> dict[str, Any]:
          """Build simple mode modal (description only)."""
          metadata_with_state = {**metadata, "show_advanced": False}

          blocks = [
              # Description Input (main focus)
              {
                  "type": "input",
                  "block_id": self.DESCRIPTION_BLOCK,
                  "element": {
                      "type": "plain_text_input",
                      "action_id": self.DESCRIPTION_ACTION,
                      "multiline": True,
                      "placeholder": {
                          "type": "plain_text",
                          "text": "A happy dancing banana wearing sunglasses...",
                      },
                  },
                  "label": {"type": "plain_text", "text": "Describe your emoji"},
              },
              # Toggle button
              {
                  "type": "actions",
                  "block_id": self.STYLE_TOGGLE_BLOCK,
                  "elements": [
                      {
                          "type": "button",
                          "action_id": self.STYLE_TOGGLE_ACTION,
                          "text": {
                              "type": "plain_text",
                              "text": "▼ Show Advanced Options",
                              "emoji": True,
                          },
                          "value": "expand",
                      }
                  ],
              },
          ]

          return {
              "type": "modal",
              "callback_id": self.MODAL_CALLBACK_ID,
              "title": {"type": "plain_text", "text": "Create Emoji"},
              "submit": {"type": "plain_text", "text": "✨ Generate"},
              "close": {"type": "plain_text", "text": "Cancel"},
              "blocks": blocks,
              "private_metadata": json.dumps(metadata_with_state),
          }

      def build_expanded_view(self, metadata: dict[str, Any]) -> dict[str, Any]:
          """Build advanced mode modal (full options)."""
          metadata_with_state = {**metadata, "show_advanced": True}

          blocks = [
              # Description Input
              {
                  "type": "input",
                  "block_id": self.DESCRIPTION_BLOCK,
                  "element": {
                      "type": "plain_text_input",
                      "action_id": self.DESCRIPTION_ACTION,
                      "multiline": True,
                      "placeholder": {
                          "type": "plain_text",
                          "text": "A happy dancing banana wearing sunglasses...",
                      },
                  },
                  "label": {"type": "plain_text", "text": "Describe your emoji"},
              },
              # Emoji Name (optional)
              {
                  "type": "input",
                  "block_id": self.EMOJI_NAME_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "plain_text_input",
                      "action_id": self.NAME_ACTION,
                      "placeholder": {
                          "type": "plain_text",
                          "text": "e.g., dancing_banana (auto-generated if empty)",
                      },
                  },
                  "label": {"type": "plain_text", "text": "Emoji Name"},
                  "hint": {
                      "type": "plain_text",
                      "text": "Will become :emoji_name: (lowercase, underscores only)",
                  },
              },
              {"type": "divider"},
              {
                  "type": "context",
                  "elements": [{"type": "mrkdwn", "text": "⚙️ *Advanced Options*"}],
              },
              # Image Provider
              {
                  "type": "input",
                  "block_id": self.IMAGE_PROVIDER_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "static_select",
                      "action_id": self.PROVIDER_ACTION,
                      "initial_option": {
                          "text": {"type": "plain_text", "text": "🍌 Nano Banana Pro"},
                          "value": "google_gemini",
                      },
                      "options": [
                          {
                              "text": {"type": "plain_text", "text": "🍌 Nano Banana Pro"},
                              "value": "google_gemini",
                          },
                          {
                              "text": {"type": "plain_text", "text": "🤖 OpenAI GPT-Image"},
                              "value": "openai",
                          },
                      ],
                  },
                  "label": {"type": "plain_text", "text": "Image Model"},
              },
              # Quality (only applies to OpenAI, Google uses prompt-based styling)
              {
                  "type": "input",
                  "block_id": self.QUALITY_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "static_select",
                      "action_id": self.QUALITY_ACTION,
                      "initial_option": {
                          "text": {"type": "plain_text", "text": "✨ High (best quality)"},
                          "value": "high",
                      },
                      "options": [
                          {
                              "text": {"type": "plain_text", "text": "✨ High (best quality)"},
                              "value": "high",
                          },
                          {
                              "text": {"type": "plain_text", "text": "⚖️ Medium (balanced)"},
                              "value": "medium",
                          },
                          {
                              "text": {"type": "plain_text", "text": "⚡ Low (fastest)"},
                              "value": "low",
                          },
                      ],
                  },
                  "label": {"type": "plain_text", "text": "Quality (OpenAI only)"},
              },
              # Background
              {
                  "type": "input",
                  "block_id": self.BACKGROUND_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "static_select",
                      "action_id": self.BACKGROUND_ACTION,
                      "initial_option": {
                          "text": {"type": "plain_text", "text": "🔲 Transparent"},
                          "value": "transparent",
                      },
                      "options": [
                          {
                              "text": {"type": "plain_text", "text": "🔲 Transparent"},
                              "value": "transparent",
                          },
                          {
                              "text": {"type": "plain_text", "text": "🎨 Auto"},
                              "value": "auto",
                          },
                      ],
                  },
                  "label": {"type": "plain_text", "text": "Background"},
              },
              # Number of Images
              {
                  "type": "input",
                  "block_id": self.NUM_IMAGES_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "static_select",
                      "action_id": self.NUM_IMAGES_ACTION,
                      "initial_option": {
                          "text": {"type": "plain_text", "text": "1 image"},
                          "value": "1",
                      },
                      "options": [
                          {
                              "text": {"type": "plain_text", "text": "1 image"},
                              "value": "1",
                          },
                          {
                              "text": {"type": "plain_text", "text": "2 images (choose best)"},
                              "value": "2",
                          },
                          {
                              "text": {"type": "plain_text", "text": "4 images (choose best)"},
                              "value": "4",
                          },
                      ],
                  },
                  "label": {"type": "plain_text", "text": "Number of Options"},
              },
              # Style Text (free-form)
              {
                  "type": "input",
                  "block_id": self.STYLE_TEXT_BLOCK,
                  "optional": True,
                  "element": {
                      "type": "plain_text_input",
                      "action_id": self.STYLE_TEXT_ACTION,
                      "placeholder": {
                          "type": "plain_text",
                          "text": "cartoon, pixel art, minimalist, 3D, watercolor...",
                      },
                  },
                  "label": {"type": "plain_text", "text": "Style (optional)"},
              },
              # Toggle button
              {
                  "type": "actions",
                  "block_id": self.STYLE_TOGGLE_BLOCK,
                  "elements": [
                      {
                          "type": "button",
                          "action_id": self.STYLE_TOGGLE_ACTION,
                          "text": {
                              "type": "plain_text",
                              "text": "▲ Hide Advanced Options",
                              "emoji": True,
                          },
                          "value": "collapse",
                      }
                  ],
              },
          ]

          return {
              "type": "modal",
              "callback_id": self.MODAL_CALLBACK_ID,
              "title": {"type": "plain_text", "text": "Create Emoji"},
              "submit": {"type": "plain_text", "text": "✨ Generate"},
              "close": {"type": "plain_text", "text": "Cancel"},
              "blocks": blocks,
              "private_metadata": json.dumps(metadata_with_state),
          }
  ```

- [✅] **3.2** Create presentation package `__init__.py`
  - File: **[EXISTS]** `src/emojismith/presentation/__init__.py`
  - **Note:** Empty — modal builder moved to application layer. Import from `emojismith.application.modal_builder`

---

### Phase 4: Infrastructure Updates

- [✅] **4.1** Add multi-image support to OpenAI repository
  - File: **[MODIFY]** `src/emojismith/infrastructure/openai/openai_api.py`
  - Replace `generate_image` method:

  ```python
  async def generate_image(
      self,
      prompt: str,
      num_images: int = 1,
      quality: str = "high",
      background: str = "transparent",
  ) -> list[bytes]:
      """Generate images using gpt-image-1.5 with fallback to gpt-image-1-mini.
      
      Args:
          prompt: Text description of the image to generate
          num_images: Number of images to generate (1-10, we cap at 4 for UX)
          quality: Rendering quality - "auto", "high", "medium", "low"
          background: Background type - "transparent", "opaque", "auto"
      
      Returns:
          List of image bytes (PNG format with alpha channel if transparent)
      """
      # Cap at 4 images for reasonable UX
      n = min(num_images, 4)
      
      try:
          response = await self._client.images.generate(
              model="gpt-image-1.5",
              prompt=prompt,
              n=n,
              size="1024x1024",
              quality=quality,
              background=background,
              response_format="b64_json",
          )
      except openai.RateLimitError as exc:
          raise RateLimitExceededError(str(exc)) from exc
      except Exception as exc:
          self._logger.warning(
              "gpt-image-1.5 failed, falling back to gpt-image-1-mini: %s", exc
          )
          try:
              response = await self._client.images.generate(
                  model="gpt-image-1-mini",
                  prompt=prompt,
                  n=n,
                  size="1024x1024",
                  background=background,
                  response_format="b64_json",
              )
          except openai.RateLimitError as rate_exc:
              raise RateLimitExceededError(str(rate_exc)) from rate_exc

      if not response.data:
          raise ValueError("OpenAI did not return image data")

      images = []
      for item in response.data:
          if item.b64_json:
              images.append(base64.b64decode(item.b64_json))
      return images
  ```

- [✅] **4.2** Add Imagen fallback and multi-image support to Gemini repository
  - File: **[MODIFY]** `src/emojismith/infrastructure/google/gemini_api.py`
  - Add new method `_generate_with_imagen`:

  ```python
  async def _generate_with_imagen(self, prompt: str) -> bytes:
      """Generate image with Imagen 4 Ultra fallback.
      
      Uses the Imagen API which has a different method signature than Gemini.
      """
      response = await self._client.aio.models.generate_images(
          model=self._fallback_model,  # "imagen-4.0-ultra-generate-001"
          prompt=prompt,
          config=types.GenerateImagesConfig(
              number_of_images=1,
              aspect_ratio="1:1",
          ),
      )

      if response.generated_images:
          return bytes(response.generated_images[0].image.image_bytes)

      raise ValueError("Imagen did not return image data")
  ```

  - Update `generate_image` method:

  ```python
  async def generate_image(
      self,
      prompt: str,
      num_images: int = 1,
  ) -> list[bytes]:
      """Generate images using Gemini with Imagen Ultra fallback.
      
      Note: Google APIs don't have a background parameter. Transparent background
      must be specified in the prompt text.
      
      Args:
          prompt: Text description (should include "transparent background" if needed)
          num_images: Number of images to generate (1-4)
      
      Returns:
          List of image bytes
      """
      images = []
      n = min(num_images, 4)

      for _ in range(n):
          try:
              image_bytes = await self._generate_with_model(prompt, self._model)
              images.append(image_bytes)
          except Exception as exc:
              if self._is_rate_limit_error(exc):
                  raise RateLimitExceededError(str(exc)) from exc

              self._logger.warning(
                  "%s failed, falling back to %s: %s",
                  self._model,
                  self._fallback_model,
                  exc,
              )
              try:
                  image_bytes = await self._generate_with_imagen(prompt)
                  images.append(image_bytes)
              except Exception as fallback_exc:
                  if self._is_rate_limit_error(fallback_exc):
                      raise RateLimitExceededError(str(fallback_exc)) from fallback_exc
                  raise fallback_exc

      return images
  ```

---

### Phase 5: Webhook Handler Updates

- [✅] **5.1** Update modal submission handler
  - File: **[MODIFY]** `src/emojismith/application/handlers/slack_webhook_handler.py`
  - Extract new style preferences from form values:

  ```python
  # In _handle_modal_submission method, extract new fields:
  background = (
      state.get(self._modal_builder.BACKGROUND_BLOCK, {})
      .get(self._modal_builder.BACKGROUND_ACTION, {})
      .get("selected_option", {})
      .get("value", "transparent")
  )
  quality = (
      state.get(self._modal_builder.QUALITY_BLOCK, {})
      .get(self._modal_builder.QUALITY_ACTION, {})
      .get("selected_option", {})
      .get("value", "high")
  )
  num_images = (
      state.get(self._modal_builder.NUM_IMAGES_BLOCK, {})
      .get(self._modal_builder.NUM_IMAGES_ACTION, {})
      .get("selected_option", {})
      .get("value", "1")
  )
  style_text = (
      state.get(self._modal_builder.STYLE_TEXT_BLOCK, {})
      .get(self._modal_builder.STYLE_TEXT_ACTION, {})
      .get("value", "")
  )

  style_preferences = EmojiStylePreferences.from_form_values(
      background=background,
      quality=quality,
      num_images=num_images,
      style_text=style_text,
  )
  ```

- [ ] **5.2** Handle multi-image response
  - When `num_images > 1`, post all images the same way a single image is posted
  - Each image should be posted as a separate message/attachment (no selection UI needed)

---

### Phase 6: Prompt Enhancement Updates

- [✅] **6.1** Update prompt enhancer to append Slack optimization suffix for Google
  - File: **[MODIFIED]** `src/emojismith/application/services/emoji_service.py`
  - Implementation uses `EmojiGenerationPreferences.get_background_prompt_suffix()` method:

  ```python
  # When using Google provider, append Slack optimization to prompt
  # The suffix includes: transparent background (if selected), bold shapes, 
  # high contrast, and display size guidance per Slack requirements
  final_prompt = enhanced_prompt + style_preferences.get_background_prompt_suffix()
  
  # Example output with transparent background:
  # "...cartoon rocket ship, transparent background, bold shapes, high contrast, 
  #  optimized for 128x128 Slack emoji display at 20-32px"
  ```

- [✅] **6.2** Add post-processing for 128KB file size limit
  - File: **[NEW]** `src/emojismith/infrastructure/image_processor.py`
  - Compress PNG images to meet Slack's 128KB limit:

  ```python
  from PIL import Image
  import io

  def compress_for_slack(image_bytes: bytes, max_size_kb: int = 128) -> bytes:
      """Compress image to meet Slack's 128KB limit while preserving transparency.
      
      Args:
          image_bytes: Original PNG image bytes
          max_size_kb: Maximum file size in KB (default: 128)
      
      Returns:
          Compressed PNG bytes under the size limit
      """
      img = Image.open(io.BytesIO(image_bytes))
      
      # Resize if needed (start at 512x512, reduce if still too large)
      sizes = [512, 256, 128]
      
      for size in sizes:
          output = io.BytesIO()
          resized = img.resize((size, size), Image.Resampling.LANCZOS)
          resized.save(output, format="PNG", optimize=True)
          
          if output.tell() <= max_size_kb * 1024:
              return output.getvalue()
      
      # Final fallback: use maximum compression
      output = io.BytesIO()
      img.resize((128, 128), Image.Resampling.LANCZOS).save(
          output, format="PNG", optimize=True, compress_level=9
      )
      return output.getvalue()
  ```

---

### Phase 7: Verification

- [✅] **7.1** Run unit tests
  ```bash
  pytest tests/unit/ -v
  ```

- [ ] **7.2** Run integration tests
  ```bash
  pytest tests/integration/ -v
  ```

- [ ] **7.3** Run full QA suite
  ```bash
  just qa
  ```

- [ ] **7.4** Manual testing checklist
  1. Open modal via message action
  2. Verify simple mode shows only description field
  3. Click "Show Advanced Options"
  4. Verify all options are visible with correct defaults
  5. Test with OpenAI provider: verify transparent background works natively
  6. Test with Google provider: verify prompt includes "transparent background"
  7. Generate emoji with 4 images option
  8. Verify all 4 images are posted to Slack (each as separate message, same format as single image)

---

## Files Summary

### Files Created ✅

| File | Purpose | Status |
|------|---------|--------|
| `src/emojismith/application/modal_builder.py` | Modal construction with progressive disclosure | ✅ Done (moved from presentation/) |
| `src/emojismith/infrastructure/image_processor.py` | PNG compression for Slack's 128KB limit | ✅ Done |

### Files Modified ✅

| File | Changes | Status |
|------|---------|--------|
| `src/emojismith/infrastructure/openai/openai_api.py` | Upgrade to gpt-image-1.5, add multi-image, verified params | ✅ Done |
| `src/emojismith/infrastructure/google/gemini_api.py` | Add imagen-ultra fallback, add multi-image | ✅ Done |
| `src/shared/domain/value_objects.py` | Add BackgroundType, QualityLevel, NumberOfImages enums, EmojiGenerationPreferences | ✅ Done |
| `src/emojismith/application/handlers/slack_webhook_handler.py` | Use modal builder, handle new preferences | ✅ Done |
| `src/emojismith/application/services/emoji_service.py` | Apply background prompt suffix for Google | ✅ Done |

---

## References

- [OpenAI Image Generation API](https://platform.openai.com/docs/api-reference/images) - Verified Dec 2025
- [Google Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation) - Verified Dec 2025
- [Google Imagen API](https://ai.google.dev/gemini-api/docs/imagen) - Verified Dec 2025
- [Slack Custom Emoji Help](https://slack.com/help/articles/206870177) - Verified Dec 2025
- [Slack Modals Overview](https://api.slack.com/surfaces/modals)

