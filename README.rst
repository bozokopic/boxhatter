Hatter
======

Hatter is continuous integration server/executor. It provides isolated
execution environments, for running automated actions, as containers managed
by podman.

Key features:

    * automated projects based on git repositories
    * containers as execution runners
    * per project configuration as YAML file inside project's repository
    * web based control and monitoring interface
    * webhook/periodic execution triggering
    * CLI executor


Runtime requirements
--------------------

* python >=3.8
* podman

Additional required python packages are listed in
`requirements.pip.runtime.txt`.


Running
-------


Server
''''''


CLI executor
''''''''''''


Configuration
-------------


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
