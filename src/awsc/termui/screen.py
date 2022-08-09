class Character:
    def __init__(self):
        self.value = " "
        self.color = Character.nullcolor
        self.bold = False
        self.out = " "
        self.dirty = False

    @staticmethod
    def nullcolor(x, **kwargs):
        return x

    def clear(self):
        self.out = "\033[38;5;220m \033[0m"
        self.dirty = False

    def output(self):
        if self.dirty:
            self.dirty = False
            out = self.value
            if self.color is not None:
                out = self.color(out, bold=self.bold)
            self.out = out
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
            if len(self.buf) == self.screen.ui.width:
                for character in self.buf:
                    character.clear()
            else:
                self.buf = [Character() for i in range(self.screen.ui.width)]

        def __getitem__(self, i):
            return self.buf[i]

        def output(self):
            return "".join(x.output() for x in self.buf)

    def clear(self):
        if len(self.buf) == self.ui.height:
            for character in self.buf:
                character.clear()
        else:
            self.buf = [Screen.Row(self) for i in range(self.ui.height)]

    def __getitem__(self, i):
        return self.buf[i]

    def output(self):
        print("\r\n".join(x.output() for x in self.buf), end="")
