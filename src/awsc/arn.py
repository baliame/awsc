class ARN:
    def __init__(self, s):
        parts = s.split(":")
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
        if self.resource_type != "":
            return "{0}/{1}".format(self.resource_type, self.resource_id)
        return self.resource_id

    @property
    def resource_id_first(self):
        return self.resource_id.split("/")[0]

    def __str__(self):
        return "arn:{0}:{1}:{2}:{3}:{4}".format(
            self.partition, self.service, self.region, self.account_id, self.resource
        )
