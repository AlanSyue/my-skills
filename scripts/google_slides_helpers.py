#!/usr/bin/env python3
"""Reusable helper functions for Google Slides API operations.

Provides utilities for authentication, slide management, shape creation,
table operations, image handling, text formatting, and speaker notes.

Usage:
    from google_slides_helpers import build_services, hex_to_rgb, ...
"""

import json
import os
import pickle
import re
import sys
import uuid

# --- Auth & Setup ---

TOKEN_PATH = os.path.join(os.path.expanduser('~'), 'my-skills', '.cache', 'google_slides_token.pickle')
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive'
]


def load_env():
    """Parse $HOME/my-skills/.env and set values into os.environ."""
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
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                os.environ.setdefault(key, value)


def get_oauth2_credentials(key_file, scopes):
    """Load or obtain OAuth2 Desktop credentials, caching to TOKEN_PATH."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

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


def build_services():
    """Build and return (slides_service, drive_service) using env credentials.

    Supports both Service Account and OAuth2 Desktop credentials.
    Returns:
        tuple: (slides_service, drive_service)
    """
    from googleapiclient.discovery import build

    load_env()
    key_file = os.environ.get('GOOGLE_CREDENTIALS_FILE') or os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_FILE')
    if not key_file:
        print('Error: GOOGLE_CREDENTIALS_FILE is not set in .env', file=sys.stderr)
        sys.exit(1)

    with open(key_file, 'r') as f:
        key_data = json.load(f)

    if key_data.get('type') == 'service_account':
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
    elif 'installed' in key_data:
        creds = get_oauth2_credentials(key_file, SCOPES)
    else:
        print('Error: unrecognized credential file format', file=sys.stderr)
        sys.exit(1)

    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return slides_service, drive_service


# --- Conversion Helpers ---

# Standard slide dimensions (16:9)
SLIDE_WIDTH = 9144000   # EMU
SLIDE_HEIGHT = 5143500  # EMU

# Common positions (EMU)
TITLE_X = 311700
TITLE_Y = 152400
CONTENT_Y = 800000


def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' to Google Slides RGB dict (0.0-1.0 floats)."""
    hex_color = hex_color.lstrip('#')
    return {
        'red': int(hex_color[0:2], 16) / 255.0,
        'green': int(hex_color[2:4], 16) / 255.0,
        'blue': int(hex_color[4:6], 16) / 255.0
    }


def emu(pt):
    """Convert points to EMU (1 pt = 12700 EMU)."""
    return int(pt * 12700)


def uid():
    """Generate a short unique ID prefix for element IDs."""
    return uuid.uuid4().hex[:8]


# --- Presentation Info ---

def get_presentation(slides_service, presentation_id):
    """Fetch and return the full presentation object."""
    return slides_service.presentations().get(
        presentationId=presentation_id
    ).execute()


def get_notes_placeholder_id(presentation, slide_id):
    """Find the speaker notes BODY placeholder ID for a given slide."""
    for slide in presentation.get('slides', []):
        if slide['objectId'] == slide_id:
            notes_page = slide.get('slideProperties', {}).get('notesPage', {})
            for element in notes_page.get('pageElements', []):
                shape = element.get('shape', {})
                ph = shape.get('placeholder', {})
                if ph.get('type') == 'BODY':
                    return element['objectId']
    return None


def get_slide_text_elements(presentation, slide_index):
    """Extract all text content from a slide's elements.

    Returns list of dicts: [{'objectId': str, 'type': str, 'text': str}, ...]
    """
    slide = presentation['slides'][slide_index]
    results = []
    for element in slide.get('pageElements', []):
        obj_id = element['objectId']
        shape = element.get('shape', {})
        el_type = shape.get('shapeType', element.get('image', {}) and 'IMAGE' or 'UNKNOWN')

        text_content = ''
        for te in shape.get('text', {}).get('textElements', []):
            if 'textRun' in te:
                text_content += te['textRun'].get('content', '')

        results.append({
            'objectId': obj_id,
            'type': el_type,
            'text': text_content.strip(),
            'placeholder_type': shape.get('placeholder', {}).get('type', '')
        })
    return results


