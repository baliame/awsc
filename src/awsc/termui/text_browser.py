"""
This module defines classes which allow viewing plain text or json data.
"""
import pyperclip
from pygments.lexers.data import JsonLexer
from pygments.token import Token

from .color import Color, ColorBlackOnGold, ColorGold, Palette8Bit
from .common import Commons
from .control import HotkeyControl


class NullHighlighter:
    """
    Syntax highlighter for text browsers which does not highlight syntax.
    """

    def __call__(self, browser, lines):
        return [[(line, browser.color)] for line in lines]


class JsonHighlighter:
    """
    Syntax highlighter for text browsers displaying json.
    """

    def _get_scheme_color(self, browser, color_name):
        try:
            color = browser.scheme["colors"][color_name]
        except AttributeError:
            return browser.color
        except KeyError:
            return browser.color
        return Color(Palette8Bit(), color["foreground"], background=color["background"])

    def __call__(self, browser, lines):
        joined = "\n".join(lines)
        lexer = JsonLexer(tabsize=2, stripnl=False, stripall=False)
        tokens = lexer.get_tokens(joined)
        current_line = []
        result_lines = []
        for token in tokens:
            token_color_name = (
                f"syntax_highlight_{str(token[0]).lower().replace('.', '_')}"
            )
            token_color = self._get_scheme_color(browser, token_color_name)
            if token[0] in Token.Text:
                brk = token[1].split("\n")
                while len(brk) > 1:
                    current_line.append((brk[0], token_color))
                    result_lines.append(current_line)
                    current_line = []
                    brk = brk[1:]
                current_line.append((brk[0], token_color))
            else:
                current_line.append((token[1], token_color))
        result_lines.append(current_line)
        return result_lines


