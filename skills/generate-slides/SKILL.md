---
name: generate-slides
description: Generate a slide deck from a topic or context, then convert it into a Google Slides presentation after user confirmation.
---

# Markdown to Google Slides

Generate a slide deck in markdown from the user's topic or context, then convert it into a Google Slides presentation using the Google Slides API.

## Input

- `$ARGUMENTS`: the topic, context, or description for the presentation

## Requirements

- Environment variables in `$HOME/my-skills/.env`:
  - `GOOGLE_CREDENTIALS_FILE` — path to a Google OAuth2 Desktop or Service Account JSON key file
  - `GOOGLE_SLIDES_SHARE_EMAIL` — email address to share the presentation with (optional, for new presentations)
- Python virtual env: `$HOME/my-skills/.venv/bin/python3`
- Python packages (pre-installed in venv): `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- Optional CLI tools for advanced visuals:
  - `d2` — D2 diagram CLI for generating flowcharts and sequence diagrams
  - `freeze` — Code screenshot tool for syntax-highlighted code images

## Phase 1 — Generate Markdown

1. Read `$ARGUMENTS` as the topic or context for the presentation.
2. Generate a markdown slide deck following this format for each slide:

   ```markdown
   ## Slide Title

   Description content here (bullet points or paragraphs)

   > Speaker notes content here
   > Can span multiple lines

   ---
   ```

   - Use `##` headings for slide titles.
   - Use bullet points (`-`) or paragraphs for the slide body.
   - Use blockquotes (`> `) for speaker notes.
   - Separate slides with `---` on its own line.
   - The first slide should use `#` as the presentation title.

3. Output the full markdown to the user and ask them to review and confirm before proceeding to Phase 2.

## Phase 2 — Create Google Slides

Only proceed after the user confirms the markdown is ready.

### Option A: Simple creation (from Markdown)

1. Pipe the confirmed markdown content to the script via stdin:
   ```bash
   echo "$MARKDOWN_CONTENT" | $HOME/my-skills/.venv/bin/python3 "$HOME/my-skills/scripts/create_google_slides.py"
   ```

2. To **update** an existing presentation instead of creating a new one:
   ```bash
   echo "$MARKDOWN_CONTENT" | $HOME/my-skills/.venv/bin/python3 "$HOME/my-skills/scripts/create_google_slides.py" --update PRESENTATION_ID
   ```

3. The script outputs JSON to stdout: `{"url": "...", "title": "...", "slide_count": N}`

### Option B: Advanced creation (with rich visuals)

For presentations requiring tables, diagrams, code images, or custom layouts, write a Python script that uses the helpers module:

```python
import sys
sys.path.insert(0, '$HOME/my-skills/scripts')
from google_slides_helpers import *

slides_service, drive_service = build_services()
PRES_ID = 'your_presentation_id'
```

Then use the helper functions described in the **Advanced Capabilities** section below.

## Advanced Capabilities

The helper module `$HOME/my-skills/scripts/google_slides_helpers.py` provides reusable functions for all Google Slides API operations.

### Authentication

```python
from google_slides_helpers import build_services

slides_service, drive_service = build_services()
# Handles Service Account and OAuth2 Desktop credentials automatically
```

### Slide Management

```python
from google_slides_helpers import (
    delete_objects_requests, create_blank_slide_request,
    get_presentation, execute_batch, uid
)

prefix = uid()  # e.g. 'a1b2c3d4'

# Delete old slides
reqs = delete_objects_requests(['slide_id_1', 'slide_id_2'])
execute_batch(slides_service, PRES_ID, reqs, 'Delete old slides')

# Create new blank slides
reqs = [
    create_blank_slide_request(f'new_{prefix}_0', insertion_index=5),
    create_blank_slide_request(f'new_{prefix}_1', insertion_index=6),
]
execute_batch(slides_service, PRES_ID, reqs, 'Create new slides')
```

### Title Text Box

