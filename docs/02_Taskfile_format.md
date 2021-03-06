# Taskfile format

The `Taskfile` is in general a normal bash script which will be loaded by b5 using the bash `source` command.
Because of this you may use anything you are already using when writing your bash scripts.

For defining tasks you will need to add functions following the `task:name`-schema. See below.

## Basic details

* All tasks are simple bash functions prefixed with `task:`
* Every task may use as many arguments as necessary ($1, $2, …)
* Please care about your arguments and use them correctly (for example $1 -> "${1}" or even "${1:-}")
* If you call multiple shell commands please make sure your function fails after one of these
  commands failed, as least inside subshells (`(command1 && command2 && …)`)

## Example

```bash
#!/usr/bin/env bash
# b5 Taskfile, see https://git.team23.de/build/b5 for details

task:css() {
    sassc input.scss output.css
}

task:install() {
    npm install
    virtualenv ../ENV
    (
        # using subshell here as source may change the outer bash context
        source ../ENV/bin/activate
        pip install -U -r requirements.txt
    )
}

task:deploy() {
    if [ -z "${1:-}" ]
    then
        echo "Please specify deployment target. ABORTING!"
        exit 1
    fi
    fab "${1}" "deploy:${2:-}"
}
```

**Note:** The Taskfile is always executed inside the "run-path", which defaults to `build/`. Make
sure to switch path, when necessary. I recommend using a subshell (see
["( … )" subshell syntax](http://www.gnu.org/software/bash/manual/html_node/Command-Grouping.html)) when
doing so.

## About Taskfile quality

We use the following bash setting to make sure all Taskfiles follow a common quality standard:

* `set -o nounset`: Variables that are not set will throw an error. Make sure to handle `$1` correctly, as
  parameters may not be passed. Use `${1:-}` if necessary.
* `set -o errexit`/`set -o errtrace`/`set -o pipefail`: Programs that fail execution (exit code != 0) will
  trigger b5 to abort the whole task and display an error. This means if you have commands that may fail
  use `command || true` to prevent b5 from stopping the execution. Please also note that subshells will
  need special treatment (subshell: `( command1; command2 )`) as these settings are not passed down. You
  may need to use `( command1 && command2 )` or similar.

## Taskfile locations

By default b5 will look for your Taskfile at these locations in this order:
* ~/.b5/Taskfile (for personal global tasks)
* build/Taskfile (`{run-path}/Taskfile`)
* build/Taskfile.local (`{run-path}/Taskfile.local`)

All Taskfile's found will be loaded before task execution.
