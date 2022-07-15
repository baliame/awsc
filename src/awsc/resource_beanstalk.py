from .base_control import Describer, ResourceLister


class EBApplicationResourceLister(ResourceLister):
    prefix = "eb_application_list"
    title = "Beanstalk Applications"
    command_palette = ["ebapplication", "ebapp", "elasticbeanstalkapplication"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_applications"
        self.item_path = ".Applications"
        self.column_paths = {
            "name": ".ApplicationName",
            "description": ".Description",
        }
        self.imported_column_sizes = {
            "name": 20,
            "description": 50,
        }
        self.hidden_columns = {
            "arn": ".ApplicationArn",
        }
        self.describe_command = EBApplicationDescriber.opener
        self.open_command = EBEnvironmentLister.opener
        self.open_selection_arg = "app"

        self.imported_column_order = ["name", "description"]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)


class EBApplicationDescriber(Describer):
    prefix = "eb_application_browser"
    title = "Beanstalk Application"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="name", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_applications"
        self.describe_kwarg_name = "ApplicationNames"
        self.describe_kwarg_is_list = True
        self.object_path = ".Applications[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )


class EBEnvironmentLister(ResourceLister):
    prefix = "eb_environment_list"
    title = "Beanstalk Environments"
    command_palette = ["ebenvironment", "ebenv", "elasticbeanstalkenvironment"]

    def __init__(self, *args, **kwargs):
        self.resource_key = "elasticbeanstalk"
        self.list_method = "describe_environments"
        self.item_path = ".Environments"
        if "app" in kwargs:
            self.app = kwargs["app"]
            self.list_kwargs = {"ApplicationName": self.app}
        else:
            self.app = None
        self.column_paths = {
            "name": ".EnvironmentName",
            "id": ".EnvironmentId",
            "application": ".ApplicationName",
            "status": ".Status",
            "health": ".Health",
            "tier": ".Tier.Name",
        }
        self.imported_column_sizes = {
            "name": 20,
            "id": 20,
            "application": 20,
            "status": 15,
            "health": 7,
            "tier": 10,
        }
        self.hidden_columns = {
            "arn": ".EnvironmentArn",
        }
        self.describe_command = EBEnvironmentDescriber.opener
        # self.open_command = EBEnvironmentLister.opener
        # self.open_selection_arg = 'lb'

        self.imported_column_order = [
            "name",
            "id",
            "tier",
            "status",
            "health",
            "application",
        ]
        self.sort_column = "name"
        self.primary_key = "name"
        super().__init__(*args, **kwargs)

    def title_info(self):
        return self.app


class EBEnvironmentDescriber(Describer):
    prefix = "eb_environment_browser"
    title = "Beanstalk Environment"

    def __init__(
        self, parent, alignment, dimensions, entry, *args, entry_key="id", **kwargs
    ):
        self.resource_key = "elasticbeanstalk"
        self.describe_method = "describe_environments"
        self.describe_kwarg_name = "EnvironmentIds"
        self.describe_kwarg_is_list = True
        self.object_path = ".Environments[0]"
        super().__init__(
            parent,
            alignment,
            dimensions,
            *args,
            entry=entry,
            entry_key=entry_key,
            **kwargs
        )
