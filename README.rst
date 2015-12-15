etcdwatch
=========

**WARNING** This is alpha quality software at this point. I have so
far used it only in limited settings so it is possible that changes to
command line options, behavior etc. may occur before I consider it
stable enough to be non-alpha.

Etcdwatch is a simple program that does three things:

1. It tracks current state of a given etcd server/cluster.
2. It serializes each state into JSON, YAML or other format.
3. It gives each state as a standard input for a specified program.

In reality it's a bit more complex, but that's what you are buying.

Try this. First, start etcd if it's not yet running::

    $ etcd

then start etcdwatch::

    $ etcdwatch -- sh -c 'cat; echo'

and do some changes in the registry::

    $ curl -s http://127.0.0.1:2379/v2/keys/test -XPUT -d value=something
    $ curl -s http://127.0.0.1:2379/v2/keys/test2 -XPUT -d value=other
    $ curl -s http://127.0.0.1:2379/v2/keys/test -XDELETE
    $ curl -s http://127.0.0.1:2379/v2/keys/test2 -XDELETE

Watch what happens.

Setup
-----

Simply::

    $ python setup.py install

Usage
-----

There are several options that can be used configure stuff like etcd
host, port etc. --- see ``etcdwatch --help``.

Examples
--------

Here's a snippet from a project::

    $ etcdwatch -- sh -c './regenerate.py && nginx -s reload'

The regenerate script reads the input, updates nginx configuration and
reloads the configuration. In this case it is used to handle a devtest
environment where each branch gets deployed to AWS ECS. During
deployment the address and port information of each sub-service gets
updated to etcd which in turn triggers the reverse proxy configuration
to be dynamically updated --- and we have
``**branch**-**service**.dev.some.dns.name`` available instantly!

Caveats
-------

Etcd is **not** a transactional data store. If you use multiple keys
it is possible that some of them are set or updated while others are
not. Thus you should always check whether the input actually makes
*sense* before using it.

Etcdwatch runs the command only on **stable** registry state. This
occurs when, after an update, no more updates have occurred for a
short period of time (a few seconds, configuable via
``--stable-timeout`` option). If you really want every single detected
update (as told by etcd, which again may not be exactly equal to each
update done by a client) to cause the program to be run, use
``--no-stable`` command line option.

License
-------

`MIT License <http://santtu.mit-license.org/>`_ © Santeri Paavolainen