def cell_has_text(table, row_idx, col_idx):
    """Check if a table cell contains non-empty text.

    IMPORTANT: Always check this before applying updateTextStyle to table cells,
    as styling empty cells causes API errors.
    """
    try:
        text_elements = (
            table['tableRows'][row_idx]['tableCells'][col_idx]
            .get('text', {})
            .get('textElements', [])
        )
        for te in text_elements:
            if 'textRun' in te and te['textRun'].get('content', '').strip():
                return True
    except (IndexError, KeyError):
        pass
    return False


# --- Slide Management ---

def delete_objects_requests(object_ids):
    """Create batch requests to delete multiple objects (slides or elements).

    Args:
        object_ids: list of objectId strings to delete
    Returns:
        list of deleteObject request dicts
    """
    return [{'deleteObject': {'objectId': oid}} for oid in object_ids]


def create_blank_slide_request(slide_id, insertion_index):
    """Create a request to insert a BLANK slide at the given index.

    Args:
        slide_id: unique objectId for the new slide
        insertion_index: position to insert (0-based)
    Returns:
        createSlide request dict
    """
    return {
        'createSlide': {
            'objectId': slide_id,
            'insertionIndex': insertion_index,
            'slideLayoutReference': {'predefinedLayout': 'BLANK'}
        }
    }


# --- Shape Creation ---

def _make_size(width, height):
    return {
        'width': {'magnitude': width, 'unit': 'EMU'},
        'height': {'magnitude': height, 'unit': 'EMU'}
    }


def _make_transform(x, y):
    return {
        'scaleX': 1, 'scaleY': 1,
        'translateX': x, 'translateY': y,
        'unit': 'EMU'
    }


def _make_color(hex_color):
    """Create opaqueColor dict from hex string."""
    return {'opaqueColor': {'rgbColor': hex_to_rgb(hex_color)}}


def create_shape_request(slide_id, shape_id, shape_type, x, y, width, height):
    """Create a generic shape (TEXT_BOX, RECTANGLE, etc.).

    Args:
        slide_id: page objectId
        shape_id: unique objectId for the shape
        shape_type: 'TEXT_BOX', 'RECTANGLE', etc.
        x, y: position in EMU
        width, height: size in EMU
    """
    return {
        'createShape': {
            'objectId': shape_id,
            'shapeType': shape_type,
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': _make_size(width, height),
                'transform': _make_transform(x, y)
            }
        }
    }


def create_title_requests(slide_id, title_text, uid_prefix,
                          font_size=24, color='#333333',
                          x=311700, y=152400, width=8520600, height=514350):
    """Create a title text box with standard styling.

    Returns a list of requests: [createShape, insertText, updateTextStyle, updateParagraphStyle]
    """
    tb_id = f'{uid_prefix}_title'
    return [
        create_shape_request(slide_id, tb_id, 'TEXT_BOX', x, y, width, height),
        {'insertText': {'objectId': tb_id, 'text': title_text, 'insertionIndex': 0}},
        {
            'updateTextStyle': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'style': {
                    'bold': True,
                    'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                    'fontFamily': 'Arial',
                    'foregroundColor': _make_color(color)
                },
                'fields': 'bold,fontSize,fontFamily,foregroundColor'
            }
        },
        {
            'updateParagraphStyle': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'style': {'alignment': 'CENTER'},
                'fields': 'alignment'
            }
        }
    ]


def create_textbox_requests(slide_id, tb_id, text, x, y, width, height,
                            font_size=14, bold=False, color='#333333',
                            alignment='START', font_family='Arial'):
    """Create a text box with text and styling.

    Returns list of requests.
    """
    reqs = [
        create_shape_request(slide_id, tb_id, 'TEXT_BOX', x, y, width, height),
        {'insertText': {'objectId': tb_id, 'text': text, 'insertionIndex': 0}},
        {
            'updateTextStyle': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'style': {
                    'bold': bold,
                    'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                    'fontFamily': font_family,
                    'foregroundColor': _make_color(color)
                },
                'fields': 'bold,fontSize,fontFamily,foregroundColor'
            }
        },
        {
            'updateParagraphStyle': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'style': {'alignment': alignment},
                'fields': 'alignment'
            }
        }
    ]
    return reqs


