import json
import time
import webbrowser

from botocore import exceptions as botoerror

from .base_control import DeleteResourceDialog, DialogFieldResourceListSelector, GenericDescriber, OpenableListControl
from .common import Common, SessionAwareDialog, datetime_hack
from .context import _context_color_defaults
from .termui.control import Border
from .termui.dialog import DialogFieldLabel, DialogFieldText
from .termui.list_control import ListEntry
from .termui.ui import ControlCodes


class AddSSODialog(SessionAwareDialog):
    """
    Dialog control for adding a new SSO.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the SSO.
    sso_id_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the SSO ID.
    """

    line_size = 20

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        existing_sso=None,
        **kwargs,
    ):
        from .resource_iam_user import MFADeviceLister

        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            f"{'New' if existing_sso is None else 'Edit'} SSO",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.editing = existing_sso
        self.set_title_label("Enter AWS SSO details")
        self.name_field = (
            DialogFieldText(
                "Name:",
                label_min=16,
                **_context_color_defaults(),
            )
            if existing_sso is None
            else DialogFieldLabel(
                [
                    ("Name: ", Common.color("generic")),
                    (existing_sso, Common.color("highlight")),
                ],
                centered=False,
            )
        )
        self.add_field(self.name_field)
        self.sso_id_field = DialogFieldText(
            "SSO ID (subdomain):",
            text="" if existing_sso is None else existing_sso,
            label_min=16,
            **_context_color_defaults(),
        )
        self.add_field(self.sso_id_field)
        self.caller = caller

    def input(self, key):
        if not self.accepts_inputs:
            return True
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def accept_and_close(self):
        if self.editing is None:
            if self.name_field.text == "":
                self.error_label.text = "Name cannot be blank."
                return
        if self.sso_id_field.text == "":
            self.error_label.text = "SSO ID cannot be blank."
            return

        self.accepts_inputs = False

        Common.Configuration.add_or_edit_sso(
            self.name_field.text if self.editing is None else self.editing,
            self.sso_id_field.text,
        )
        self.close()

    def close(self):
        if self.caller is not None:
            self.caller.reload_ssos()
        super().close()


