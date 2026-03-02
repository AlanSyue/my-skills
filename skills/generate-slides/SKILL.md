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
  - `GOOGLE_SERVICE_ACCOUNT_KEY_FILE` — path to a Google Service Account JSON key file
  - `GOOGLE_SLIDES_SHARE_EMAIL` — email address to share the presentation with
- Python packages: `google-api-python-client`, `google-auth`

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

1. **Check Python dependencies**:
   - Run: `python3 -c "from googleapiclient.discovery import build; from google.oauth2 import service_account; print('OK')"`
   - If this fails, instruct the user to install: `pip3 install google-api-python-client google-auth`

2. **Create the presentation**:
   - Pipe the confirmed markdown content to the script via stdin:
     ```bash
     echo "$MARKDOWN_CONTENT" | python3 "$HOME/my-skills/scripts/create_google_slides.py"
     ```

3. **Handle the result**:
   - The script outputs JSON to stdout: `{"url": "...", "title": "...", "slide_count": N}`
   - If the script exits with a non-zero code, display the stderr output and help the user troubleshoot.
   - Common errors:
     - Missing `GOOGLE_SERVICE_ACCOUNT_KEY_FILE`: tell user to set it in `.env`
     - Missing `GOOGLE_SLIDES_SHARE_EMAIL`: tell user to set it in `.env`
     - Invalid credentials: tell user to check their service account key file
     - Missing Python packages: tell user to run `pip3 install google-api-python-client google-auth`

4. **Output the result**:
   - Display the presentation URL to the user.
   - Mention the number of slides created.