class TextBrowser(HotkeyControl):
    """
    Text browsers allow the display of large blobs of text which can be optionally syntax highlighted.

    Attributes
    ----------
    scheme : awsc.config.scheme.Scheme
        Reference to the scheme being used by the browser. Since this module has no access to the configuration, this needs to be explicitly
        passed.
    color : awsc.termui.color.Color
        Default color used for text within the browser.
    filtered_color : awsc.termui.color.Color
        Color used for highlighting text when using search.
    lines : list
        A raw list of lines to display, without syntax highlighting applied.
    display_lines : list
        A list of lines to display with syntax highlighting applied. Acts as a cache that is cleared when new raw lines are added.
    top : int
        The amount of rows by which the control is scrolled down.
    left : int
        The amount of characters by which the control is scrolled right.
    wrap : bool
        If set, wraps lines that would go off the right edge. Disables scrolling horizontally.
    _filter : str
        Search string.
    filter_positions : dict
        A cache of all positions within the control where matches for the search are found.
    """

    def __init__(
        self,
        *args,
        color=ColorGold,
        filtered_color=ColorBlackOnGold,
        scheme=None,
        syntax_highlighting=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.entries = []

        self.add_hotkey("KEY_DOWN", self.scroll_down)
        self.add_hotkey("KEY_UP", self.scroll_up)
        self.add_hotkey("KEY_LEFT", self.scroll_left)
        self.add_hotkey("KEY_RIGHT", self.scroll_right)
        self.add_hotkey("KEY_END", self.end)
        self.add_hotkey("KEY_HOME", self.home)
        self.add_hotkey("KEY_PGUP", self.pgup)
        self.add_hotkey("KEY_PGDOWN", self.pgdown)
        self.add_hotkey("c", self.copy_contents, "Copy")
        self.add_hotkey("w", self.toggle_wrap, "Toggle Wrap")
        self.scheme = scheme
        self.color = color
        self.filtered_color = filtered_color
        self.lines = []
        self.display_lines = []
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
        """
        Generates a list of raw lines.

        Returns
        -------
        list(str)
            A list of lines in the text browser.
        """
        return [self.raw(i) for i in range(len(self.lines))]

    def raw(self, line=None):
        """
        Generates the raw output of the text browser.

        Parameters
        ----------
        line : int, optional
            If provided, returns the line with this index, otherwise, returns the text of the entire text browser.

        Returns
        -------
        str
            The raw text of the entire browser if no line index is provided, otherwise, the raw text of a single line.
        """
        if line is None:
            return "\n".join(self.rawlines())
        return "".join(
            [self._raw(self.lines[line][i]) for i in range(len(self.lines[line]))]
        )

    def add_text(self, text):
        """
        Adds raw text to the text browser.

        Parameters
        ----------
        text : str
            The text to append to the existing text in the browser.
        """
        add = text.split("\n")
        self.lines.extend(add)
        self.display_lines = self.syntax_highlighter(self, self.lines)
        Commons.UIInstance.dirty = True

    def clear(self):
        """
        Empties out the text browser.
        """
        Commons.UIInstance.dirty = True
        self.lines = []
        self.display_lines = []
        self.filter_positions = {}
        self.filter = None
        self.top = 0
        self.left = 0

    @property
    def filter(self):
        """
        Property. If changed, searches for that particular snippet of text within the browser. Set to None to stop searching.
        """
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
                processed_line = rawline.split(self._filter)
                pos = 0
                for j in range(1, len(processed_line)):
                    pos += len(processed_line[j - 1])
                    if i not in self.filter_positions:
                        self.filter_positions[i] = []
                    self.filter_positions[i].append(pos)
                if len(processed_line) > 1:
                    self._current_filter_match.append(i)

        for elem in self._current_filter_match:
            if elem > self._filter_line:
                self._filter_line = elem
                self.top = elem
                return
        if len(self._current_filter_match) > 0:
            self.top = self._current_filter_match[0]
            self._filter_line = self.top

    def toggle_wrap(self, *args):
        """
        Hotkey callback for toggling the wrap flag.
        """
        self.wrap = not self.wrap
        if self.wrap:
            self.left = 0

    def scroll_down(self, *args):
        """
        Hotkey callback for scrolling down within the browser by a single line.
        """
        if self.top < len(self.lines) - 1:
            self.top += 1

    def scroll_up(self, *args):
        """
        Hotkey callback for scrolling up within the browser by a single line.
        """
        if self.top > 0:
            self.top -= 1

    def scroll_right(self, *args):
        """
        Hotkey callback for scrolling right within the browser by a single character column.
        """
        if self.wrap:
            return
        self.left += 1

    def scroll_left(self, *args):
        """
        Hotkey callback for scrolling left within the browser by a single character column.
        """
        if self.wrap:
            return
        if self.left > 0:
            self.left -= 1

    def end(self, *args):
        """
        Hotkey callback for scrolling to bring the final line in view within the browser.
        """
        corners = self.corners
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        height = y1 - y0 + 1
        limit = len(self.lines) - height if not self.wrap else len(self.lines) - 1
        self.top = max(limit, 0)

    def home(self, *args):
        """
        Hotkey callback for jumping to the top of the text browser.
        """
        self.top = 0

    def pgup(self, *args):
        """
        Hotkey callback for scrolling up within the browser by a single page.
        """
        corners = self.corners
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        height = y1 - y0 + 1
        self.top = max(self.top - height, 0)

    def pgdown(self, *args):
        """
        Hotkey callback for scrolling down within the browser by a single page.
        """
        corners = self.corners
        y0 = corners[1][0] + (0 if self.border is None else 1)
        y1 = corners[1][1] - (0 if self.border is None else 1)
        height = y1 - y0 + 1
        limit = len(self.lines) - height if not self.wrap else len(self.lines) - 1
        self.top = max(min(limit, self.top + height), 0)

    def copy_contents(self, *args):
        """
        Hotkey callback for copying the contents of the text browser to the system clipboard.
        """
        pyperclip.copy(self.raw())

    def paint(self):
        super().paint()
        ((x0, x1), (y, y1)) = self.inner
        for i, line in enumerate(self.display_lines):
            if i < self.top:
                continue
            skip_chars = self.left
            x = x0
            end = False
            pos = skip_chars
            next_filter_pos = -1
            next_filter_last_pos = -1
            nfp_idx = 0
            if i in self.filter_positions:
                for filter_position in self.filter_positions[i]:
                    if filter_position >= pos:
                        next_filter_pos = filter_position
                        next_filter_last_pos = filter_position + len(self._filter) - 1
                        break
                    if filter_position + len(self._filter) - 1 >= pos:
                        next_filter_pos = filter_position
                        next_filter_last_pos = filter_position + len(self._filter) - 1
                    else:
                        nfp_idx += 1
            for elem in line:
                buf = self._raw(elem)
                if skip_chars > len(buf):
                    skip_chars -= len(buf)
                    continue
                if skip_chars > 0:
                    buf = buf[skip_chars:]
                    skip_chars = 0
                color = self.color if not isinstance(elem, tuple) else elem[1]

                while len(buf) > 0:
                    space = x1 - x + 1
                    text = buf[:space]
                    buf = buf[space:]
                    while len(text) > 0:
                        if next_filter_pos <= pos <= next_filter_last_pos >= 0:
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
                        elif 0 <= next_filter_pos < pos + len(text):
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