def create_accent_bar_requests(slide_id, bar_id, x, y, width, height, color_hex):
    """Create a colored accent bar (rectangle with solid fill, no outline).

    Commonly used for decorative top/bottom bars or left-side card accents.
    """
    return [
        create_shape_request(slide_id, bar_id, 'RECTANGLE', x, y, width, height),
        {
            'updateShapeProperties': {
                'objectId': bar_id,
                'shapeProperties': {
                    'shapeBackgroundFill': {
                        'solidFill': {'color': {'rgbColor': hex_to_rgb(color_hex)}}
                    },
                    'outline': {'propertyState': 'NOT_RENDERED'}
                },
                'fields': 'shapeBackgroundFill,outline'
            }
        }
    ]


def create_card_requests(slide_id, card_id, title, description,
                         x, y, width, height,
                         bg_hex, border_hex, title_color_hex,
                         title_size=18, desc_size=13, desc_color='#555555'):
    """Create a styled card with title + description, background fill, and colored border.

    Args:
        slide_id: page objectId
        card_id: unique objectId for the card
        title: bold title text (first line)
        description: description text (second line onward)
        x, y, width, height: position and size in EMU
        bg_hex: background color hex
        border_hex: border/outline color hex
        title_color_hex: title text color hex
        title_size: title font size in PT
        desc_size: description font size in PT
        desc_color: description text color hex

    Returns list of API requests.
    """
    full_text = f'{title}\n{description}' if description else title
    title_end = len(title)

    reqs = [
        create_shape_request(slide_id, card_id, 'TEXT_BOX', x, y, width, height),
        {
            'updateShapeProperties': {
                'objectId': card_id,
                'shapeProperties': {
                    'shapeBackgroundFill': {
                        'solidFill': {'color': {'rgbColor': hex_to_rgb(bg_hex)}}
                    },
                    'outline': {
                        'outlineFill': {
                            'solidFill': {'color': {'rgbColor': hex_to_rgb(border_hex)}}
                        },
                        'weight': {'magnitude': 1.5, 'unit': 'PT'}
                    }
                },
                'fields': 'shapeBackgroundFill,outline'
            }
        },
        {'insertText': {'objectId': card_id, 'text': full_text, 'insertionIndex': 0}},
        # Style title portion
        {
            'updateTextStyle': {
                'objectId': card_id,
                'textRange': {'type': 'FIXED_RANGE', 'startIndex': 0, 'endIndex': title_end},
                'style': {
                    'bold': True,
                    'fontSize': {'magnitude': title_size, 'unit': 'PT'},
                    'fontFamily': 'Arial',
                    'foregroundColor': _make_color(title_color_hex)
                },
                'fields': 'bold,fontSize,fontFamily,foregroundColor'
            }
        },
    ]

    # Style description portion if present
    if description:
        desc_start = title_end + 1  # after the newline
        desc_end = len(full_text)
        reqs.append({
            'updateTextStyle': {
                'objectId': card_id,
                'textRange': {'type': 'FIXED_RANGE', 'startIndex': desc_start, 'endIndex': desc_end},
                'style': {
                    'fontSize': {'magnitude': desc_size, 'unit': 'PT'},
                    'fontFamily': 'Arial',
                    'foregroundColor': _make_color(desc_color)
                },
                'fields': 'fontSize,fontFamily,foregroundColor'
            }
        })

    # Center all text
    reqs.append({
        'updateParagraphStyle': {
            'objectId': card_id,
            'textRange': {'type': 'ALL'},
            'style': {'alignment': 'CENTER'},
            'fields': 'alignment'
        }
    })

    return reqs


