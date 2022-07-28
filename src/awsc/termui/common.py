class Commons:
    UIInstance = None
    TextfieldInputs = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890/:@#.$=_-[]{}()<>|%!+~? "
    TextfieldInputsAlphaNum = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
    )

    @classmethod
    def alphanum_with_symbols(cls, symbols):
        return "{0}{1}".format(cls.TextfieldInputsAlphaNum, symbols)
