"""
This module contains common termui features.
"""


class Commons:
    """
    TermUI Common class.

    This class holds the UI singleton as well as some default constants.

    Attributes
    ----------
    UIInstance : awsc.termui.ui.UI
        The UI singleton which has been instantiated for the terminal.
    TextfieldInputs : str
        All accepted inputs for a textfield which accepts any latin alphabet character, number, or most commonly used symbols.
    TextfieldInputsAlphaNum : str
        All accepted inputs for a textfield which accepts only latin alphabet characters and numbers.
    """

    UIInstance = None
    TextfieldInputs = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890/:@#.$=_-[]{}()<>|%!+~? "
    TextfieldInputsAlphaNum = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
    )

    @classmethod
    def alphanum_with_symbols(cls, symbols):
        """
        Generates a set of accepted inputs for a textfield which accepts all latin alphabet characters and numbers but only a certain set of symbols.

        Returns
        -------
        str
            The set of accepted inputs for the textfield.
        """
        return f"{cls.TextfieldInputsAlphaNum}{symbols}"


def column_sizer(y0, y1, labels, data):
    """
    Determines column widths.

    Parameters
    ----------
    y0 : int
        Starting y.
    y1 : int
        Ending y.
    labels : list
        A list of labels.
    data : dict, optional
        A mapping of labels to values.

    Returns
    -------
    list(int)
        A list of widths for each column.
    """
    longest = []
    length = 0
    y = y0
    for name in labels:
        if data is not None and name not in data:
            continue
        display = name + ": "
        if len(display) > length:
            length = len(display)
        y += 1
        if y > y1:
            y = y0
            longest.append(length)
            length = 0
    if length > 0:
        longest.append(length)
    return longest
