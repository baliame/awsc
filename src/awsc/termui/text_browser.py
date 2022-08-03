import pyperclip
from pygments.lexers import JsonLexer
from pygments.token import Token

from .color import Color, ColorBlackOnGold, ColorGold, Palette8Bit
from .common import Commons
from .control import Control


class NullHighlighter:
    def __call__(self, browser, lines):
        return [[(line, browser.color)] for line in lines]


class JsonHighlighter:
    def _get_scheme_color(self, browser, color_name):
        try:
            c = browser.scheme["colors"][color_name]
        except KeyError as e:
            return browser.color
        return Color(Palette8Bit(), c["foreground"], background=c["background"])

    def __call__(self, browser, lines):
        import sys

        joined = "\n".join(lines)
        lexer = JsonLexer(tabsize=2, stripnl=False, stripall=False)
        tokens = lexer.get_tokens(joined)
        current_line = []
        result_lines = []
        for token in tokens:
            print("Token: {0}".format(token), file=sys.stderr)
            if token[0] in Token.Text:
                brk = token[1].split("\n")
                while len(brk) > 1:
                    current_line.append(
                        (
                            brk[0],
                            self._get_scheme_color(
                                browser,
                                "syntax_highlight_{0}".format(
                                    str(token[0]).lower().replace(".", "_")
                                ),
                            ),
                        )
                    )
                    result_lines.append(current_line)
                    current_line = []
                    brk = brk[1:]
                current_line.append(
                    (
                        brk[0],
                        self._get_scheme_color(
                            browser,
                            "syntax_highlight_{0}".format(
                                str(token[0]).lower().replace(".", "_")
                            ),
                        ),
                    )
                )
            else:
                current_line.append(
                    (
                        token[1],
                        self._get_scheme_color(
                            browser,
                            "syntax_highlight_{0}".format(
                                str(token[0]).lower().replace(".", "_")
                            ),
                        ),
                    )
                )
        result_lines.append(current_line)
        return result_lines


