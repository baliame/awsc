# 0.3.2

* Fix EC2 launch dialog
* Fix ELB describe view

# 0.3.1

## User changes

* Removed an entire fleet of debug prints I left in the code. Sorry.

# 0.3.0

## Developer changes

* Broke up resources.py to smaller modules, using on-demand imports for openers.
* Move command palette registration logic from main to individual lister classes.

## User changes

* Added JSON syntax highlighting to describe actions
* Added ability to use EC2 Instance Connect for SSH.
  * No actual checks are done if it's available on an instance.
  * Makes a best effort to use the API and abort SSHing if it fails to do so for any reason.
* Now automatically imports `~/.aws/credentials` on startup
  * Does not currently import `~/.aws/config` but it is planned
  * Note that import will happen on every startup for convenience
  * Name of imported context will be the same as the name of the context in the credentials file
  * **This will overwrite any existing context with the same name mercilessly**, but I see no compelling argument not to.
  * Account ID field is automatically determined via an STS call. Any context which fails this STS call will not be imported.
* Secret key field on add context dialog is now masked as a password.

# 0.2.0

## User changes

* Allows viewing EC2 instance metrics using BarGraph control. Hotkey: m.
* Stop instance command is instead a toggle now - can be used to start stopped instances.
* Ability to manually scale autoscaling groups.
* EBS volume resource
* Fixed automatic refreshing of resource lists in dialog mode.
* Added related resource view for EC2 instances

## Developer changes

* Checkbox for dialogs.
* Implemented BarGraph control.
* Better generalization of session-aware dialogs.
* Refactored Describer class to have less duplicate code. In another pass, we'll just make resource listers generate these instead.
* SingleRelationLister, for parsing ids out of a single describe() call and listing them.

# 0.1.0

* Initial release