def create_bullet_textbox_requests(slide_id, tb_id, lines, x, y, width, height,
                                   font_size=13, color='#333333'):
    """Create a text box with bullet-pointed lines.

    Args:
        lines: list of strings, each becomes a bullet point
    """
    text = '\n'.join(lines)
    reqs = [
        create_shape_request(slide_id, tb_id, 'TEXT_BOX', x, y, width, height),
        {'insertText': {'objectId': tb_id, 'text': text, 'insertionIndex': 0}},
        {
            'updateTextStyle': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'style': {
                    'fontSize': {'magnitude': font_size, 'unit': 'PT'},
                    'fontFamily': 'Arial',
                    'foregroundColor': _make_color(color)
                },
                'fields': 'fontSize,fontFamily,foregroundColor'
            }
        },
        {
            'createParagraphBullets': {
                'objectId': tb_id,
                'textRange': {'type': 'ALL'},
                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
            }
        }
    ]
    return reqs


# --- Table Operations ---

# Default table style constants
TABLE_HEADER_COLOR = '#4A86C8'
TABLE_HEADER_TEXT_COLOR = '#FFFFFF'
TABLE_ODD_ROW_COLOR = '#F3F3F3'
TABLE_EVEN_ROW_COLOR = '#FFFFFF'
TABLE_TEXT_COLOR = '#333333'


def create_table_request(slide_id, table_id, rows, cols, x, y, width, height):
    """Create a table at the specified position.

    Args:
        rows: total number of rows (including header)
        cols: number of columns
    """
    return {
        'createTable': {
            'objectId': table_id,
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': _make_size(width, height),
                'transform': _make_transform(x, y)
            },
            'rows': rows,
            'columns': cols
        }
    }


def populate_table_requests(table_id, data):
    """Insert text into all table cells.

    Args:
        data: 2D list of strings, data[row][col]
    Returns:
        list of insertText requests
    """
    reqs = []
    for r, row in enumerate(data):
        for c, cell_text in enumerate(row):
            if cell_text:  # skip empty cells
                reqs.append({
                    'insertText': {
                        'objectId': table_id,
                        'cellLocation': {'rowIndex': r, 'columnIndex': c},
                        'text': str(cell_text),
                        'insertionIndex': 0
                    }
                })
    return reqs


def style_table_requests(table_id, num_rows, num_cols,
                         header_bg=TABLE_HEADER_COLOR,
                         header_text_color=TABLE_HEADER_TEXT_COLOR,
                         odd_row_bg=TABLE_ODD_ROW_COLOR,
                         even_row_bg=TABLE_EVEN_ROW_COLOR,
                         text_color=TABLE_TEXT_COLOR,
                         header_font_size=12, body_font_size=11,
                         table_object=None):
    """Style a table with colored header and alternating row colors.

    Args:
        table_id: objectId of the table
        num_rows: total rows (including header)
        num_cols: number of columns
        table_object: optional — the actual table object from the API response.
            If provided, uses cell_has_text() to avoid styling empty cells.
            If None, applies text styles to all cells (may error on empty cells).
        header_bg: header background color hex
        header_text_color: header text color hex
        odd_row_bg: odd row background hex
        even_row_bg: even row background hex
        text_color: body text color hex

    Returns:
        list of API requests for styling
    """
    reqs = []

    for r in range(num_rows):
        for c in range(num_cols):
            # Background color
            if r == 0:
                bg = header_bg
            elif r % 2 == 1:
                bg = odd_row_bg
            else:
                bg = even_row_bg

            reqs.append({
                'updateTableCellProperties': {
                    'objectId': table_id,
                    'tableRange': {
                        'location': {'rowIndex': r, 'columnIndex': c},
                        'rowSpan': 1, 'columnSpan': 1
                    },
                    'tableCellProperties': {
                        'tableCellBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': hex_to_rgb(bg)}}
                        }
                    },
                    'fields': 'tableCellBackgroundFill'
                }
            })

            # Text styling — check for empty cells if table_object provided
            should_style = True
            if table_object is not None:
                should_style = cell_has_text(table_object, r, c)

            if should_style:
                if r == 0:
                    # Header: bold, white text
                    reqs.append({
                        'updateTextStyle': {
                            'objectId': table_id,
                            'cellLocation': {'rowIndex': r, 'columnIndex': c},
                            'textRange': {'type': 'ALL'},
                            'style': {
                                'bold': True,
                                'fontSize': {'magnitude': header_font_size, 'unit': 'PT'},
                                'fontFamily': 'Arial',
                                'foregroundColor': _make_color(header_text_color)
                            },
                            'fields': 'bold,fontSize,fontFamily,foregroundColor'
                        }
                    })
                else:
                    # Body: normal text
                    reqs.append({
                        'updateTextStyle': {
                            'objectId': table_id,
                            'cellLocation': {'rowIndex': r, 'columnIndex': c},
                            'textRange': {'type': 'ALL'},
                            'style': {
                                'fontSize': {'magnitude': body_font_size, 'unit': 'PT'},
                                'fontFamily': 'Arial',
                                'foregroundColor': _make_color(text_color)
                            },
                            'fields': 'fontSize,fontFamily,foregroundColor'
                        }
                    })

    return reqs


