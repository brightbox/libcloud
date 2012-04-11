# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
from libcloud.utils.py3 import httplib

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.brightbox import BrightboxNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.file_fixtures import ComputeFileFixtures
from test.secrets import BRIGHTBOX_PARAMS


class BrightboxTest(unittest.TestCase, TestCaseMixin):
    def setUp(self):
        BrightboxNodeDriver.connectionCls.conn_classes = (None, BrightboxMockHttp)
        BrightboxMockHttp.type = None
        self.driver = BrightboxNodeDriver(*BRIGHTBOX_PARAMS)

    def test_authentication(self):
        BrightboxMockHttp.type = 'INVALID_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

        BrightboxMockHttp.type = 'UNAUTHORIZED_CLIENT'
        self.assertRaises(InvalidCredsError, self.driver.list_nodes)

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        self.assertEqual(len(nodes[0].public_ips), 1)
        self.assertEqual(len(nodes[1].public_ips), 1)
        self.assertEqual(len(nodes[0].private_ips), 1)
        self.assertEqual(len(nodes[1].private_ips), 1)
        self.assertTrue('109.107.35.16' in nodes[0].public_ips)
        self.assertTrue('10.74.210.210' in nodes[0].private_ips)
        self.assertTrue('10.240.228.234' in nodes[1].private_ips)
        self.assertTrue('2a02:1348:14c:393a:24:19ff:fef0:e4ea' in nodes[1].public_ips)
        self.assertEqual(nodes[0].state, NodeState.RUNNING)
        self.assertEqual(nodes[1].state, NodeState.RUNNING)

    def test_list_node_extras(self):
        nodes = self.driver.list_nodes()
        self.assertFalse(nodes[0].size is None)
        self.assertFalse(nodes[1].size is None)
        self.assertFalse(nodes[0].image is None)
        self.assertFalse(nodes[1].image is None)
        self.assertEqual(nodes[0].image.id, 'img-arm8f')
        self.assertEqual(nodes[0].size.id, 'typ-urtky')
        self.assertEqual(nodes[1].image.id, 'img-j93gd')
        self.assertEqual(nodes[1].size.id, 'typ-qdiwq')
        self.assertEqual(nodes[0].extra['fqdn'],'srv-xvpn7.gb1.brightbox.com')
        self.assertEqual(nodes[1].extra['fqdn'],'srv-742vn.gb1.brightbox.com')
        self.assertEqual(nodes[0].extra['hostname'],'srv-xvpn7')
        self.assertEqual(nodes[1].extra['hostname'],'srv-742vn')
        self.assertEqual(nodes[0].extra['status'], 'active')
        self.assertEqual(nodes[1].extra['status'], 'active')
        self.assertTrue('interfaces' in nodes[0].extra)
        self.assertTrue('zone' in nodes[0].extra)
        self.assertTrue('snapshots' in nodes[0].extra)
        self.assertTrue('server_groups' in nodes[0].extra)
        self.assertTrue('started_at' in nodes[0].extra)
        self.assertTrue('created_at' in nodes[0].extra)
        self.assertTrue('deleted_at' in nodes[0].extra)

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 1)
        self.assertEqual(sizes[0].id, 'typ-4nssg')
        self.assertEqual(sizes[0].name, 'Brightbox Nano Instance')
        self.assertEqual(sizes[0].ram, 512)

    def test_list_images(self):
        images = self.driver.list_images()
        self.assertEqual(len(images), 25)
        self.assertEqual(images[0].id, 'img-99q79')
        self.assertEqual(images[0].name, 'CentOS 5.5 server')

    def test_list_images_extras(self):
        images = self.driver.list_images()
        extra = images[24].extra
        self.assertTrue(extra['ancestor'] is None)
        self.assertEqual(extra['arch'], 'i686')
        self.assertFalse(extra['compatibility_mode'])
        self.assertEqual(extra['created_at'], '2012-01-22T05:36:24Z')
        self.assertTrue('description' in extra)
        self.assertEqual(extra['disk_size'], 671)
        self.assertTrue(extra['min_ram'] is None)
        self.assertFalse(extra['official'])
        self.assertEqual(extra['owner'], 'acc-tqs4c')
        self.assertTrue(extra['public'])
        self.assertEqual(extra['source'], 'oneiric-i386-20178.gz')
        self.assertEqual(extra['source_type'], 'upload')
        self.assertEqual(extra['status'], 'deprecated')
        self.assertEqual(extra['username'], 'ubuntu')
        self.assertEqual(extra['virtual_size'], 1025)
        self.assertFalse('licence_name' in extra)


    def test_reboot_node_response(self):
        node = self.driver.list_nodes()[0]
        self.assertRaises(NotImplementedError, self.driver.reboot_node, [node])

    def test_destroy_node(self):
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_create_node(self):
        size = self.driver.list_sizes()[0]
        image = self.driver.list_images()[0]
        node = self.driver.create_node(name='Test Node', image=image, size=size)
        self.assertEqual('srv-3a97e', node.id)
        self.assertEqual('Test Node', node.name)


class BrightboxMockHttp(MockHttp):
    fixtures = ComputeFileFixtures('brightbox')

    def _token(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.OK, self.fixtures.load('token.json'))

    def _token_INVALID_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.BAD_REQUEST, '{"error":"invalid_client"}')

    def _token_UNAUTHORIZED_CLIENT(self, method, url, body, headers):
        if method == 'POST':
            return self.response(httplib.UNAUTHORIZED, '{"error":"unauthorized_client"}')

    def _1_0_images(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_images.json'))

    def _1_0_servers(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_servers.json'))
        elif method == 'POST':
            body = json.loads(body)

            node = json.loads(self.fixtures.load('create_server.json'))

            node['name'] = body['name']

            return self.response(httplib.ACCEPTED, json.dumps(node))

    def _1_0_servers_srv_xvpn7(self, method, url, body, headers):
        if method == 'DELETE':
            return self.response(httplib.ACCEPTED, '')

    def _1_0_server_types(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_server_types.json'))

    def _1_0_zones(self, method, url, body, headers):
        if method == 'GET':
            return self.response(httplib.OK, self.fixtures.load('list_zones.json'))

    def response(self, status, body):
        return (status, body, {'content-type': 'application/json'}, httplib.responses[status])


if __name__ == '__main__':
    sys.exit(unittest.main())

# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python

