# -*- coding: utf-8 -*-
#
# Copyright © 2015 Santeri Paavolainen <santtu@iki.fi>
#
# Licensed under the MIT License --- see LICENSE file in the source
# directory for details.
#

import argparse
import etcd
import yaml
import pickle
import io
import json
import subprocess
import tempfile
import logging
import urllib3.exceptions
import time
try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse


# TODO: maybe as_dict_index should return also a flag for
# "inconsistency" which would trigger a full re-read? Of course that
# should never happen if this routine worked correctly, but ...
def as_dict_index(node, data={}):
    index = 0

    def set(k, v):
        p = data
        ks = k.split('/')
        for pe in ks[1:-1]:
            p = p.setdefault(pe, {})
        p[ks[-1]] = v

    def delete(k):
        p = data
        ks = k.split('/')
        for pe in ks[1:-1]:
            p = p.setdefault(pe, {})

        if ks[-1] in p:
            del p[ks[-1]]

    for child in node.children:
        if child.modifiedIndex is not None:
            index = max(index, child.modifiedIndex)

        if child.action == 'delete':
            delete(child.key)

        elif not child.dir:
            set(child.key, child.value)

    return data, index


def track(client,
          path="/", start_index=0, recursive=True, stable_timeout=1):
    """This is a generator that returns `data, index` tuples where `data`
    is the current state and `index` is the index of that data. The
    generator runs empty if the connection to the etcd server is lost.
    """

    log = logging.getLogger('etcdwatch.track')

    index = start_index
    wait = False
    data = {}

    log.debug("Initial state: index=%r, wait=%r, data=%r, recursive=%r",
              index, wait, data, recursive)

    while True:
        stable = False
        timeout = 0

        # We always wait for a "stable" state. This is defined simply
        # as not getting new updates for a short period of time.
        #
        # We keep iterating a read-merge loop until two things occur:
        # at least one read is successful (we got an update), and the
        # last read timeouted.

        timeout = 30
        updated = False

        log.debug("Entering read loop, timeout=%r, index=%r",
                  timeout, index)

        while not stable:
            try:
                result = client.read(
                    path,
                    recursive=recursive,
                    wait=wait,
                    waitIndex=index + 1 if index is not None else None,
                    timeout=timeout)

                data, index = as_dict_index(result, data)
                updated = True
                log.debug("Updated, got result: %r", result)
            except etcd.EtcdKeyNotFound:
                time.sleep(5)
            except etcd.EtcdConnectionFailed as ex:
                stable = updated
                log.debug("Timeout (inner %r)", ex.cause.__class__)

                if isinstance(ex.cause, urllib3.exceptions.MaxRetryError):
                    log.exception("Could not connect")
                    return

                if not isinstance(
                        ex.cause,
                        (urllib3.exceptions.ReadTimeoutError,)):
                    log.exception("Uncategorized secondary exception")

            if updated:
                if stable_timeout is None:
                    log.debug("No stability timeout set")
                    break

                timeout = stable_timeout

            wait = True

            log.debug("STATE: index=%r, wait=%r, timeout=%r, "
                      "updated=%r, stable=%r",
                      index, wait, timeout, updated, stable)

        log.debug("Stable state reached, index=%r, data: %r",
                  index, data)

        yield data, index


def main():
    logging.basicConfig(level=logging.CRITICAL)
    log = logging.getLogger('etcdwatch')

    parser = argparse.ArgumentParser(
        description=
        """This program connects to an etcd registry and will keep watch on a
        given registry path, spawning a child process when changes
        occur handing the child process the current etcd state in
        standard input in JSON or YAML format.

    """)
    parser.add_argument('script', nargs='+', metavar='SCRIPT')
    parser.add_argument('-H', '--host', default='localhost',
                        help="etcd host (default localhost)")
    parser.add_argument('-p', '--port', type=int, default=4001,
                        help="etcd port (default 4001)")
    parser.add_argument('-u', '--url', type=urlparse,
                        help="etcd host in URL format")
    parser.add_argument(
        '-f', '--format',
        choices=('json', 'yaml', 'pickle'), default='json',
        help="output format (default json)")
    parser.add_argument(
        '-d', '--path', default="/",
        help="etcd registry path or entry to watch (default /)")
    parser.add_argument(
        '--wait-index', type=int, metavar="NUM",
        help="wait index to start from")
    parser.add_argument(
        '-1', '--one-event', default=False,
        action='store_true',
        help="run only once, then exit")
    parser.add_argument(
        '--no-reconnect', default=False, action='store_true',
        help="do not try to reconnect")
    parser.add_argument(
        '--protocol', default='http', choices=('http', 'https'),
        help="protocol used to connect")
    parser.add_argument(
        '--no-recursive', default=False, action='store_true',
        help="do not track all changes recursively from path")
    parser.add_argument(
        '--reconnect-timeout', default=30, type=int,
        help="timeout before trying to reconnect if connection is lost")
    parser.add_argument(
        '--no-stable', default=False, action='store_true',
        help="do not wait for stable state, run script on every change")
    parser.add_argument(
        '--stable-timeout', default=1, type=int,
        metavar="SECS",
        help="time to wait for changes to reach stability (default: 1 second)")
    parser.add_argument('--debug', default=False, action='store_true')

    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)
        #logging.getLogger().setLevel(logging.DEBUG)

    log.debug("Parsed args: %r", args)

    index = args.wait_index

    try:
        while True:
            if args.url:
                host, port_str = args.url.netloc.split(":")
                port = int(port_str)
                client = etcd.Client(host=host, port=port,
                                     protocol=args.url.scheme)
                log.debug("Client %r from URL %r: host=%s port=%s proto=%s",
                          client, args.url, host, port, args.url.scheme)
            else:
                client = etcd.Client(host=args.host,
                                     port=args.port,
                                     protocol=args.protocol)
                log.debug("Client %r from options: host=%s pot=%s proto=%s",
                          client, args.host, args.port, args.protocol)

            log.debug("client: %r", client)

            for data, index in track(
                    client,
                    path=args.path,
                    start_index=index,
                    recursive=not args.no_recursive,
                    stable_timeout=(None if args.no_stable
                                    else args.stable_timeout)):

                log.debug("Tracked index=%r, data: %r", index, data)

                if args.format == 'pickle':
                    out = io.BytesIO()
                    pickle.dump(data, out)
                    out.seek(0)
                    out = out.read()
                elif args.format == 'json':
                    out = json.dumps(data).encode('utf-8')
                elif args.format == 'yaml':
                    out = yaml.dump(data).encode('utf-8')
                else:
                    assert False

                inf = tempfile.TemporaryFile()
                inf.write(out)
                inf.flush()
                inf.seek(0)

                log.debug("Calling %r with stdin=%r", args.script, out)

                ret = subprocess.call(args.script, stdin=inf)

                del inf

                log.debug("Subprocess result: %r", ret)

                if args.one_event:
                    log.debug("Run only once, exiting")
                    break

            log.debug("No more data, client disconnect?")

            if args.no_reconnect:
                break

            log.debug("Sleeping %ds before reconnect...",
                      args.reconnect_timeout)

            time.sleep(args.reconnect_timeout)
    except KeyboardInterrupt:
        pass
