Hatter
======

Hatter is continuous integration server/executor. It provides isolated
execution environments, for running automated actions, as containers managed
by podman.

Key features:

    * automated projects based on git repositories
    * containers as execution runners
    * per project configuration as YAML file inside project's repository
    * web based control and monitoring interface (without JavaScript)
    * webhook/periodic execution triggering
    * CLI executor


Runtime requirements
--------------------

* python >=3.8
* git
* podman


Install
-------

::

    $ pip install hatter


Running
-------

Hatter enables execution of actions described by simple YAML files which
contain container image name and Posix shell execution script. Actions files
are stored as part of git repositories (default name of action file is
`.hatter.yaml`, stored in root of git working tree).

These actions can be executed with::

    $ hatter execute <path>

where ``<path>`` is path to git repository containing action definition.
Referenced git repository can be local or remote.

Additionally, hatter can be run as daemon providing web server interface::

    $ hatter server

When run as server, hatter periodically lists configured git repository
references, and schedules action executions if new commits are available.
New commit checking can also be triggered by webhooks available at listening
`/repo/<repo_name>/webhook` URL path (``<repo_name>`` is configured repository
name).

Hatter server provides basic web GUI which can be used for monitoring
action executions and scheduling new executions based on user provided
git reference.

Action and server configurations are defined and documented by JSON schemas
`schemas_json/action.yaml`_ and `schemas_json/server.yaml`_.

For additional options, see::

    $ hatter --help


Configuration example
---------------------

* `.hatter.yaml`

    ::

        image: alpine
        command: |
            echo "hello $WHO"

* `server.yaml`

    ::

        repos:
            example:
                url: path/to/example/repository
                env:
                    WHO: world


Build
-----

Build tool used for Hatter is pydoit (`<http://pydoit.org>`_). It can be
installed together with other python dependencies by running::

    $ pip install -r requirements.pip.dev.txt

For listing available doit tasks, use::

    $ doit list

Default task::

    $ doit

creates `build` folder containing Hatter distribution.


License
-------

hatter - continuous integration server/executor
Copyright (C) 2017-2022  Bozo Kopic

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
