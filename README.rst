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
* libvirt

Additional required python packages are listed in `requirements.pip.run.txt`.


Development requirements
------------------------

* nodejs >=7
* yarn

Additional required python packages are listed in `requirements.pip.dev.txt`.


Source
------

Source code available at `<https://github.com/bozokopic/hatter>`_.


Documentation
-------------

Online documentation available at `<http://hatter.readthedocs.io>`_.


Build
-----

Build tool used for Hatter is pydoit (`<http://pydoit.org>`_). It can be
installed together with other python dependencies by running::

    $ pip install -r requirements.pip.dev.txt

For listing available doit tasks, use::

    $ doit list

Default task::

    $ doit

creates `dist` folder containing Hatter distribution.


TODO
----

* user interface - frontend

    * create user interface

* other

    * test functionality
    * write complete setup.py
    * distribution
