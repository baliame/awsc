import yaml


class Scheme:
    def __init__(self, config):
        self.style_file = config.path / "style.yaml"
        self.config = config
        if not self.style_file.exists():
            self.create_default_config()
        else:
            self.parse_config()

    def backup_and_reset(self):
        print(
            "Restoring style scheme to defaults. Creating backup of pre-restore scheme."
        )
        backup = self.config.path / "style.yaml.bak"
        self.style_file.rename(backup)
        self.create_default_config()

    def create_default_config(self):
        print("Creating first time style scheme...")
        self.style = {
            "colors": {
                "generic": {
                    "foreground": 220,
                    "background": 0,
                },
                "highlight": {
                    "foreground": 70,
                    "background": 0,
                },
                "highlight_selection": {
                    "foreground": 0,
                    "background": 70,
                },
                "info_display_title": {
                    "foreground": 70,
                    "background": 0,
                },
                "info_display_value": {
                    "foreground": 220,
                    "background": 0,
                },
                "hotkey_display_title": {
                    "foreground": 70,
                    "background": 0,
                },
                "hotkey_display_value": {
                    "foreground": 220,
                    "background": 0,
                },
                "modal_dialog_label_highlight": {
                    "foreground": 70,
                    "background": 0,
                },
                "modal_dialog_label": {
                    "foreground": 220,
                    "background": 0,
                },
                "generic_border": {
                    "foreground": 220,
                    "background": 0,
                },
                "modal_dialog_border": {
                    "foreground": 220,
                    "background": 0,
                },
                "border_title": {
                    "foreground": 111,
                    "background": 0,
                },
                "border_title_info": {
                    "foreground": 70,
                    "background": 0,
                },
                "modal_dialog_border_title": {
                    "foreground": 111,
                    "background": 0,
                },
                "modal_dialog_border_title_info": {
                    "foreground": 70,
                    "background": 0,
                },
                "column_title": {
                    "foreground": 0,
                    "background": 208,
                },
                "message_success": {
                    "foreground": 70,
                    "background": 0,
                },
                "message_info": {
                    "foreground": 33,
                    "background": 0,
                },
                "message_error": {
                    "foreground": 124,
                    "background": 0,
                },
                "error": {
                    "foreground": 124,
                    "background": 0,
                },
                "modal_dialog_error": {
                    "foreground": 124,
                    "background": 0,
                },
                "selection": {
                    "foreground": 0,
                    "background": 220,
                },
                "textfield_label": {
                    "foreground": 220,
                    "background": 0,
                },
                "textfield": {
                    "foreground": 0,
                    "background": 208,
                },
                "textfield_selection": {
                    "foreground": 0,
                    "background": 220,
                },
                "button": {
                    "foreground": 220,
                    "background": 0,
                },
                "button_selection": {
                    "foreground": 0,
                    "background": 220,
                },
                "context_list_generic": {
                    "foreground": 220,
                    "background": 0,
                },
                "context_list_selection": {
                    "foreground": 0,
                    "background": 220,
                },
                "context_list_border": {
                    "foreground": 220,
                    "background": 0,
                },
                "context_list_border_title": {
                    "foreground": 111,
                    "background": 0,
                },
                "context_list_heading": {
                    "foreground": 0,
                    "background": 208,
                },
                "search_bar_border": {
                    "foreground": 220,
                    "background": 0,
                },
                "search_bar_color": {
                    "foreground": 220,
                    "background": 0,
                },
                "search_bar_symbol_color": {
                    "foreground": 70,
                    "background": 0,
                },
                "search_bar_autocomplete_color": {
                    "foreground": 239,
                    "background": 0,
                },
                "search_bar_inactive_color": {
                    "foreground": 239,
                    "background": 0,
                },
                "command_bar_border": {
                    "foreground": 220,
                    "background": 0,
                },
                "command_bar_color": {
                    "foreground": 220,
                    "background": 0,
                },
                "command_bar_symbol_color": {
                    "foreground": 70,
                    "background": 0,
                },
                "command_bar_autocomplete_color": {
                    "foreground": 239,
                    "background": 0,
                },
                "command_bar_ok_color": {
                    "foreground": 33,
                    "background": 0,
                },
                "command_bar_error_color": {
                    "foreground": 124,
                    "background": 0,
                },
                "modal_dialog_textfield": {
                    "foreground": 0,
                    "background": 208,
                },
                "modal_dialog_textfield_selected": {
                    "foreground": 0,
                    "background": 220,
                },
                "modal_dialog_textfield_label": {
                    "foreground": 220,
                    "background": 0,
                },
                "syntax_highlight_token_text": {
                    "foreground": 220,
                    "background": 0,
                },
                "syntax_highlight_token_error": {
                    "foreground": 196,
                    "background": 0,
                },
                "syntax_highlight_token_other": {
                    "foreground": 243,
                    "background": 0,
                },
                "syntax_highlight_token_keyword": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_constant": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_declaration": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_namespace": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_pseudo": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_reserved": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_keyword_type": {
                    "foreground": 183,
                    "background": 0,
                },
                "syntax_highlight_token_literal": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_date": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_affix": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_backtick": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_char": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_delimiter": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_double": {
                    "foreground": 154,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_escape": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_heredoc": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_interpol": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_other": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_regex": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_single": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_string_symbol": {
                    "foreground": 193,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_bin": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_float": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_hex": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_integer": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_integer_long": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_literal_number_oct": {
                    "foreground": 111,
                    "background": 0,
                },
                "syntax_highlight_token_operator": {
                    "foreground": 93,
                    "background": 0,
                },
                "syntax_highlight_token_operator_word": {
                    "foreground": 93,
                    "background": 0,
                },
                "syntax_highlight_token_punctuation": {
                    "foreground": 15,
                    "background": 0,
                },
                "syntax_highlight_token_punctuation_marker": {
                    "foreground": 15,
                    "background": 0,
                },
                "syntax_highlight_token_name": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_tag": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_attribute": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_builtin": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_builtin_pseudo": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_class": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_constant": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_decorator": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_entity": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_exception": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_function": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_function_magic": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_label": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_namespace": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_other": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_variable": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_variable_class": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_variable_global": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_variable_instance": {
                    "foreground": 64,
                    "background": 0,
                },
                "syntax_highlight_token_name_variable_magic": {
                    "foreground": 64,
                    "background": 0,
                },
            },
            "borders": {
                "default": {
                    "horizontal": "─",
                    "vertical": "│",
                    "TL": "┌",
                    "TR": "┐",
                    "BL": "└",
                    "BR": "┘",
                },
                "search_bar": {
                    "horizontal": "─",
                    "vertical": "│",
                    "TL": "┌",
                    "TR": "┐",
                    "BL": "└",
                    "BR": "┘",
                },
                "modal": {
                    "horizontal": "─",
                    "vertical": "│",
                    "TL": "┌",
                    "TR": "┐",
                    "BL": "└",
                    "BR": "┘",
                },
                "resource_list": {
                    "horizontal": "─",
                    "vertical": "│",
                    "TL": "┌",
                    "TR": "┐",
                    "BL": "└",
                    "BR": "┘",
                },
            },
        }

        with self.style_file.open("w") as f:
            f.write(yaml.dump(self.style))

    def __getitem__(self, item):
        return self.style[item]

    def parse_config(self):
        with self.style_file.open("r") as f:
            self.style = yaml.safe_load(f.read())
