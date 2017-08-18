Functionality
=============

Hatter is CI tool with emphasis on simple workflow based on virtual machine
work executors. In contrast to most other CI tools, Hatter doesn't have
specialized executors that need to be installed on machines that execute
user defined commands. Each executor is generic VM with SSH daemon which
is used for file transfer and execution of user defined commands. Therefore,
Hatter is implemented as single daemon that orchestrates VMs lifecycle and
remote command execution.


Server
------

Hatter server daemon provides project execution orchestrator facility with
web-based administration interface. It is configured with single YAML
configuration defined by :ref:`JSON Schema <server-configuration>`. Single
server instance can support automation of multiple projects.


Project
-------

Hatter project is represented by single git repository containing project
configuration file - `.hatter.yml`. Configuration file is defined by
:ref:`JSON Schema <project-configuration>`. This configuration can define
multiple execution environments with appropriate execution commands.


Execution environment
---------------------
