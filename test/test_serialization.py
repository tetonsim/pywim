import unittest
import enum
import datetime

import pywim

class Primitives(pywim.WimObject):
    def __init__(self, b=None):
        self.a = 0
        self.b = b if b else 'test'
        self.c = 99.9
        self.d = None

class ObjectWithList(pywim.WimObject):
    def __init__(self):
        self.l = pywim.WimList(Primitives)

class TestEnum(enum.Enum):
    A = 1
    B = 2

class ObjectWithEnum(pywim.WimObject):
    def __init__(self):
        self.e = TestEnum(1)

class ObjectIgnore(pywim.WimObject):
    def __init__(self):
        self.x = Primitives('alaska')
        self.y = pywim.WimIgnore.make(Primitives)('alabama')

class ObjectWithDateTimes(pywim.WimObject):
    def __init__(self):
        self.a = datetime.datetime.utcnow()

class WimObjectTest(unittest.TestCase):
    def test_primitives(self):
        p1 = Primitives()

        d = p1.to_dict()
        p = Primitives.from_dict(d)

        self.assertEqual(p.a, p1.a)
        self.assertEqual(p.b, p1.b)
        self.assertEqual(p.c, p1.c)
        self.assertIsNone(p.d)

        self.assertFalse('d' in d.keys())

    def test_list(self):
        l1 = ObjectWithList()

        p1 = Primitives()
        p2 = Primitives()

        p2.c = 101.0
        p2.d = 'new string'

        l1.l.extend((p1, p2))

        d = l1.to_dict()
        l2 = ObjectWithList.from_dict(d)

        self.assertEqual(len(l2.l), 2)

        p3 = l2.l[0]
        p4 = l2.l[1]

        self.assertEqual(p3.a, p1.a)
        self.assertEqual(p3.b, p1.b)
        self.assertEqual(p3.c, p1.c)
        self.assertIsNone(p3.d)

        self.assertEqual(p4.a, p2.a)
        self.assertEqual(p4.b, p2.b)
        self.assertEqual(p4.c, p2.c)
        self.assertEqual(p4.d, p2.d)

    def test_enum(self):
        e1 = ObjectWithEnum()
        e2 = ObjectWithEnum()

        e2.e = TestEnum.B

        d1 = e1.to_dict()
        d2 = e2.to_dict()

        e3 = ObjectWithEnum.from_dict(d1)
        e4 = ObjectWithEnum.from_dict(d2)

        self.assertEqual(e3.e, TestEnum.A)
        self.assertEqual(e4.e, TestEnum.B)

    def test_ignore(self):
        i1 = ObjectIgnore()

        i1.x.a = 101

        # modify y - our tests below will make sure
        # these values are not persistent through the
        # serialization/deserialization process
        i1.y.a = 102
        i1.y.b = 'arkansas'

        d1 = i1.to_dict()

        self.assertTrue('x' in d1.keys())
        self.assertFalse('y' in d1.keys())

        i2 = ObjectIgnore.from_dict(d1)

        self.assertEqual(i2.x.a, 101)
        self.assertEqual(i2.x.b, 'alaska')

        self.assertNotEqual(i2.y.a, 102)
        self.assertEqual(i2.y.b, 'alabama') # should be equal to what ObjectIgnore constructs it to

    def test_date_times(self):
        obj = ObjectWithDateTimes()

        wyo_statehood = datetime.datetime(1890, 7, 10, 8, 0, 0)
        obj.a = wyo_statehood

        d = obj.to_dict()

        self.assertTrue('a' in d.keys())
        self.assertEqual(d['a'], wyo_statehood.isoformat())

        obj2 = ObjectWithDateTimes.from_dict(d)

        self.assertEqual(obj2.a, wyo_statehood)
