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