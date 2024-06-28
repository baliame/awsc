"""
Mdoule for controls related to load balanching.
"""

from .base_control import Describer, ResourceLister, boolean_determiner_generator


class R53DomainDescriber(Describer):
    """
    Describer control for v2 load balancers.
    """

    prefix = "r53d_domain_browser"
    title = "Route53 Domain"

    resource_type = "route53 domain"
    main_provider = "route53domains"
    category = "Route53Domains"
    subcategory = "Domains"
    describe_method = "get_domain_detail"
    describe_kwarg_name = "DomainName"
    object_path = "."


class R53DomainResourceLister(ResourceLister):
    """
    Lister control for v2 load balancers.
    """

    prefix = "r53d_domain_list"
    title = "Route53 Domains"
    command_palette = ["r53d", "domain", "registrar"]

    resource_type = "route53 domain"
    main_provider = "route53domains"
    category = "Route53 Domains"
    subcategory = "Domains"
    list_method = "list_domains"
    item_path = ".Domains"
    columns = {
        "name": {
            "path": ".DomainName",
            "size": 40,
            "weight": 0,
            "sort_weight": 0,
        },
        "autorenew": {
            "path": boolean_determiner_generator("AutoRenew"),
            "size": 10,
            "weight": 1,
        },
        "locked": {
            "path": boolean_determiner_generator("TransferLock"),
            "size": 10,
            "weight": 2,
        },
        "expiry": {"path": ".Expiry", "size": 15, "weight": 3},
    }
    describe_command = R53DomainDescriber.opener
