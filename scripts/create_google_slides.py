#!/usr/bin/env python3
"""Convert Marp-style markdown into a Google Slides presentation."""
import json
import os
import pickle
import re
import sys


def load_env():
    """Parse $HOME/my-skills/.env manually and set values into os.environ."""
    env_path = os.path.join(os.path.expanduser('~'), 'my-skills', '.env')
    if not os.path.isfile(env_path):
        return
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Strip surrounding quotes if present
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                os.environ.setdefault(key, value)


def parse_markdown(md_text):
    """Split markdown by '\\n---\\n' into slides.

    Each slide is a dict with 'title' (first heading), 'body' (remaining lines),
    and 'notes' (blockquote lines starting with '> ', used as speaker notes).
    """
    raw_slides = md_text.split('\n---\n')
    slides = []
    for raw in raw_slides:
        raw = raw.strip()
        if not raw:
            continue
        lines = raw.split('\n')
        title = ''
        body_lines = []
        notes_lines = []
        title_found = False
        in_notes = False
        for line in lines:
            if not title_found and line.startswith('#'):
                title = line.lstrip('#').strip()
                title_found = True
            elif line.startswith('> '):
                in_notes = True
                # Strip the '> ' prefix and any bold markers from the label line
                note_text = line[2:]
                # Skip the "Speaker Notes:" / "**Speaker Notes:**" label line itself
                stripped = note_text.strip().replace('**', '')
                if stripped.lower() in ('speaker notes:', 'speaker notes'):
                    continue
                notes_lines.append(note_text)
            elif in_notes and line.startswith('>'):
                # Handle '>' lines with no text (empty blockquote continuation)
                note_text = line[1:].strip()
                if note_text:
                    notes_lines.append(note_text)
            else:
                if in_notes:
                    in_notes = False
                body_lines.append(line)
        body = '\n'.join(body_lines).strip()
        notes = '\n'.join(notes_lines).strip()
        slides.append({'title': title, 'body': body, 'notes': notes})
    return slides


def parse_inline_formatting(text):
    """Parse bold and italic markers in text.

    Returns a list of segments: [{"text": str, "bold": bool, "italic": bool}].
    Handles ***bold italic***, **bold**, and *italic*.
    """
    segments = []
    # Pattern order: bold+italic (***), bold (**), italic (*) — longest match first
    pattern = re.compile(r'\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*', re.DOTALL)
    last_end = 0
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        if start > last_end:
            segments.append({'text': text[last_end:start], 'bold': False, 'italic': False})
        if m.group(1) is not None:
            # ***bold italic***
            segments.append({'text': m.group(1), 'bold': True, 'italic': True})
        elif m.group(2) is not None:
            # **bold**
            segments.append({'text': m.group(2), 'bold': True, 'italic': False})
        elif m.group(3) is not None:
            # *italic*
            segments.append({'text': m.group(3), 'bold': False, 'italic': True})
        last_end = end
    if last_end < len(text):
        segments.append({'text': text[last_end:], 'bold': False, 'italic': False})
    return segments


TOKEN_PATH = os.path.join(os.path.expanduser('~'), 'my-skills', '.cache', 'google_slides_token.pickle')