# --- Image Operations ---

def upload_image_to_drive(drive_service, filepath, filename=None):
    """Upload an image to Google Drive and set public read permission.

    Args:
        drive_service: Google Drive API service
        filepath: local path to the image file
        filename: optional display name (defaults to basename of filepath)

    Returns:
        str: public URL in format https://drive.google.com/uc?id={file_id}
    """
    from googleapiclient.http import MediaFileUpload

    if filename is None:
        filename = os.path.basename(filepath)

    # Determine mimetype
    ext = os.path.splitext(filepath)[1].lower()
    mimetypes = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml'}
    mimetype = mimetypes.get(ext, 'image/png')

    file_metadata = {'name': filename}
    media = MediaFileUpload(filepath, mimetype=mimetype, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    file_id = file.get('id')

    # Set public read permission
    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return f'https://drive.google.com/uc?id={file_id}'


def create_image_request(slide_id, image_id, image_url, x, y, width, height):
    """Create a request to insert an image from a URL.

    The image_url should be a Google Drive public URL from upload_image_to_drive().
    """
    return {
        'createImage': {
            'objectId': image_id,
            'url': image_url,
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': _make_size(width, height),
                'transform': _make_transform(x, y)
            }
        }
    }


# --- Text Formatting ---

def parse_inline_formatting(text):
    """Parse bold/italic markdown markers in text.

    Handles ***bold italic***, **bold**, and *italic*.

    Returns:
        list of dicts: [{'text': str, 'bold': bool, 'italic': bool}, ...]
    """
    segments = []
    pattern = re.compile(r'\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*', re.DOTALL)
    last_end = 0
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        if start > last_end:
            segments.append({'text': text[last_end:start], 'bold': False, 'italic': False})
        if m.group(1) is not None:
            segments.append({'text': m.group(1), 'bold': True, 'italic': True})
        elif m.group(2) is not None:
            segments.append({'text': m.group(2), 'bold': True, 'italic': False})
        elif m.group(3) is not None:
            segments.append({'text': m.group(3), 'bold': False, 'italic': True})
        last_end = end
    if last_end < len(text):
        segments.append({'text': text[last_end:], 'bold': False, 'italic': False})
    return segments


def create_speaker_notes_request(notes_placeholder_id, text):
    """Create a request to insert speaker notes.

    Use get_notes_placeholder_id() first to find the placeholder ID.
    """
    if not notes_placeholder_id or not text:
        return []
    return [{
        'insertText': {
            'objectId': notes_placeholder_id,
            'text': text,
            'insertionIndex': 0
        }
    }]


# --- Batch Execution ---

def execute_batch(slides_service, presentation_id, requests, description=''):
    """Execute a batch of requests against the Google Slides API.

    Args:
        slides_service: Google Slides API service
        presentation_id: the presentation ID
        requests: list of request dicts
        description: optional description for logging

    Returns:
        API response
    """
    if not requests:
        return None
    if description:
        print(f'Executing batch: {description} ({len(requests)} requests)')
    return slides_service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()


