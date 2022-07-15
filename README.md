# AWSC - AWS Commander

AWSC is a tool inspired by [k9s](https://github.com/derailed/k9s) - the goal is to create a similarly easy to use terminal-based UI for the AWS API.

## Installation

### Requirements

AWSC has been tested with and therefore requires python 3.8 or later.

### Stable releases

AWSC is available on pypi and can be installed via pip.

```bash
$ pip3 install awsc
````

### Edge versions

You can install the latest git revision from the root directory of the repository by issuing:

```bash
$ sudo python3 setup.py install
```

## First use

Through either installation method, the `awsc` binary should become available.

Upon launching AWSC, you are prompted to set an encryption key (password) for your database of access credentials. You will have to enter this encryption key every time you launch AWSC.

You will then be taken to the list of AWS contexts. Your stored contexts from your filesystem (`~/.aws/credentials`) will be imported automatically. Select one of these, or you can either add a new context by pressing `a`.

For navigation, refer to the top right hotkey display on each screen.

### Command palette

The command palette can be accessed by pressing `:`. This allows you to navigate between the different AWS resources. Most resources have short names that are accepted, but the full name of the resource without spaces should also be accepted. For an exhaustive list of commands that are available, type 'help' and press enter.

### Defaults

You can configure a default context, region and ssh key in their relevant screens. These are remembered and automatically set on each launch. Your default SSH key is only used if the keypair for the instance you are accessing does not already have an associated SSH key.

## Version history

Refer to the [changelog](CHANGELOG.md) for release notes on versions.
