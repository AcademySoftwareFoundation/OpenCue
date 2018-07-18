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
import logging

import main

import common
Cue3 = common.Cue3

logger = logging.getLogger("cue3.cuetools")

Parser = None

TEST_HOST = ""
TEST_FAC = ""
TEST_SHOW = ""

class CueadminTests(unittest.TestCase):

    def testCreateShow(self):
        show = "test_show"
        args = Parser.parse_args(["-create-show",show,"-force"])
        try:
            s = Cue3.findShow(show)
            s.proxy.delete()
        except Cue3.EntityNotFoundException,e:
            pass

        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertEqual(s.data.name,show)
        s.proxy.delete()

    def testDeleteShow(self):
        show = "test_show"
        args = Parser.parse_args(["-delete-show",show,"-force"])
        try:
            s = Cue3.findShow(show)
        except Cue3.EntityNotFoundException,e:
            s = Cue3.createShow(show)
        main.handleArgs(args)
        try:
            s = Cue3.findShow(show)
            assert False
        except Cue3.EntityNotFoundException,e:
            assert True

    def testEnableBooking(self):
        show = TEST_SHOW
        args = Parser.parse_args(["-booking",show,"off","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertFalse(s.data.bookingEnabled)
        args = Parser.parse_args(["-booking",show,"on","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertTrue(s.data.bookingEnabled)

    def testEnableDispatch(self):
        show = TEST_SHOW
        args = Parser.parse_args(["-dispatching",show,"off","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertFalse(s.data.dispatchEnabled)
        args = Parser.parse_args(["-dispatching",show,"on","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertTrue(s.data.dispatchEnabled)

    def testDefaultMinCores(self):
        show = TEST_SHOW
        args = Parser.parse_args(["-default-min-cores",show,"100","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertEquals(100, s.data.defaultMinCores)
        args = Parser.parse_args(["-default-min-cores",show,"1","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertEquals(1, s.data.defaultMinCores)

    def testDefaultMaxCores(self):
        show = TEST_SHOW
        args = Parser.parse_args(["-default-max-cores",show,"100","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertEquals(100, s.data.defaultMaxCores)
        args = Parser.parse_args(["-default-max-cores",show,"200","-force"])
        main.handleArgs(args)
        s = Cue3.findShow(show)
        self.assertEquals(200, s.data.defaultMaxCores)

    def testCreateAlloc(self):
        fac = TEST_FAC
        name = "test_alloc"
        entity = "%s.%s" % (fac, name)
        args = Parser.parse_args(["-create-alloc", fac, name, "tag", "-force"])
        try:
            s = Cue3.findAllocation(entity)
            s.proxy.delete()
        except Cue3.EntityNotFoundException,e:
            pass
        main.handleArgs(args)
        s = Cue3.findAllocation(entity)
        self.assertEqual(s.data.name, entity)
        s.proxy.delete()

    def testDeleteAlloc(self):
        entity = "{0}.test_alloc".format(TEST_FAC)
        args = Parser.parse_args(["-delete-alloc", entity, "-force"])
        try:
            s = Cue3.findAllocation(entity)
        except Cue3.EntityNotFoundException,e:
            f = Cue3.getFacility(TEST_FAC)
            f.proxy.createAllocation("test_alloc", "tulip")
        main.handleArgs(args)
        try:
            Cue3.findAllocation(entity)
            assert False
        except Cue3.EntityNotFoundException,e:
            assert True

    def testRenameAlloc(self):
        facprx = Cue3.getFacility(TEST_FAC).proxy

        entity1 = "{0}.test_alloc".format(TEST_FAC)
        new_name = "other_alloc"
        entity2 = "{0}.other_alloc".format(TEST_FAC)

        args = Parser.parse_args(["-rename-alloc", entity1, entity2, "-force"])

        deleteAlloc(entity1)
        deleteAlloc(entity2)

        facprx.createAllocation("test_alloc", "tulip")
        main.handleArgs(args)
        s = Cue3.findAllocation(entity2)
        self.assertEqual(s.data.name, entity2)
        s.proxy.delete()

    def testTagAlloc(self):
        fprx = Cue3.getFacility(TEST_FAC).proxy
        entity = "{0}.test_alloc".format(TEST_FAC)
        new_tag = "new_tag"
        args = Parser.parse_args(["-tag-alloc", entity ,new_tag, "-force"])

        deleteAlloc(entity)

        fprx.createAllocation("test_alloc", entity)
        main.handleArgs(args)
        s = Cue3.findAllocation(entity)
        self.assertEqual(s.data.tag, new_tag)
        s.proxy.delete()

    def testTransferAlloc(self):
        fprx = Cue3.getFacility(TEST_FAC).proxy
        e1 = "{0}.talloc1".format(TEST_FAC)
        e2 = "{0}.talloc2";.format(TEST_FAC)
        args = Parser.parse_args(["-transfer", e1 ,e2, "-force"])

        deleteAlloc(e1)
        deleteAlloc(e2)

        fprx.createAllocation("talloc1", e1)
        fprx.createAllocation("talloc2", e2)
        main.handleArgs(args)

        Cue3.findAllocation(e1).proxy.delete()
        Cue3.findAllocation(e2).proxy.delete()

        # Need to make this test better to sure hosts are
        # actually being transfered on the server.

    def testSetRepairStare(self):
        e = TEST_HOST
        args = Parser.parse_args(["-repair", "-host", e, "-force"])
        main.handleArgs(args)

        self.assertEquals(Cue3.findHost(e).data.state,Cue3.HardwareState.Repair)
        Cue3.findHost(e).proxy.setHardwareState(Cue3.HardwareState.Up)

    def testLockHost(self):
        e = TEST_HOST
        args = Parser.parse_args(["-lock", "-host", e, "-force"])
        main.handleArgs(args)

        self.assertEquals(Cue3.findHost(e).data.lockState,Cue3.LockState.Locked)
        Cue3.findHost(e).proxy.unlock()

    def testUnlockHost(self):
        e = TEST_HOST
        args = Parser.parse_args(["-unlock", "-host", e, "-force"])
        main.handleArgs(args)

        self.assertEquals(Cue3.findHost(e).data.lockState,Cue3.LockState.Open)
        Cue3.findHost(e).proxy.unlock()

    def testMovesHost(self):
        e = TEST_HOST
        dst = "{0}.unassigned".format(TEST_FAC)
        back = Cue3.findHost(e).data.allocName

        args = Parser.parse_args(["-move", dst, "-host", e, "-force"])
        main.handleArgs(args)

        self.assertEquals(Cue3.findHost(e).data.allocName, dst)
        args = Parser.parse_args(["-move", back, "-host", e, "-force"])
        main.handleArgs(args)
        self.assertEquals(Cue3.findHost(e).data.allocName, back)

    def testCreateSub(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a,h)
        deleteSub(r)

        args = Parser.parse_args(["-create-sub", h, a, "100","110", "-force"])
        main.handleArgs(args)

        s = Cue3.findSubscription(r)
        self.assertEquals(s.data.showName,h)
        self.assertEquals(s.data.allocationName,a)
        self.assertEquals(s.data.name, r)
        self.assertEquals(s.data.size, float(100))
        self.assertEquals(s.data.burst, float(110))
        s.proxy.delete()

    def testDeleteSub(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a,h)
        deleteSub(r)

        show = Cue3.findShow(h)
        show.proxy.createSubscription(Cue3.findAllocation(a).proxy, 100.0, 110.0)

        args = Parser.parse_args(["-delete-sub", h, a, "-force"])
        main.handleArgs(args)

        try:
            Cue3.findSubscription(r)
            raise Exception("subscription should have been deleted")
        except:
            pass

    def testSetSize(self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = Cue3.findShow(h)
        show.proxy.createSubscription(Cue3.findAllocation(a).proxy, 100.0, 110.0)

        args = Parser.parse_args(["-size", h, a, "200","-force"])
        main.handleArgs(args)

        s = Cue3.findSubscription(r)
        self.assertEquals(s.data.size,200.0)
        deleteSub(r)

    def testSetBurst (self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = Cue3.findShow(h)
        show.proxy.createSubscription(Cue3.findAllocation(a).proxy, 100.0, 110.0)

        args = Parser.parse_args(["-burst", h, a, "200","-force"])
        main.handleArgs(args)

        s = Cue3.findSubscription(r)
        self.assertEquals(s.data.burst,200.0)
        deleteSub(r)

    def testSetBurstPercentage (self):
        a = "{0}.unassigned".format(TEST_FAC)
        h = TEST_SHOW
        r = "%s.%s" % (a, h)
        deleteSub(r)

        show = Cue3.findShow(h)
        show.proxy.createSubscription(Cue3.findAllocation(a).proxy, 100.0, 110.0)

        args = Parser.parse_args(["-burst", h, a, "20%","-force"])
        main.handleArgs(args)

        s = Cue3.findSubscription(r)
        self.assertEquals(s.data.burst, 120.0)
        deleteSub(r)

def deleteSub(name):
    try:
        Cue3.findSubscription(name).proxy.delete()
    except Cue3.EntityNotFoundException,e:
        pass

def deleteAlloc(name):
    try:
        s = Cue3.findAllocation(name)
        s.proxy.delete()
    except Cue3.EntityNotFoundException,e:
        pass

def run(parser):
    if not TEST_FAC or not TEST_HOST or not TEST_SHOW:
        print "Please set TEST_FAC, TEST_HOST and TEST_SHOW before running tests."
        return

    global Parser
    Parser = parser
    suite = unittest.TestLoader().loadTestsFromTestCase(CueadminTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