# --- Targeted Slide Update ---

def get_slide_by_index(presentation, index):
    """Get slide info by page number (0-based index).

    Args:
        presentation: full presentation object from get_presentation()
        index: 0-based slide index

    Returns:
        dict with keys:
            - 'objectId': slide objectId
            - 'index': the slide index
            - 'elements': list of dicts with 'objectId', 'type', 'text' for each element

    Raises:
        IndexError: if index is out of range
    """
    slides = presentation.get('slides', [])
    if index < 0 or index >= len(slides):
        raise IndexError(f'Slide index {index} out of range (0-{len(slides)-1})')

    slide = slides[index]
    elements = []
    for el in slide.get('pageElements', []):
        obj_id = el['objectId']

        # Determine element type
        el_type = 'UNKNOWN'
        if 'shape' in el:
            el_type = el['shape'].get('shapeType', 'SHAPE')
        elif 'table' in el:
            el_type = 'TABLE'
        elif 'image' in el:
            el_type = 'IMAGE'
        elif 'line' in el:
            el_type = 'LINE'

        # Extract text if available
        text = ''
        if 'shape' in el:
            for te in el['shape'].get('text', {}).get('textElements', []):
                if 'textRun' in te:
                    text += te['textRun'].get('content', '')

        elements.append({
            'objectId': obj_id,
            'type': el_type,
            'text': text.strip()
        })

    return {
        'objectId': slide['objectId'],
        'index': index,
        'elements': elements
    }


def clear_slide_requests(presentation, slide_id, keep_types=None):
    """Create requests to delete all elements on a slide, optionally keeping certain types.

    Args:
        presentation: full presentation object
        slide_id: objectId of the slide to clear
        keep_types: optional set of element types to keep, e.g. {'IMAGE'}.
            If None, deletes ALL elements on the slide.

    Returns:
        list of deleteObject requests
    """
    keep_types = keep_types or set()
    reqs = []

    for slide in presentation.get('slides', []):
        if slide['objectId'] == slide_id:
            for el in slide.get('pageElements', []):
                el_type = 'UNKNOWN'
                if 'shape' in el:
                    el_type = el['shape'].get('shapeType', 'SHAPE')
                elif 'table' in el:
                    el_type = 'TABLE'
                elif 'image' in el:
                    el_type = 'IMAGE'
                elif 'line' in el:
                    el_type = 'LINE'

                if el_type not in keep_types:
                    reqs.append({'deleteObject': {'objectId': el['objectId']}})
            break

    return reqs


def replace_slide(slides_service, presentation_id, slide_id, slide_index):
    """Delete a slide and create a new BLANK slide at the same position.

    Args:
        slides_service: Google Slides API service
        presentation_id: presentation ID
        slide_id: objectId of the slide to replace
        slide_index: current index of the slide (0-based)

    Returns:
        str: objectId of the new slide
    """
    new_id = f'replaced_{uid()}'

    # Delete old slide, then create new one at the same index
    reqs = [
        {'deleteObject': {'objectId': slide_id}},
        create_blank_slide_request(new_id, slide_index)
    ]
    execute_batch(slides_service, presentation_id, reqs, f'Replace slide at index {slide_index}')

    return new_id