Standard 24pt bold centered title at the top of a slide:

```python
from google_slides_helpers import create_title_requests

reqs = create_title_requests('slide_id', 'My Title', uid_prefix='s1')
# Returns: [createShape, insertText, updateTextStyle, updateParagraphStyle]
```

### Styled Cards

Cards with colored background, border, bold title, and description:

```python
from google_slides_helpers import create_card_requests

reqs = create_card_requests(
    slide_id='slide_id',
    card_id='card_1',
    title='Card Title',
    description='Line 1\nLine 2\nLine 3',
    x=500000, y=700000, width=2600000, height=1700000,
    bg_hex='#EBF5FB',         # light background
    border_hex='#2471A3',     # colored border
    title_color_hex='#2471A3' # title text color
)
```

### Accent Bars

Decorative colored bars (top/bottom of slide, or left-side card accents):

```python
from google_slides_helpers import create_accent_bar_requests

# Top bar
reqs = create_accent_bar_requests('slide_id', 'bar_top',
    x=0, y=0, width=9144000, height=200000, color_hex='#2471A3')

# Left-side card accent
reqs = create_accent_bar_requests('slide_id', 'accent_1',
    x=900000, y=750000, width=60000, height=440000, color_hex='#E74C3C')
```

### Bullet Lists

```python
from google_slides_helpers import create_bullet_textbox_requests

reqs = create_bullet_textbox_requests(
    'slide_id', 'bullets_1',
    lines=['First point', 'Second point', 'Third point'],
    x=500000, y=800000, width=4000000, height=2000000
)
```

### Tables

Tables with blue header, alternating row colors, and safe empty-cell handling:

```python
from google_slides_helpers import create_styled_table_on_slide

data = [
    ['Header 1', 'Header 2', 'Header 3'],      # row 0 = header
    ['Cell 1-1', 'Cell 1-2', 'Cell 1-3'],
    ['Cell 2-1', 'Cell 2-2', 'Cell 2-3'],
]

# High-level: creates, populates, and styles in one call
create_styled_table_on_slide(
    slides_service, drive_service, PRES_ID,
    slide_id='slide_id', table_id='table_1',
    data=data,
    x=311700, y=800000, width=8520600, height=2400000
)
```

For more control, use the lower-level functions:
```python
from google_slides_helpers import (
    create_table_request, populate_table_requests,
    style_table_requests, cell_has_text
)
```

**IMPORTANT**: Always use `cell_has_text()` before applying `updateTextStyle` to table cells. Styling empty cells causes API errors.

### Images (D2 Diagrams, Freeze Code Screenshots)

#### Generate D2 diagrams
```bash
# White background, suitable for slides
d2 --theme 0 input.d2 output.png
```

D2 diagram tips:
- Always use `--theme 0` (white background) — dark themes look bad on slides
- Use explicit `style.font-color: "#333333"` on nodes for readability
- Use saturated fill colors visible on white: `style.fill: "#CCE5FF"`

#### Generate code screenshots with freeze
```bash
echo 'code here' | freeze -l go --theme dracula --window=false \
    --padding 20,30,20,30 --font.size 14 -o output.png
```

Freeze tips:
- **NEVER use Chinese/CJK characters** in code — they render as boxes (garbled)
- Replace Chinese comments with English equivalents before generating
- Use `--theme dracula` for consistent dark code blocks

#### Upload and insert images
```python
from google_slides_helpers import upload_image_to_drive, create_image_request

# Upload to Google Drive (sets public read permission)
url = upload_image_to_drive(drive_service, '/path/to/image.png', 'display_name.png')

# Insert into slide
req = create_image_request('slide_id', 'img_1', url,
    x=571500, y=800000, width=8001000, height=4000000)
```

### Speaker Notes

```python
from google_slides_helpers import get_notes_placeholder_id, create_speaker_notes_request

pres = get_presentation(slides_service, PRES_ID)
notes_id = get_notes_placeholder_id(pres, 'slide_id')
reqs = create_speaker_notes_request(notes_id, 'Speaker notes text here')
```

