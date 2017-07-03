Hatter
======

Hatter is continuous integration server. It provides isolated execution
environments, for running automated actions, as virtual machines managed by
libvirt.

Key features:

    * automated projects based on git repositories
    * virtual machines as execution runners
    * virtual machine snapshots for consistent execution environments
    * per project configuration as YAML file inside project's repository
    * web based control and monitoring interface


Runtime requirements
--------------------

* python >=3.6

Additional required python packages are listed in `requirements.pip.txt`.


Development requirements
------------------------

* nodejs >=7
* yarn


Build
-----

Build tool used for Hatter is pydoit (`http://pydoit.org/`). It can be
installed together with other python dependencies by running::

    $ pip install -r requirements.pip.txt

For listing available doit tasks, use::

    $ doit list

Default task::

    $ doit

creates `dist` folder containing Hatter distribution.


TODO
----

* automation executor

    * implement retrieval of git repositories and communication with VM guest
    * implement execution of automated tasks provided by YAML configuration
    * add logging facility for monitoring execution process

* web server - backend

    * define basic structure for SQLite database
    * provide web hooks for incomming push notifications (support Github and
      Gitlab events)
    * orchestrate automation executor
    * JSON Schema describing messages used in communication between backend and
      frontend
    * implement functionality provided by internal communication protocol

* user interface - frontend

    * implement communication with backend
    * create user interface

* other

    * documentation
    * write complete setup.py
    * distribution