def get_oauth2_credentials(key_file, scopes):
    """Load or obtain OAuth2 Desktop credentials, caching them to TOKEN_PATH."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print('Error: google-auth-oauthlib is required for OAuth2 Desktop credentials. '
              'Run: pip3 install google-auth-oauthlib', file=sys.stderr)
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(key_file, scopes)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def main():
    load_env()

    # Read markdown from stdin or file argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r') as f:
            md_text = f.read()
    elif not sys.stdin.isatty():
        md_text = sys.stdin.read()
    else:
        print('Usage: create_google_slides.py [file.md]  or  echo "..." | create_google_slides.py', file=sys.stderr)
        sys.exit(1)

    slides = parse_markdown(md_text)
    if not slides:
        print('Error: no slides found in markdown input.', file=sys.stderr)
        sys.exit(1)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print('Error: missing Python packages. Run: pip3 install google-api-python-client google-auth', file=sys.stderr)
        sys.exit(1)

    try:
        key_file = os.environ.get('GOOGLE_CREDENTIALS_FILE') or os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_FILE')
        if not key_file:
            print('Error: GOOGLE_CREDENTIALS_FILE is not set in .env', file=sys.stderr)
            sys.exit(1)

        SCOPES = [
            'https://www.googleapis.com/auth/presentations',
            'https://www.googleapis.com/auth/drive'
        ]

        with open(key_file, 'r') as f:
            key_data = json.load(f)

        if key_data.get('type') == 'service_account':
            creds = service_account.Credentials.from_service_account_file(
                key_file, scopes=SCOPES
            )
        elif 'installed' in key_data:
            creds = get_oauth2_credentials(key_file, SCOPES)
        else:
            print('Error: unrecognized credential file format', file=sys.stderr)
            sys.exit(1)
        slides_service = build('slides', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # Create new presentation
        presentation = slides_service.presentations().create(
            body={'title': slides[0]['title']}
        ).execute()
        presentation_id = presentation['presentationId']

        # Remember default slide ID to delete later
        default_slide_id = presentation['slides'][0]['objectId']

        # Batch Update #1: create all slides and delete the default blank slide
        requests = []
        for i, slide in enumerate(slides):
            layout = 'TITLE_AND_BODY' if slide['body'].strip() else 'TITLE'
            requests.append({
                'createSlide': {
                    'insertionIndex': i,
                    'slideLayoutReference': {'predefinedLayout': layout},
                    'objectId': f'slide_{i}'
                }
            })
        requests.append({
            'deleteObject': {'objectId': default_slide_id}
        })
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        # Refresh presentation to get placeholder IDs
        presentation = slides_service.presentations().get(
            presentationId=presentation_id
        ).execute()

        # Batch Update #2: insert text and apply formatting
        requests = []
        for i, slide_data in enumerate(slides):
            page = presentation['slides'][i]
            title_placeholder = None
            body_placeholder = None
            for element in page.get('pageElements', []):
                shape = element.get('shape', {})
                ph = shape.get('placeholder', {})
                ph_type = ph.get('type', '')
                if ph_type in ('TITLE', 'CENTERED_TITLE'):
                    title_placeholder = element['objectId']
                elif ph_type in ('BODY', 'SUBTITLE'):
                    body_placeholder = element['objectId']

            # Insert title text
            if title_placeholder and slide_data['title']:
                requests.append({
                    'insertText': {
                        'objectId': title_placeholder,
                        'text': slide_data['title'],
                        'insertionIndex': 0
                    }
                })

            # Insert body with formatting
            if body_placeholder and slide_data['body'].strip():
                lines = slide_data['body'].strip().split('\n')
                full_text = ''
                line_positions = []
                for line in lines:
                    is_bullet = line.startswith('- ') or line.startswith('* ')
                    clean_line = line[2:] if is_bullet else line
                    start = len(full_text)
                    full_text += clean_line + '\n'
                    end = len(full_text)
                    line_positions.append({
                        'start': start,
                        'end': end,
                        'text': clean_line,
                        'is_bullet': is_bullet
                    })

                # Insert all text at once
                requests.append({
                    'insertText': {
                        'objectId': body_placeholder,
                        'text': full_text,
                        'insertionIndex': 0
                    }
                })

                # Apply bullet formatting
                for lp in line_positions:
                    if lp['is_bullet']:
                        requests.append({
                            'createParagraphBullets': {
                                'objectId': body_placeholder,
                                'textRange': {
                                    'type': 'FIXED_RANGE',
                                    'startIndex': lp['start'],
                                    'endIndex': lp['end'] - 1
                                },
                                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                            }
                        })

                # Apply inline formatting (bold/italic)
                for lp in line_positions:
                    segments = parse_inline_formatting(lp['text'])
                    offset = lp['start']
                    for seg in segments:
                        seg_start = offset
                        seg_end = offset + len(seg['text'])
                        if seg['bold'] or seg['italic']:
                            style = {}
                            fields = []
                            if seg['bold']:
                                style['bold'] = True
                                fields.append('bold')
                            if seg['italic']:
                                style['italic'] = True
                                fields.append('italic')
                            requests.append({
                                'updateTextStyle': {
                                    'objectId': body_placeholder,
                                    'textRange': {
                                        'type': 'FIXED_RANGE',
                                        'startIndex': seg_start,
                                        'endIndex': seg_end
                                    },
                                    'style': style,
                                    'fields': ','.join(fields)
                                }
                            })
                        offset = seg_end

            # Insert speaker notes
            if slide_data.get('notes', '').strip():
                notes_page = page.get('slideProperties', {}).get('notesPage', {})
                notes_placeholder = None
                for element in notes_page.get('pageElements', []):
                    shape = element.get('shape', {})
                    ph = shape.get('placeholder', {})
                    if ph.get('type') == 'BODY':
                        notes_placeholder = element['objectId']
                        break
                if notes_placeholder:
                    requests.append({
                        'insertText': {
                            'objectId': notes_placeholder,
                            'text': slide_data['notes'],
                            'insertionIndex': 0
                        }
                    })

        if requests:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

        # Share presentation via Drive API
        share_email = os.environ.get('GOOGLE_SLIDES_SHARE_EMAIL')
        if share_email:
            drive_service.permissions().create(
                fileId=presentation_id,
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': share_email
                },
                sendNotificationEmail=False
            ).execute()

        # Output result as JSON
        result = {
            'url': f'https://docs.google.com/presentation/d/{presentation_id}/edit',
            'title': slides[0]['title'],
            'slide_count': len(slides)
        }
        print(json.dumps(result))

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