### Targeted Slide Update

Update individual slides without affecting the rest of the presentation:

```python
from google_slides_helpers import (
    get_presentation, get_slide_by_index, get_slide_index_by_id,
    clear_slide_requests, replace_slide,
    update_slide_title, update_slide_notes,
    execute_batch
)

pres = get_presentation(slides_service, PRES_ID)

# Inspect a slide by page number (0-based)
info = get_slide_by_index(pres, 5)  # page 6
print(info['objectId'], info['elements'])

# Find slide index by objectId
idx = get_slide_index_by_id(pres, 'slide_5')

# Clear all elements on a slide (optionally keep images)
reqs = clear_slide_requests(pres, 'slide_5', keep_types={'IMAGE'})
execute_batch(slides_service, PRES_ID, reqs, 'Clear slide')

# Replace a slide with a new blank one at the same position
new_id = replace_slide(slides_service, PRES_ID, 'slide_5', slide_index=5)

# Update only the title text
update_slide_title(slides_service, PRES_ID, pres, 'slide_5', 'New Title')

# Update only the speaker notes
update_slide_notes(slides_service, PRES_ID, pres, 'slide_5', 'New speaker notes here')
```

### Text Formatting

```python
from google_slides_helpers import parse_inline_formatting

segments = parse_inline_formatting('This is **bold** and *italic*')
# [{'text': 'This is ', 'bold': False, 'italic': False},
#  {'text': 'bold', 'bold': True, 'italic': False},
#  {'text': ' and ', 'bold': False, 'italic': False},
#  {'text': 'italic', 'bold': False, 'italic': True}]
```

## Design Conventions

When creating visually rich slides, follow these conventions:

### Colors
| Usage | Hex | Description |
|-------|-----|-------------|
| Primary accent | `#2471A3` | Blue — links, headers, accent bars |
| Success | `#27AE60` | Green — completed, positive |
| Error/Failure | `#E74C3C` | Red — failed, negative |
| Warning | `#E67E22` | Orange — compensation, caution |
| Pending | `#F39C12` | Yellow/Orange — in-progress |
| Purple | `#8E44AD` | Purple — state machines, special |
| Teal | `#1ABC9C` | Teal — techniques, tips |
| Table header | `#4A86C8` | Blue — table header background |

### Dimensions (EMU)
| Element | Value |
|---------|-------|
| Slide width | 9,144,000 |
| Slide height | 5,143,500 |
| Title position | (311700, 152400) |
| Content start Y | 800,000 |
| 1 PT in EMU | 12,700 |

### Slide Patterns

1. **Title slide**: Accent bars top/bottom + centered title (36pt) + subtitle (18pt)
2. **Section overview**: Title + 2x3 or 3+2 colored cards grid
3. **Content with table**: Title + styled table (blue header, alternating rows)
4. **Content with diagram**: Title + D2 diagram image (centered or left) + annotation bullets (right)
5. **Content with code**: Title + freeze code image (left) + annotation bullets (right)
6. **Agenda**: Title + numbered card strips with colored left accents
7. **Summary**: Title + takeaway cards in grid layout
8. **Q&A**: Accent bars + large centered "Q & A" text

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|---------|
| `GOOGLE_CREDENTIALS_FILE not set` | Missing env var | Set in `$HOME/my-skills/.env` |
| `The object has no text` (400) | `updateTextStyle` on empty table cell | Use `cell_has_text()` check |
| CJK characters as boxes | freeze doesn't support CJK fonts | Use English-only text in freeze |
| Dark diagram background | D2 theme 200 | Use `--theme 0` for white bg |
| OAuth token expired | Cached token stale | Delete `$HOME/my-skills/.cache/google_slides_token.pickle` |

## Output

- Display the presentation URL to the user
- Mention the number of slides created/updated
