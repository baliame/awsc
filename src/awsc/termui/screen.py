class Character:
    def __init__(self):
        self.value = " "
        self.color = None
        self.bold = False
        self.out = " "
        self.dirty = False

    def clear(self):
        self.out = "\033[38;5;220m \033[0m"
        self.dirty = False

    def output(self):
        if self.dirty:
            self.dirty = False
            o = self.value
            if self.color is not None:
                o = self.color(o, bold=self.bold)
            self.out = o
        return self.out


class Screen:
    def __init__(self, ui):
        self.ui = ui
        self.buf = []
        self.clear()

    class Row:
        def __init__(self, screen):
            self.screen = screen
            self.buf = []
            self.clear()

        def clear(self):
            if len(self.buf) == self.screen.ui.w:
                for c in self.buf:
                    c.clear()
            else:
                self.buf = [Character() for i in range(self.screen.ui.w)]

        def __getitem__(self, i):
            return self.buf[i]

        def output(self):
            return "".join(x.output() for x in self.buf)

    def clear(self):
        if len(self.buf) == self.ui.h:
            for c in self.buf:
                c.clear()
        else:
            self.buf = [Screen.Row(self) for i in range(self.ui.h)]

    def __getitem__(self, i):
        return self.buf[i]

    def output(self):
        print("\r\n".join(x.output() for x in self.buf), end="")
