"""
Module for working with ARNs (Amazon Resource Names).
"""


class ARN:
    """
    Represents an Amazon Resource Name.

    Attributes
    ----------
    partition : str
        The partition of the ARN.
    service : str
        The AWS service identified by the ARN.
    region : str
        The region of the resource identified by ARN, if applicable.
    account_id : str
        The AWS account the resource belongs to, if applicable.
    resource_type : str
        The resource type of the resource, if present in the ARN.
    resource_id : str
        The ID of the resource identified by the ARN.
    """

    def __init__(self, string):
        """
        Initializes an ARN object from an existing ARN string.

        Parameters
        ----------
        string : str
            The ARN string to initialize this object from.
        """
        parts = string.split(":")
        if len(parts) < 6:
            raise ValueError(
                "ARN does not contain enough components for full identification"
            )
        self.partition = parts[1] if parts[1] != "" else "aws"
        if parts[2] == "":
            raise ValueError("ARN is missing service identifier.")
        self.service = parts[2]
        self.region = parts[3]
        self.account_id = parts[4]
        if len(parts) == 6:
            test = parts[5].split("/")
            if len(test) > 1:
                self.resource_type = test[0]
                self.resource_id = "/".join(test[1:])
            else:
                self.resource_id = parts[5]
                self.resource_type = ""
        else:
            self.resource_type = parts[5]
            self.resource_id = ":".join(parts[6:])

    @property
    def resource(self):
        """
        Returns the resource portion of the ARN.

        If the resource type is present in the ARN, the full resource section including the type will be returned.

        Returns
        -------
        str
            The full resource section of the ARN.
        """
        if self.resource_type != "":
            return f"{self.resource_type}/{self.resource_id}"
        return self.resource_id

    @property
    def resource_id_first(self):
        """
        Returns the first resource identifier in the ARN.

        In some cases, the ARN may contain multiple resource IDs separated by slashes. This property is useful
        if only the first ID is required.

        Returns
        -------
        str
            The resource ID until the first slash encountered in the string.
        """
        return self.resource_id.split("/")[0]

    def __str__(self):
        """
        Converts the ARN object into an ARN string.

        Returns
        -------
        str
            The string representation of the ARN.
        """
        return f"arn:{self.partition}:{self.service}:{self.region}:{self.account_id}:{self.resource}"