class TextBrowser(Control):
    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        color=ColorGold,
        filtered_color=ColorBlackOnGold,
        scheme=None,
        syntax_highlighting=False,
        *args,
        **kwargs
    ):
        super().__init__(parent, alignment, dimensions, *args, **kwargs)
        self.entries = []
        self.hotkeys = {
            "KEY_DOWN": self.scroll_down,
            "KEY_UP": self.scroll_up,
            "KEY_LEFT": self.scroll_left,
            "KEY_RIGHT": self.scroll_right,
            "c": self.copy_contents,
            "w": self.toggle_wrap,
            "KEY_END": self.end,
            "KEY_HOME": self.home,
            "KEY_PGUP": self.pgup,
            "KEY_PGDOWN": self.pgdown,
        }
        self.tooltips = {"c": "Copy", "w": "Toggle Wrap"}
        self.scheme = scheme
        self.color = color
        self.filtered_color = filtered_color
        self.lines = []
        self.display_lines = []
        self._prefilter_lines = []
        self.top = 0
        self.left = 0
        self._filter_line = 0
        self.wrap = False
        self._filter = None
        self.filter_positions = {}
        self._current_filter_match = []
        self.syntax_highlighter = (
            JsonHighlighter() if syntax_highlighting else NullHighlighter()
        )

    def _raw(self, line_part):
        if isinstance(line_part, tuple):
            return line_part[0]
        return line_part

    def rawlines(self):
        return [self.raw(i) for i in range(len(self.lines))]

    def raw(self, line=None):
        if line is None:
            return "\n".join(self.rawlines())
        else:
            return "".join(
                [self._raw(self.lines[line][i]) for i in range(len(self.lines[line]))]
            )

    def add_text(self, text):
        add = text.split("\n")
        self.lines.extend(add)
        self._prefilter_lines.extend(add)
        self.display_lines = self.syntax_highlighter(self, self.lines)
        Commons.UIInstance.dirty = True

    def clear(self):
        Commons.UIInstance.dirty = True
        self.lines = []
        self.filter_positions = {}
        self._prefilter_lines = []
        self.filter = None
        self.top = 0
        self.left = 0

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        Commons.UIInstance.dirty = True
        refilter = False
        if self._filter != value:
            self._filter_line = -1
            self.filter_positions = {}
            self._current_filter_match = []
            refilter = True

        self._filter = value

        if value is None or value == "":
            return

        if refilter:
            for i in range(len(self.lines)):
                rawline = self.raw(i)
                ml = rawline.split(self._filter)
                pos = 0
                for j in range(1, len(ml)):
                    pos += len(ml[j - 1])
                    if i not in self.filter_positions:
                        self.filter_positions[i] = []
                    self.filter_positions[i].append(pos)
                if len(ml) > 1:
                    self._current_filter_match.append(i)

        for elem in self._current_filter_match:
            if elem > self._filter_line:
                self._filter_line = elem
                self.top = elem
                return
        if len(self._current_filter_match) > 0:
            self.top = self._current_filter_match[0]
            self._filter_line = self.top

    def add_hotkey(self, hotkey, action, tooltip=None):
        self.hotkeys[hotkey] = action
        if tooltip is not None:
            self.tooltips[hotkey] = tooltip
        Commons.UIInstance.dirty = True

    def input(self, key):
        inkey = str(key)
        if key.is_sequence:
            inkey = key.name
        else:
            inkey = inkey.lower()
        if inkey in self.hotkeys.keys():
            self.hotkeys[inkey](self)
            Commons.UIInstance.dirty = True
            return True
        return False

    def toggle_wrap(self, *args):
        self.wrap = not self.wrap
        if self.wrap:
            self.left = 0

    def scroll_down(self, *args):
        if self.top < len(self.lines) - 1:
            self.top += 1

    def scroll_up(self, *args):
        if self.top > 0:
            self.top -= 1

    def scroll_right(self, *args):
        if self.wrap:
            return
        self.left += 1

    def scroll_left(self, *args):
        if self.wrap:
            return
        if self.left > 0:
            self.left -= 1

    def end(self, *args):
        c = self.corners()
        y0 = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        h = y1 - y0 + 1
        limit = len(self.lines) - h if not self.wrap else len(self.lines) - 1
        self.top = max(limit, 0)

    def home(self, *args):
        self.top = 0

    def pgup(self, *args):
        c = self.corners()
        y0 = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        h = y1 - y0 + 1
        self.top = max(self.top - h, 0)

    def pgdown(self, *args):
        c = self.corners()
        y0 = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        h = y1 - y0 + 1
        limit = len(self.lines) - h if not self.wrap else len(self.lines) - 1
        self.top = max(min(limit, self.top + h), 0)

    def copy_contents(self, *args):
        pyperclip.copy(self.raw())

    def paint(self):
        import sys

        super().paint()
        print(
            "Lines ({0}): {1}".format(len(self.display_lines), self.display_lines),
            file=sys.stderr,
        )
        c = self.corners()
        y = c[1][0] + (0 if self.border is None else 1)
        y1 = c[1][1] - (0 if self.border is None else 1)
        x0 = c[0][0] + (0 if self.border is None else 1)
        x1 = c[0][1] - (0 if self.border is None else 1)
        for i in range(self.top, len(self.display_lines)):
            line = self.display_lines[i]
            skip_chars = self.left
            x = x0
            end = False
            pos = skip_chars
            next_filter_pos = -1
            next_filter_last_pos = -1
            nfp_idx = 0
            if i in self.filter_positions:
                for p in self.filter_positions[i]:
                    if p >= pos:
                        next_filter_pos = p
                        next_filter_last_pos = p + len(self._filter) - 1
                        break
                    elif p + len(self._filter) - 1 >= pos:
                        next_filter_pos = p
                        next_filter_last_pos = p + len(self._filter) - 1
                    else:
                        nfp_idx += 1
            for elem in line:
                buf = self._raw(elem)
                if skip_chars > len(buf):
                    skip_chars -= len(buf)
                    continue
                elif skip_chars > 0:
                    buf = buf[skip_chars:]
                    skip_chars = 0
                color = self.color if not isinstance(elem, tuple) else elem[1]

                while len(buf) > 0:
                    space = x1 - x + 1
                    text = buf[:space]
                    buf = buf[space:]
                    while len(text) > 0:
                        if (
                            next_filter_last_pos >= 0
                            and pos >= next_filter_pos
                            and pos <= next_filter_last_pos
                        ):
                            filt = next_filter_last_pos - pos + 1
                            if filt >= len(text):
                                Commons.UIInstance.print(
                                    text, xy=(x, y), color=self.filtered_color
                                )
                                x += len(text)
                                pos += len(text)
                                text = ""
                            else:
                                Commons.UIInstance.print(
                                    text[:filt], xy=(x, y), color=self.filtered_color
                                )
                                text = text[filt:]
                                x += filt
                                pos += filt
                                nfp_idx += 1
                                if len(self.filter_positions[i]) > nfp_idx:
                                    next_filter_pos = self.filter_positions[i][nfp_idx]
                                    next_filter_last_pos = (
                                        next_filter_pos + len(self._filter) - 1
                                    )
                                else:
                                    next_filter_pos = -1
                                    next_filter_last_pos = -1
                        elif next_filter_pos >= 0 and pos + len(text) > next_filter_pos:
                            unfilt = next_filter_pos - pos
                            if unfilt > 0:
                                Commons.UIInstance.print(
                                    text[:unfilt], xy=(x, y), color=color
                                )
                                text = text[unfilt:]
                                x += unfilt
                                pos += unfilt
                            filt = next_filter_last_pos - next_filter_pos + 1
                            if filt >= len(text):
                                Commons.UIInstance.print(
                                    text, xy=(x, y), color=self.filtered_color
                                )
                                x += len(text)
                                pos += len(text)
                                text = ""
                            else:
                                Commons.UIInstance.print(
                                    text[:filt], xy=(x, y), color=self.filtered_color
                                )
                                text = text[filt:]
                                x += filt
                                pos += filt
                                nfp_idx += 1
                                if len(self.filter_positions[i]) > nfp_idx:
                                    next_filter_pos = self.filter_positions[i][nfp_idx]
                                    next_filter_last_pos = (
                                        next_filter_pos + len(self._filter) - 1
                                    )
                                else:
                                    next_filter_pos = -1
                                    next_filter_last_pos = -1
                        else:
                            Commons.UIInstance.print(text, xy=(x, y), color=color)
                            pos += len(text)
                            x += len(text)
                            text = ""
                    if x > x1:
                        y += 1
                        x = x0
                        if not self.wrap:
                            end = True

                    if end or y > y1:
                        break
            if not end:
                y += 1
                x = x0
            if y > y1:
                break
