#!/usr/bin/env python3
"""Convert Confluence body.storage HTML to clean Markdown, reducing token usage."""
import sys
import json
import re
from html.parser import HTMLParser


class HTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = []
        self.list_stack = []
        self.ol_counters = []
        self.in_code_block = False
        self.heading_level = 0
        self.skip_tags = 0  # nesting depth of tags to skip
        self.link_href = None
        self.link_text = []
        self.in_link = False
        # Table state
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False
        self.is_header_row = False

    def _append(self, text):
        if self.in_cell:
            self.current_cell.append(text)
        elif self.in_link:
            self.link_text.append(text)
        else:
            self.output.append(text)

    def handle_starttag(self, tag, attrs):
        if self.skip_tags > 0 and tag not in ('ac:rich-text-body', 'ac:plain-text-body'):
            self.skip_tags += 1
            return

        attrs_dict = dict(attrs)

        # --- Confluence macros ---
        if tag == 'ac:structured-macro':
            name = attrs_dict.get('ac:name', '')
            if name == 'code':
                self.in_code_block = True
                self._append('\n```\n')
            elif name in ('info', 'note', 'warning', 'tip'):
                self._append(f'\n> **{name.upper()}**: ')
            elif name in ('toc', 'anchor', 'excerpt', 'section', 'column'):
                self.skip_tags += 1
            return

        if tag == 'ac:parameter':
            self.skip_tags += 1
            return

        if tag in ('ac:rich-text-body', 'ac:plain-text-body'):
            if self.skip_tags > 0:
                self.skip_tags -= 1
            return

        if tag == 'ac:link':
            self.in_link = True
            self.link_text = []
            self.link_href = None
            return

        if tag == 'ri:page':
            title = attrs_dict.get('ri:content-title', '')
            if title:
                self.link_href = title
            return

        if tag.startswith(('ac:', 'ri:')):
            return

        # --- Standard HTML ---
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.heading_level = int(tag[1])
            self._append('\n\n' + '#' * self.heading_level + ' ')

        elif tag in ('strong', 'b'):
            self._append('**')

        elif tag in ('em', 'i'):
            self._append('*')

        elif tag == 'u':
            self._append('__')

        elif tag == 's':
            self._append('~~')

        elif tag == 'p':
            if not self.in_cell:
                self._append('\n\n')

        elif tag == 'br':
            self._append('\n')

        elif tag == 'hr':
            self._append('\n---\n')

        elif tag == 'a':
            self.in_link = True
            self.link_href = attrs_dict.get('href', '')
            self.link_text = []

        elif tag == 'img':
            alt = attrs_dict.get('alt', 'image')
            src = attrs_dict.get('src', '')
            self._append(f'![{alt}]({src})')

        elif tag == 'ul':
            self.list_stack.append('ul')
            if not self.in_cell:
                self._append('\n')

        elif tag == 'ol':
            self.list_stack.append('ol')
            self.ol_counters.append(0)
            if not self.in_cell:
                self._append('\n')

        elif tag == 'li':
            indent = '  ' * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == 'ol':
                self.ol_counters[-1] += 1
                self._append(f'{indent}{self.ol_counters[-1]}. ')
            else:
                self._append(f'{indent}- ')

        elif tag == 'code' and not self.in_code_block:
            self._append('`')

        elif tag == 'pre':
            self.in_code_block = True
            self._append('\n```\n')

        elif tag == 'blockquote':
            self._append('\n> ')

        elif tag == 'table':
            self.in_table = True
            self.table_rows = []

        elif tag == 'tr':
            self.current_row = []
            self.is_header_row = False

        elif tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = []
            if tag == 'th':
                self.is_header_row = True

    def handle_endtag(self, tag):
        if self.skip_tags > 0:
            if tag in ('ac:structured-macro', 'ac:parameter'):
                self.skip_tags -= 1
            return

        if tag in ('ac:rich-text-body', 'ac:plain-text-body'):
            return

        if tag == 'ac:link':
            text = ''.join(self.link_text).strip()
            href = self.link_href or ''
            if href:
                self.output.append(f'[{text or href}]({href})')
            elif text:
                self.output.append(text)
            self.in_link = False
            self.link_text = []
            self.link_href = None
            return

        if tag == 'ac:structured-macro':
            if self.in_code_block:
                self.in_code_block = False
                self._append('\n```\n')
            return

        if tag.startswith(('ac:', 'ri:')):
            return

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._append('\n')
            self.heading_level = 0

        elif tag in ('strong', 'b'):
            self._append('**')

        elif tag in ('em', 'i'):
            self._append('*')

        elif tag == 'u':
            self._append('__')

        elif tag == 's':
            self._append('~~')

        elif tag == 'a':
            text = ''.join(self.link_text).strip()
            href = self.link_href or ''
            if href:
                self.output.append(f'[{text or href}]({href})')
            elif text:
                self.output.append(text)
            self.in_link = False
            self.link_text = []
            self.link_href = None

        elif tag == 'ul':
            if self.list_stack:
                self.list_stack.pop()
            self._append('\n')

        elif tag == 'ol':
            if self.list_stack:
                self.list_stack.pop()
            if self.ol_counters:
                self.ol_counters.pop()
            self._append('\n')

        elif tag == 'li':
            self._append('\n')

        elif tag == 'code' and not self.in_code_block:
            self._append('`')

        elif tag == 'pre':
            self.in_code_block = False
            self._append('\n```\n')

        elif tag in ('td', 'th'):
            self.current_row.append(''.join(self.current_cell).strip())
            self.current_cell = []
            self.in_cell = False

        elif tag == 'tr':
            self.table_rows.append((self.is_header_row, self.current_row))
            self.current_row = []

        elif tag == 'table':
            self.in_table = False
            self._render_table()

    def handle_data(self, data):
        if self.skip_tags > 0:
            return
        self._append(data)

    def handle_entityref(self, name):
        entities = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'nbsp': ' '}
        self._append(entities.get(name, f'&{name};'))

    def handle_charref(self, name):
        try:
            if name.startswith('x'):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
            self._append(char)
        except (ValueError, OverflowError):
            self._append(f'&#{name};')

    def _render_table(self):
        if not self.table_rows:
            return

        rows = [r for _, r in self.table_rows]
        if not rows:
            return

        cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < cols:
                r.append('')

        widths = [max(len(r[i]) if i < len(r) else 0 for r in rows) for i in range(cols)]
        widths = [max(w, 3) for w in widths]

        lines = []
        first_is_header = self.table_rows[0][0] if self.table_rows else False

        for idx, row in enumerate(rows):
            line = '| ' + ' | '.join(
                cell.ljust(widths[j]) for j, cell in enumerate(row)
            ) + ' |'
            lines.append(line)
            if idx == 0:
                sep = '| ' + ' | '.join('-' * widths[j] for j in range(cols)) + ' |'
                lines.append(sep)

        self.output.append('\n\n' + '\n'.join(lines) + '\n')

    def get_markdown(self):
        text = ''.join(self.output)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    parser = HTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        html = data.get('body', {}).get('storage', {}).get('value', '')
        if html:
            data['body_markdown'] = html_to_markdown(html)
            del data['body']
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, KeyError):
        print(html_to_markdown(raw))


if __name__ == '__main__':
    main()
