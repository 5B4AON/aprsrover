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

    def test_send_object_report_success(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.send_object_report(
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

    def test_send_object_report_success_with_name(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_object_report(
            mycall="CALL-14",
            path=["WIDE1-1"],
            time_dhm="011234z",
            lat_dmm="5132.07N",
            long_dmm="00007.40W",
            symbol_id="/",
            symbol_code=">",
            comment="Test object",
            name="OBJNAME"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        # Object name should be used and padded to 9 chars
        self.assertIn(b";OBJNAME  *011234z5132.07N/00007.40W>Test object", frame.info)

    def test_send_object_report_success_without_name(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_object_report(
            mycall="CALL-15",
            path=["WIDE1-1"],
            time_dhm="011234z",
            lat_dmm="5132.07N",
            long_dmm="00007.40W",
            symbol_id="/",
            symbol_code=">",
            comment="Test object"
            # name omitted, should use mycall
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b";CALL-15  *011234z5132.07N/00007.40W>Test object", frame.info)

    def test_send_object_report_invalid_name(self):
        self.aprs.initialized = True
        # Too long
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-16",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object",
                name="TOOLONGNAME"
            )
        # Empty string
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-17",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object",
                name=""
            )

    def test_send_object_report_invalid_callsign(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="BADCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_path(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-15",
                path=[""],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_time(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-16",
                path=["WIDE1-1"],
                time_dhm="01123z",  # Too short
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_lat(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-17",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="BADLAT",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_long(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-18",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="BADLONG",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_symbol_id(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-19",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="XX",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_invalid_symbol_code(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-20",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">>",
                comment="Test object"
            )

    def test_send_object_report_invalid_comment(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_object_report(
                mycall="CALL-21",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="X" * 44
            )

    def test_send_object_report_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_object_report(
                mycall="CALL-22",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test object"
            )

    def test_send_object_report_write_exception(self):
        class BadProto(DummyKissProtocol):
            def write(self, frame): raise RuntimeError("fail")
        self.aprs.kiss_protocol = BadProto()
        self.aprs.initialized = True
        with self.assertRaises(AprsError):
            self.aprs.send_object_report(
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

    def test_send_position_report_success_with_time(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_position_report(
            mycall="CALL-30",
            path=["WIDE1-1"],
            lat="5132.07N",  # was lat_dmm
            lon="00007.40W",  # was long_dmm
            symbol_id="/",
            symbol_code=">",
            comment="Test position",
            time_dhm="011234z"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b"/011234z5132.07N/00007.40W>Test position", frame.info)

    def test_send_position_report_success_without_time(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_position_report(
            mycall="CALL-31",
            path=["WIDE1-1"],
            lat="5132.07N",  # was lat_dmm
            lon="00007.40W",  # was long_dmm
            symbol_id="/",
            symbol_code=">",
            comment="No time"
            # time_dhm omitted
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b"!5132.07N/00007.40W>No time", frame.info)

    def test_send_position_report_invalid_time(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-32",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Bad time",
                time_dhm="01123z"  # Too short
            )

    def test_send_position_report_invalid_lat(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-33",
                path=["WIDE1-1"],
                lat="BADLAT",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Bad lat"
            )

    def test_send_position_report_invalid_long(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-34",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="BADLONG",
                symbol_id="/",
                symbol_code=">",
                comment="Bad long"
            )

    def test_send_position_report_invalid_symbol_id(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-35",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="XX",
                symbol_code=">",
                comment="Bad symbol id"
            )

    def test_send_position_report_invalid_symbol_code(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-36",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">>",
                comment="Bad symbol code"
            )

    def test_send_position_report_invalid_comment(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="CALL-37",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="X" * 44
            )

    def test_send_position_report_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_position_report(
                mycall="CALL-38",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test"
            )

    def test_send_position_report_write_exception(self):
        class BadProto(DummyKissProtocol):
            def write(self, frame): raise RuntimeError("fail")
        self.aprs.kiss_protocol = BadProto()
        self.aprs.initialized = True
        with self.assertRaises(AprsError):
            self.aprs.send_position_report(
                mycall="CALL-39",
                path=["WIDE1-1"],
                lat="5132.07N",
                lon="00007.40W",
                symbol_id="/",
                symbol_code=">",
                comment="Test"
            )

    def test_send_status_report_success_with_time(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_status_report(
            mycall="CALL-40",
            path=["WIDE1-1"],
            status="Net Control Center",
            time_dhm="092345z"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b">092345zNet Control Center", frame.info)

    def test_send_status_report_success_without_time(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APDW16"
        self.aprs.send_status_report(
            mycall="CALL-41",
            path=["WIDE1-1"],
            status="Mission started"
            # time_dhm omitted
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b">Mission started", frame.info)

    def test_send_status_report_invalid_time(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_status_report(
                mycall="CALL-42",
                path=["WIDE1-1"],
                status="Bad time",
                time_dhm="09234z"  # Too short
            )

    def test_send_status_report_invalid_status_too_long(self):
        self.aprs.initialized = True
        # 63 chars, should fail (max 62 without time)
        with self.assertRaises(ValueError):
            self.aprs.send_status_report(
                mycall="CALL-43",
                path=["WIDE1-1"],
                status="X" * 63
            )
        # 56 chars, should fail (max 55 with time)
        with self.assertRaises(ValueError):
            self.aprs.send_status_report(
                mycall="CALL-44",
                path=["WIDE1-1"],
                status="X" * 56,
                time_dhm="092345z"
            )

    def test_send_status_report_invalid_status_chars(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_status_report(
                mycall="CALL-45",
                path=["WIDE1-1"],
                status="Bad|status"
            )
        with self.assertRaises(ValueError):
            self.aprs.send_status_report(
                mycall="CALL-46",
                path=["WIDE1-1"],
                status="Bad~status"
            )

    def test_send_status_report_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_status_report(
                mycall="CALL-47",
                path=["WIDE1-1"],
                status="Test"
            )

    def test_send_status_report_write_exception(self):
        class BadProto(DummyKissProtocol):
            def write(self, frame): raise RuntimeError("fail")
        self.aprs.kiss_protocol = BadProto()
        self.aprs.initialized = True
        with self.assertRaises(AprsError):
            self.aprs.send_status_report(
                mycall="CALL-48",
                path=["WIDE1-1"],
                status="Test"
            )

    def test_send_my_message_no_ack_invalid_recipient(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-10",
                path=["WIDE1-1"],
                recipient="BADRECIP",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_path_type(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-11",
                path="notalist",
                recipient="DEST-11",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_message_type(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-12",
                path=["WIDE1-1"],
                recipient="DEST-12",
                message=None  # type: ignore
            )

    def test_send_my_message_no_ack_message_too_long(self):
        self.aprs.initialized = True
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="CALL-13",
                path=["WIDE1-1"],
                recipient="DEST-13",
                message="X" * 68
            )

    def test_send_my_message_no_ack_message_min_length(self):
        proto = DummyKissProtocol()
        self.aprs.kiss_protocol = proto
        self.aprs.initialized = True
        self.aprs.send_my_message_no_ack(
            mycall="CALL-14",
            path=["WIDE1-1"],
            recipient="DEST-14",
            message="A"
        )
        self.assertTrue(proto.written_frames)
        frame = proto.written_frames[0]
        self.assertIn(b"A", frame.info)

    def test_send_position_report_standard(self):
        self.aprs.initialized = True
        self.aprs.kiss_protocol = self.aprs.kiss  # Use dummy
        self.aprs.send_position_report(
            mycall="5B4AON-9",
            path=["WIDE1-1"],
            lat="3511.14N",
            lon="03322.94E",
            symbol_id="/",
            symbol_code=">",
            comment="Test standard",
            time_dhm="011234z",
            compressed=False,
        )
        frame = self.aprs.kiss_protocol.protocol.written_frames[-1]
        self.assertIsNotNone(frame)
        info = frame.info.decode()
        self.assertTrue(
            info.startswith("/011234z3511.14N/03322.94E>Test standard")
            or info.startswith("!3511.14N/03322.94E>Test standard")
        )

    def test_send_position_report_compressed(self):
        self.aprs.initialized = True
        self.aprs.kiss_protocol = self.aprs.kiss  # Use dummy
        self.aprs.send_position_report(
            mycall="5B4AON-9",
            path=["WIDE1-1"],
            lat=35.1856,
            lon=33.3823,
            symbol_id="/",
            symbol_code=">",
            comment="Test compressed",
            time_dhm="011234z",
            compressed=True,
        )
        frame = self.aprs.kiss_protocol.protocol.written_frames[-1]
        self.assertIsNotNone(frame)
        info = frame.info.decode()
        # Compressed format starts with /time symbol_id, then 8 base91 chars, then 3 spaces, symbol_code, comment
        self.assertTrue(info.startswith("/011234z/"))
        self.assertIn("Test compressed", info)
        # Check length of base91 encoded part (should be 8 chars after symbol_id)
        base91_part = info[10+1:10+1+8]  # after /011234z and symbol_id
        self.assertEqual(len(base91_part), 8)

    def test_send_position_report_invalid_callsign(self):
        self.aprs.initialized = True
        self.aprs.kiss_protocol = self.aprs.kiss
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="BADCALL",
                path=["WIDE1-1"],
                lat="3511.14N",
                lon="03322.94E",
                symbol_id="/",
                symbol_code=">",
                comment="Test",
            )

    def test_send_position_report_invalid_latlon_for_compressed(self):
        self.aprs.initialized = True
        self.aprs.kiss_protocol = self.aprs.kiss
        with self.assertRaises(ValueError):
            self.aprs.send_position_report(
                mycall="5B4AON-9",
                path=["WIDE1-1"],
                lat="notafloat",
                lon="notafloat",
                symbol_id="/",
                symbol_code=">",
                comment="Test",
                compressed=True,
            )

    def test_send_position_report_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_position_report(
                mycall="5B4AON-9",
                path=["WIDE1-1"],
                lat="3511.14N",
                lon="03322.94E",
                symbol_id="/",
                symbol_code=">",
                comment="Test",
            )