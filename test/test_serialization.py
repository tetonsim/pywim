import unittest
import enum

import pywim

class Primitives(pywim.WimObject):
    def __init__(self):
        self.a = 0
        self.b = 'test'
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
        self.e = pywim.WimEnum(TestEnum)

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

        e2.e.enum_value = TestEnum.B

        d1 = e1.to_dict()
        d2 = e2.to_dict()

        e3 = ObjectWithEnum.from_dict(d1)
        e4 = ObjectWithEnum.from_dict(d2)

        self.assertEqual(e3.e.enum_value, TestEnum.A)
        self.assertEqual(e4.e.enum_value, TestEnum.B)
