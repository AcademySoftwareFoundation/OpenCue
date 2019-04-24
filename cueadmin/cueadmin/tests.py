#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import unittest

import opencue

import common


Parser = None

TEST_HOST = ""
TEST_FAC = ""
TEST_SHOW = ""


class CueadminTests(unittest.TestCase):



    def testTransferAlloc(self):
        facility = opencue.api.getFacility(TEST_FAC)
        e1 = "{0}.talloc1".format(TEST_FAC)
        e2 = "{0}.talloc2".format(TEST_FAC)
        args = Parser.parse_args(["-transfer", e1, e2, "-force"])

        deleteAlloc(e1)
        deleteAlloc(e2)

        facility.createAllocation("talloc1", e1)
        facility.createAllocation("talloc2", e2)
        common.handleArgs(args)

        opencue.api.findAllocation(e1).delete()
        opencue.api.findAllocation(e2).delete()

        # Need to make this test better to sure hosts are
        # actually being transferred on the server.

    def testSetRepairStare(self):
        e = TEST_HOST
        args = Parser.parse_args(["-repair", "-host", e, "-force"])
        common.handleArgs(args)

        self.assertEquals(opencue.api.findHost(e).data.state, opencue.api.host_pb2.REPAIR)
        opencue.api.findHost(e).setHardwareState(opencue.api.host_pb2.UP)

    def testLockHost(self):
        e = TEST_HOST
        args = Parser.parse_args(["-lock", "-host", e, "-force"])
        common.handleArgs(args)

        self.assertEquals(opencue.api.findHost(e).data.lock_state, opencue.api.host_pb2.LOCKED)
        opencue.api.findHost(e).unlock()

    def testUnlockHost(self):
        e = TEST_HOST
        args = Parser.parse_args(["-unlock", "-host", e, "-force"])
        common.handleArgs(args)

        self.assertEquals(opencue.api.findHost(e).data.lock_state, opencue.api.host_pb2.OPEN)
        opencue.api.findHost(e).unlock()

    def testMovesHost(self):
        e = TEST_HOST
        dst = "{0}.unassigned".format(TEST_FAC)
        back = opencue.api.findHost(e).data.alloc_name

        args = Parser.parse_args(["-move", dst, "-host", e, "-force"])
        common.handleArgs(args)

        self.assertEquals(opencue.api.findHost(e).data.alloc_name, dst)
        args = Parser.parse_args(["-move", back, "-host", e, "-force"])
        common.handleArgs(args)
        self.assertEquals(opencue.api.findHost(e).data.alloc_name, back)

    def testCreateSub(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        args = Parser.parse_args(["-create-sub", h, a, "100", "110", "-force"])
        common.handleArgs(args)

        s = opencue.api.findSubscription(r)
        self.assertEquals(s.data.show_name, h)
        self.assertEquals(s.data.allocation_name, a)
        self.assertEquals(s.data.name, r)
        self.assertEquals(s.data.size, float(100))
        self.assertEquals(s.data.burst, float(110))
        s.delete()

    def testDeleteSub(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = opencue.api.findShow(h)
        show.createSubscription(opencue.api.findAllocation(a).data, 100.0, 110.0)

        args = Parser.parse_args(["-delete-sub", h, a, "-force"])
        common.handleArgs(args)

        try:
            opencue.api.findSubscription(r)
            raise Exception("subscription should have been deleted")
        except opencue.EntityNotFoundException:
            pass

    def testSetSize(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = opencue.api.findShow(h)
        show.createSubscription(opencue.api.findAllocation(a).data, 100.0, 110.0)

        args = Parser.parse_args(["-size", h, a, "200", "-force"])
        common.handleArgs(args)

        s = opencue.api.findSubscription(r)
        self.assertEquals(s.data.size, 200.0)
        deleteSub(r)

    def testSetBurst (self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = opencue.api.findShow(h)
        show.createSubscription(opencue.api.findAllocation(a).data, 100.0, 110.0)

        args = Parser.parse_args(["-burst", h, a, "200", "-force"])
        common.handleArgs(args)

        s = opencue.api.findSubscription(r)
        self.assertEquals(s.data.burst, 200.0)
        deleteSub(r)

    def testSetBurstPercentage (self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = opencue.api.findShow(h)
        show.createSubscription(opencue.api.findAllocation(a).data, 100.0, 110.0)

        args = Parser.parse_args(["-burst", h, a, "20%","-force"])
        common.handleArgs(args)

        s = opencue.api.findSubscription(r)
        self.assertEquals(s.data.burst, 120.0)
        deleteSub(r)


def deleteSub(name):
    try:
        opencue.api.findSubscription(name).delete()
    except opencue.EntityNotFoundException:
        pass


def deleteAlloc(name):
    try:
        s = opencue.api.findAllocation(name)
        s.delete()
    except opencue.EntityNotFoundException:
        pass


def run(parser):
    if not TEST_FAC or not TEST_HOST or not TEST_SHOW:
        print "Please set TEST_FAC, TEST_HOST and TEST_SHOW before running tests."
        return

    global Parser
    Parser = parser
    suite = unittest.TestLoader().loadTestsFromTestCase(CueadminTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