class SSOAccountLister(OpenableListControl):
    """
    Lister control for SSO login.
    """

    prefix = "sso_role_list"
    title = "SSO Roles"
    override_enter = True

    def __init__(self, *args, sso_dialog, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_column("account name", 20)

        if len(sso_dialog.account_cache):
            for k, v in sso_dialog.account_cache.items():
                self.add_entry(ListEntry(k, **{"account name": v}))
            return

        try:
            accts = sso_dialog.sso.list_accounts(accessToken=sso_dialog.tok['access'], maxResults=200)
        except:
            Common.Session.set_message("SSO security token expired during session, reauthentication is required, workflow.", Common.color("message_error"))
            sso_dialog.close()
            self.rejected = True
            return
        for account in accts['accountList']:
            k = account['accountId']
            v = account['accountName']
            sso_dialog.account_cache[k] = v
            self.add_entry(ListEntry(k, **{"account name": v}))
        #    roles = sso_dialog.sso.list_account_roles(accessToken=sso_dialog.token['accessToken'], accountId=account['accountId'], maxResults=200)
        #    for role in roles['roleList']:
        #        key=f'{account['accountId']}::{role['roleName']}'
        #        v = {'accountId': account['accountId'], 'accountName': account['accountName'], 'roleName': role['roleName']}
        #        sso_dialog.account_cache[key] = v
        #        self.add_entry(ListEntry(key, **{"account id": v['accountId'], "account name": v['accountName'], "role name": v['roleName']}))


class SSORoleLister(OpenableListControl):
    """
    Lister control for SSO login.
    """

    prefix = "sso_role_list"
    title = "SSO Roles"
    override_enter = True

    def __init__(self, *args, sso_dialog, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_column("account id", 12)
        self.add_column("account name", 20)
        self.add_column("role name", 20)
        account_id = sso_dialog.account_selector_field.value

        if account_id in sso_dialog.role_cache and len(sso_dialog.role_cache[account_id]):
            for k, v in sso_dialog.role_cache[account_id].items():
                self.add_entry(ListEntry(k, **{"account id": account_id, "account name": sso_dialog.account_cache[account_id], "role name": v}))
            return

        if account_id not in sso_dialog.role_cache:
            sso_dialog.role_cache[account_id] = {}

        roles = sso_dialog.sso.list_account_roles(accessToken=sso_dialog.tok['access'], accountId=account_id, maxResults=200)
        for role in roles['roleList']:
            v = role['roleName']
            k = f'{account_id}::{v}'
            
            sso_dialog.role_cache[account_id][k] = v
            self.add_entry(ListEntry(k, **{"account id": account_id, "account name": sso_dialog.account_cache[account_id], "role name": v}))

class RunSSODialog(SessionAwareDialog):
    """
    Dialog control for connecting to an SSO.

    Attributes
    ----------
    caller : awsc.termui.control.Control
        Parent control which controls this dialog.
    error_label : awsc.termui.dialog.DialogFieldLabel
        Error label for displaying validation errors.
    name_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the name of the SSO.
    sso_id_field : awsc.termui.dialog.DialogFieldText
        Textfield for entering the SSO ID.
    """

    line_size = 20

    def find_oidc_client(self):
        oidc_client = Common.Configuration.keystore.get_sso_client(self.sso_id)
        if oidc_client is None or oidc_client['clientSecretExpiresAt'] < time.time():
            Common.log(f"{'oidc_client does not exist' if oidc_client is None else f"oidc_client expired at {oidc_client['clientSecretExpiresAt'] }, current time {time.time()}"}, requesting new oidc_client", "New OIDC client request", "SSO", "info", "OIDC", set_message=False)
            try:
                oidc_client = self.oidc.register_client(clientName="AWSC - AWS Commander", clientType='public')
            except botoerror.BotoCoreError as e:
                self.reject_dialog = True
                Common.Session.set_message(f"Error starting SSO flow: {e}", Common.color("message_error"))
                return
            Common.Configuration.keystore.set_sso_client(self.sso_id, oidc_client)
        else:
            Common.log(f"using existing OIDC client {oidc_client['clientId']} (expires at {oidc_client['clientSecretExpiresAt']}, current time {time.time()})", "OIDC client found", "SSO", "info", "OIDC", set_message=False)
        self.creds = oidc_client

    def __init__(
        self,
        parent,
        alignment,
        dimensions,
        *args,
        caller=None,
        existing_sso=None,
        **kwargs,
    ):
        from .resource_iam_user import MFADeviceLister

        self.reject_dialog = False
        self.accepts_inputs = True
        kwargs["border"] = Border(
            Common.border("default"),
            Common.color("modal_dialog_border"),
            "Connecting to AWS via SSO",
            Common.color("modal_dialog_border_title"),
        )
        kwargs["ok_action"] = self.accept_and_close
        kwargs["cancel_action"] = self.close

        self.sso_id = Common.Configuration['sso'][existing_sso]['sso_id']

        aws = Common.Session.service_provider
        session = aws.env_session()
        self.sso = session.client('sso')
        self.oidc = session.client('sso-oidc')

        tok = Common.Configuration.keystore.get_ephemeral_device_token(self.sso_id)

        self.status_label = DialogFieldLabel(
            [
                ("Status: ", Common.color("generic")),
                (f"Awaiting web browser authorization | Polled 0 time(s)", Common.color("highlight")),
            ],
            centered=False,
        )

        self.code_label = DialogFieldLabel("", centered=False)

        self.account_selector_field = None
        self.role_selector_field = None

        if tok is not None and tok['expiry'] > time.time():
            try:
                self.sso.list_accounts(accessToken=tok['access'], maxResults=5)
            except Exception as e:
                tok = None

        if tok is None:
            self.polling_attempts = 0

            self.find_oidc_client()

            try:
                self.device_auth = self.oidc.start_device_authorization(clientId=self.creds['clientId'], clientSecret=self.creds['clientSecret'], startUrl=f"https://{self.sso_id}.awsapps.com/start")
            except botoerror.BotoCoreError as e:
                self.reject_dialog = True
                Common.Session.set_message(f"Error starting SSO flow: {e}", Common.color("message_error"))
                return
            self.auth_start = time.time()

            self.code_label = DialogFieldLabel(
                [
                    ("Authorization code for this device: ", Common.color("generic")),
                    (self.device_auth['userCode'], Common.color("highlight")),
                ],
                centered=False,
            )

            self.next_check = self.auth_start + self.device_auth['interval']
            auth_url = self.device_auth['verificationUriComplete']
            self.is_authorized = False
            webbrowser.open(auth_url, autoraise=True)
            Common.Session.ui.tickers.append(self.await_session)
            self.caller = caller
            self.tok = None
        elif tok['expiry'] < time.time() and tok['refresh'] is not None:
            self.find_oidc_client()
            try:
                token = self.oidc.create_token(
                    grantType='refreshToken',
                    refreshToken=tok['refresh'],
                    clientId=self.creds['clientId'],
                    clientSecret=self.creds['clientSecret'],
                )
            except e:
                Common.Session.set_message(f"Token refresh failed: {e}", Common.color('message_error'))
                self.reject_dialog = True
                Common.Configuration.keystore.clear_ephemeral_device_token(self.sso_id)
                return
            Common.Configuration.keystore.set_ephemeral_device_token(self.sso_id, token['accessToken'], time.time() + token['expiresIn'], token['refreshToken']) 
            self.tok = Common.Configuration.keystore.get_ephemeral_device_token(self.sso_id)
            self.is_authorized = True
        else:
            self.status_label.modify_segment(1, f"Already authorized")

            self.tok = tok
            self.is_authorized = True
        
        super().__init__(parent, alignment, dimensions, caller=caller, *args, **kwargs)
        self.set_title_label("Connecting to AWS via SSO")
        self.add_field(self.status_label, 1)
        self.add_field(self.code_label, 2)
        if self.is_authorized:
            self.got_session()

    def input(self, key):
        if not self.accepts_inputs:
            return True
        if key.is_sequence and key.name == "KEY_ESCAPE":
            self.close()
            return True
        return super().input(key)

    def account_list_return(self, *args):
        self.role_selector_field.disabled = False

    def got_session(self, *args):
        self.account_selector_field = DialogFieldResourceListSelector(
            SSOAccountLister,
            "Account:",
            default="",
            label_min=16,
            **_context_color_defaults(),
            selector_cb_callable=self.account_list_return,
            additional_kwa={"sso_dialog": self}
        )
    
        self.add_field(self.account_selector_field)

        self.role_selector_field = DialogFieldResourceListSelector(
            SSORoleLister,
            "Role:",
            default="",
            label_min=16,
            **_context_color_defaults(),
            disabled=True,
            additional_kwa={"sso_dialog": self}
        )
    
        self.add_field(self.role_selector_field)
        self.account_cache = {}
        self.role_cache = {}
        Common.Session.ui.dirty = True

    def await_session(self, *args):
        ct = time.time()
        if ct > self.auth_start + self.device_auth['expiresIn']:
            Common.Session.set_message(f"Verification flow expired.")
            self.close()
            return
        if self.next_check < ct:
            self.next_check = ct + self.device_auth['interval'] + 1
            try:
                token = self.oidc.create_token(
                    grantType='urn:ietf:params:oauth:grant-type:device_code',
                    deviceCode=self.device_auth['deviceCode'],
                    clientId=self.creds['clientId'],
                    clientSecret=self.creds['clientSecret'],
                )
            except self.oidc.exceptions.AuthorizationPendingException:
                self.polling_attempts += 1
                self.status_label.modify_segment(1, f"Awaiting web browser authorization | Polled {self.polling_attempts} time(s)")
                return
            Common.Configuration.keystore.set_ephemeral_device_token(self.sso_id, token['accessToken'], time.time() + token['expiresIn'], token['refreshToken'] if 'refreshToken' in token else None)
            Common.log(json.dumps(token), 'Debug', 'Debug', 'debug', 'Debug', set_message=False)
            self.tok = Common.Configuration.keystore.get_ephemeral_device_token(self.sso_id)

            self.is_authorized = True

            try:
                Common.Session.ui.tickers.remove(self.await_session)
            except ValueError as e:
                pass

            self.got_session()

    def accept_and_close(self):
        if not self.is_authorized:
            self.error_label.text = "Cannot accept dialog while authorization is in progress."
            return
    
        if self.account_selector_field.value not in self.account_cache:
            self.error_label.text = "Select a valid account to continue."
            return

        if self.role_selector_field is None or self.role_selector_field.value not in self.role_cache[self.account_selector_field.value]:
            self.error_label.text = "Select a valid role to continue."
            return
        
        self.accepts_inputs = False

        role_context = self.role_selector_field.value
        account = self.account_selector_field.value
        role = self.role_cache[account][role_context]
        role_creds = self.sso.get_role_credentials(roleName=role, accountId=account, accessToken=self.tok['access'])['roleCredentials']
        Common.Configuration.add_or_edit_ephemeral_context(role_context, account, role_creds['accessKeyId'], role_creds['secretAccessKey'], role_creds['sessionToken'], expires_at=role_creds['expiration'] / 1000)
        Common.Session.context = role_context
        Common.Session.set_message(f"Assumed role {role} in account {account} via SSO. ", Common.color('message_success'))

        self.close()

    def close(self):
        try:
            Common.Session.ui.tickers.remove(self.await_session)
        except ValueError as e:
            pass
        super().close()


class SSODescriber(GenericDescriber):
    def __init__(self, *args, selection, **kwargs):
        sso = selection["name"]
        data = Common.Session.retrieve_sso(sso)
        content = json.dumps(data, default=datetime_hack, indent=2, sort_keys=True)
        super().__init__(
            *args,
            describing="sso",
            content=content,
            **kwargs,
        )


class SSOList(OpenableListControl):
    """
    Lister control for SSO login.
    """

    prefix = "sso_list"
    title = "SSO Logins"
    describer = SSODescriber.opener
    override_enter = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_column("sso id", 12)
        self.reload_ssos()

    def reload_ssos(self):
        """
        Refreshes the list of SSOs from configuration.
        """
        self.entries = []
        for name, sso in Common.Configuration['sso'].items():
            self.add_entry(ListEntry(name, **{"sso id": sso['sso_id']}))

    @OpenableListControl.Autohotkey("a", "Add SSO")
    def add_new_sso(self, _):
        """
        Hotkey callback for adding a new SSO.
        """
        AddSSODialog.opener(caller=self)

    @OpenableListControl.Autohotkey("e", "Edit SSO", True)
    def edit_sso(self, _):
        """
        Hotkey callback for editing an SSO.
        """
        AddSSODialog.opener(
            caller=self, existing_sso=self.selection["name"]
        )

    def on_become_frame(self):
        super().on_become_frame()
        self.on_become_frame_hooks.clear()

    @OpenableListControl.Autohotkey("KEY_ENTER", "Login and select role", True)
    def select_sso(self, _, initial=False):
        """
        Hotkey callback for executing SSO login.
        """
        RunSSODialog.opener(caller=self, existing_sso=self.selection["name"])

    @OpenableListControl.Autohotkey(ControlCodes.D, "Delete SSO", True)
    def delete_selected_sso(self, _):
        """
        Hotkey callback for deleting the selected SSO.
        """
        DeleteResourceDialog.opener(
            caller=self,
            resource_type="sso",
            resource_identifier=self.selection["name"],
            callback=self.do_delete,
        )

    def do_delete(self, **kwargs):
        """
        Action callback for the SSO deletion dialog.
        """
        Common.Configuration.delete_sso(self.selection["name"])
        self.reload_ssos()

        