def update_slide_title(slides_service, presentation_id, presentation, slide_id, new_title):
    """Update the title text of a slide.

    Finds the title element (TITLE/CENTERED_TITLE placeholder or first TEXT_BOX with large font),
    deletes its existing text, and inserts new text.

    Args:
        slides_service: Google Slides API service
        presentation_id: presentation ID
        presentation: full presentation object
        slide_id: objectId of the slide
        new_title: new title text

    Returns:
        bool: True if title was updated, False if no title element found
    """
    title_obj_id = None

    for slide in presentation.get('slides', []):
        if slide['objectId'] == slide_id:
            for el in slide.get('pageElements', []):
                shape = el.get('shape', {})
                ph = shape.get('placeholder', {})
                ph_type = ph.get('type', '')

                # Check for title placeholder
                if ph_type in ('TITLE', 'CENTERED_TITLE'):
                    title_obj_id = el['objectId']
                    break

            # If no placeholder, look for a TEXT_BOX element that looks like a title
            # (has bold text and is near the top of the slide)
            if not title_obj_id:
                for el in slide.get('pageElements', []):
                    if 'shape' not in el:
                        continue
                    shape = el['shape']
                    if shape.get('shapeType') != 'TEXT_BOX':
                        continue
                    # Check if it's near the top (translateY < 300000)
                    transform = el.get('elementProperties', el.get('transform', {}))
                    # Check text style for bold
                    for te in shape.get('text', {}).get('textElements', []):
                        style = te.get('textRun', {}).get('style', {})
                        if style.get('bold') and te.get('textRun', {}).get('content', '').strip():
                            title_obj_id = el['objectId']
                            break
                    if title_obj_id:
                        break
            break

    if not title_obj_id:
        return False

    # Delete all existing text and insert new title
    reqs = [
        {
            'deleteText': {
                'objectId': title_obj_id,
                'textRange': {'type': 'ALL'}
            }
        },
        {
            'insertText': {
                'objectId': title_obj_id,
                'text': new_title,
                'insertionIndex': 0
            }
        }
    ]
    execute_batch(slides_service, presentation_id, reqs, f'Update title to: {new_title}')
    return True


def update_slide_notes(slides_service, presentation_id, presentation, slide_id, new_notes):
    """Update the speaker notes of a slide.

    Clears existing notes and inserts new text.

    Args:
        slides_service: Google Slides API service
        presentation_id: presentation ID
        presentation: full presentation object
        slide_id: objectId of the slide
        new_notes: new speaker notes text

    Returns:
        bool: True if notes were updated, False if no notes placeholder found
    """
    notes_id = get_notes_placeholder_id(presentation, slide_id)
    if not notes_id:
        return False

    reqs = [
        {
            'deleteText': {
                'objectId': notes_id,
                'textRange': {'type': 'ALL'}
            }
        }
    ]
    reqs.extend(create_speaker_notes_request(notes_id, new_notes))
    execute_batch(slides_service, presentation_id, reqs, 'Update speaker notes')
    return True


def get_slide_index_by_id(presentation, slide_id):
    """Find the 0-based index of a slide by its objectId.

    Returns:
        int: slide index, or -1 if not found
    """
    for i, slide in enumerate(presentation.get('slides', [])):
        if slide['objectId'] == slide_id:
            return i
    return -1


# --- High-Level Convenience Functions ---

def create_styled_table_on_slide(slides_service, drive_service, presentation_id,
                                 slide_id, table_id, data,
                                 x=311700, y=800000, width=8520600, height=3600000):
    """Create and style a table on an existing slide in one call.

    Args:
        data: 2D list where data[0] is the header row

    This is a convenience function that handles:
    1. Create the table
    2. Populate cells
    3. Refresh presentation to get table object
    4. Style with cell_has_text() safety check
    """
    rows = len(data)
    cols = len(data[0])

    # Step 1: Create table and populate
    reqs = [create_table_request(slide_id, table_id, rows, cols, x, y, width, height)]
    reqs.extend(populate_table_requests(table_id, data))
    execute_batch(slides_service, presentation_id, reqs, 'Create and populate table')

    # Step 2: Refresh and style (need fresh data for cell_has_text)
    pres = get_presentation(slides_service, presentation_id)
    table_object = None
    for slide in pres['slides']:
        if slide['objectId'] == slide_id:
            for el in slide.get('pageElements', []):
                if el['objectId'] == table_id:
                    table_object = el.get('table')
                    break
            break

    style_reqs = style_table_requests(table_id, rows, cols, table_object=table_object)
    execute_batch(slides_service, presentation_id, style_reqs, 'Style table')
