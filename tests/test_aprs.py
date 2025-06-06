import sys
import os
import unittest
from typing import Any, List
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.aprs import Aprs, AprsError, KISSInterface
from ax253 import Frame

class DummyKissProtocol:
    def __init__(self):
        self.written_frames: List[Frame] = []
        self.read_frames: List[Frame] = []
        self.read_called = False

    def write(self, frame: Frame) -> None:
        self.written_frames.append(frame)

    async def read(self):
        self.read_called = True
        for frame in self.read_frames:
            yield frame

class DummyKISS(KISSInterface):
    def __init__(self):
        self.protocol = DummyKissProtocol()
        self.create_called = False

    async def create_tcp_connection(self, host: str, port: int, kiss_settings: dict) -> tuple[Any, Any]:
        self.create_called = True
        return (object(), self.protocol)

    def write(self, frame: Frame) -> None:
        self.protocol.write(frame)

    def read(self):
        return self.protocol.read()

class TestAprs(unittest.TestCase):
    def setUp(self) -> None:
        self.dummy_kiss = DummyKISS()
        self.aprs = Aprs(host="localhost", port=8001, kiss=self.dummy_kiss)
        self.aprs.kiss_protocol = self.dummy_kiss.protocol
        self.aprs.transport = object()
        self.aprs.initialized = True

    def test_register_and_unregister_observer(self):
        calls = []
        def cb(frame): calls.append(frame)
        self.aprs.register_observer("CALL-1", cb)
        self.assertIn("CALL-1", self.aprs._observers)
        self.assertIn(cb, self.aprs._observers["CALL-1"])
        self.aprs.unregister_observer("CALL-1", cb)
        self.assertNotIn("CALL-1", self.aprs._observers)

    def test_unregister_observer_all(self):
        cb1 = lambda f: None
        cb2 = lambda f: None
        self.aprs.register_observer("CALL-2", cb1)
        self.aprs.register_observer("CALL-2", cb2)
        self.aprs.unregister_observer("CALL-2")
        self.assertNotIn("CALL-2", self.aprs._observers)

    def test_unregister_observer_not_found(self):
        cb = lambda f: None
        self.aprs.register_observer("CALL-3", cb)
        # Should not raise
        self.aprs.unregister_observer("CALL-3", lambda f: None)

    def test_clear_observers(self):
        cb = lambda f: None
        self.aprs.register_observer("CALL-4", cb)
        self.aprs.clear_observers()
        self.assertEqual(self.aprs._observers, {})

    def test_notify_observers(self):
        called = []
        def cb(frame): called.append(frame)
        self.aprs.register_observer("DEST-1", cb)
        # Frame info must contain ":DEST-1   :" (callsign padded to 9 chars)
        info = b":DEST-1   :hello"
        frame = Frame(destination="X", source="Y", path=[], info=info)
        self.aprs._notify_observers(frame)
        self.assertEqual(called[0], frame)

    def test_notify_observers_callback_exception(self):
        def bad_cb(frame): raise RuntimeError("fail")
        self.aprs.register_observer("DEST-2", bad_cb)
        info = b":DEST-2:hello"
        frame = Frame(destination="X", source="Y", path=[], info=info)
        # Should not raise
        self.aprs._notify_observers(frame)

    def test_get_my_message(self):
        # Pad CALL-5 to 9 chars for APRS message format
        info = b":CALL-5   :test message{123"
        frame = Frame(destination="X", source="Y", path=[], info=info)
        msg = self.aprs.get_my_message("CALL-5", frame)
        self.assertEqual(msg, "test message")

    def test_get_my_message_none(self):
        info = b":OTHER:hello"
        frame = Frame(destination="X", source="Y", path=[], info=info)
        msg = self.aprs.get_my_message("CALL-6", frame)
        self.assertIsNone(msg)

    def test_send_my_message_no_ack_success(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.send_my_message_no_ack(
            mycall="CALL-9",
            path=["WIDE1-1"],
            recipient="DEST-9",
            message="Hello APRS"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b"Hello APRS", frame.info)

    def test_send_my_message_no_ack_invalid_callsign(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="BADCALL",
                path=["WIDE1-1"],
                recipient="DEST-10",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_path(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-10",
                path=[""],
                recipient="DEST-10",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_message(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-11",
                path=["WIDE1-1"],
                recipient="DEST-11",
                message=""
            )

    def test_send_my_message_no_ack_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-12",
                path=["WIDE1-1"],
                recipient="DEST-12",
                message="Hello"
            )

    def test_send_my_message_no_ack_write_exception(self):
        class BadProto(DummyKissProtocol):
            def write(self, frame): raise RuntimeError("fail")
        self.aprs.kiss_protocol = BadProto()
        self.aprs.initialized = True
        with self.assertRaises(AprsError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-13",
                path=["WIDE1-1"],
                recipient="DEST-13",
                message="Hello"
            )

    def test_send_my_object_no_course_speed_success(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.send_my_object_no_course_speed(
            mycall="CALL-14",
            path=["WIDE1-1"],
            time_dhm="011234z",
            lat_dmm="5132.07N",
            long_dmm="00007.40W",
            symbol_id="/",
            symbol_code=">",
            comment="Test object"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b"Test object", frame.info)

    def test_send_my_object_no_course_speed_invalid_callsign(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="BADCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_path(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-15",
                path=[""],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_time(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-16",
                path=["WIDE1-1"],
                time_dhm="01123z",  # Too short
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_lat(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-17",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="BADLAT",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_long(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-18",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="BADLONG",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_symbol_id(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-19",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="XX",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_symbol_code(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-20",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">>",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_comment(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-21",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="X" * 44
            )

    def test_send_my_object_no_course_speed_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-22",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_write_exception(self):
        class BadProto(DummyKissProtocol):
            def write(self, frame): raise RuntimeError("fail")
        self.aprs.kiss_protocol = BadProto()
        self.aprs.initialized = True
        with self.assertRaises(AprsError):
            self.aprs.send_my_object_no_course_speed(
                mycall="CALL-23",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_connect_success(self):
        aprs = Aprs(host="localhost", port=8001, kiss=self.dummy_kiss)
        import asyncio
        asyncio.run(aprs.connect())
        self.assertTrue(aprs.initialized)
        self.assertIsInstance(aprs.kiss_protocol, DummyKissProtocol)

    def test_connect_failure(self):
        class FailingKISS(DummyKISS):
            async def create_tcp_connection(self, host, port, kiss_settings):
                raise Exception("fail")
        aprs = Aprs(host="localhost", port=8001, kiss=FailingKISS())
        import asyncio
        with self.assertRaises(AprsError):
            asyncio.run(aprs.connect())

    def test_run_not_initialized(self):
        aprs = Aprs(host="localhost", port=8001, kiss=self.dummy_kiss)
        with self.assertRaises(AprsError):
            import asyncio
            asyncio.run(aprs.run())

    def test_run_loop_and_cancel(self):
        proto = DummyKissProtocol()
        # Pad DEST-24 to 9 chars for APRS message format
        info = b":DEST-24  :hello"
        frame = Frame(destination="X", source="Y", path=[], info=info)
        proto.read_frames.append(frame)
        aprs = Aprs(host="localhost", port=8001, kiss=self.dummy_kiss)
        aprs.kiss_protocol = proto
        aprs.transport = object()
        aprs.initialized = True
        called = []
        aprs.register_observer("DEST-24", lambda f: called.append(f))
        import asyncio
        async def run_and_cancel():
            task = asyncio.create_task(aprs.run())
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        asyncio.run(run_and_cancel())
        self.assertTrue(called)

    def test_send_ack_if_requested(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        info = b":CALL-7     :test{42"
        frame = Frame(destination="X", source="SRC", path=[], info=info)
        self.aprs.send_ack_if_requested(frame, "MYCALL-1", ["WIDE1-1"])
        self.assertTrue(proto.written_frames)
        ack_frame = proto.written_frames[0]
        self.assertIn(b":ack42", ack_frame.info)

    def test_send_ack_if_requested_not_initialized(self):
        self.aprs.initialized = False
        info = b":CALL-8     :test{42"
        frame = Frame(destination="X", source="SRC", path=[], info=info)
        # Should not raise
        self.aprs.send_ack_if_requested(frame, "MYCALL-2", ["WIDE1-1"])

if __name__ == "__main__":
    unittest.main()