import sys
import os
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.aprs import Aprs, AprsError

class DummyFrame:
    def __init__(self, info: bytes = b'', source: str = 'SRC'):
        self.info = info
        self.source = source

class TestAprs(unittest.TestCase):
    def setUp(self):
        self.aprs = Aprs(host="localhost", port=8001)
        self.aprs.kiss_protocol = MagicMock()
        self.aprs.initialized = True
        self.aprs.APRS_SW_VERSION = "APRSW"

    def test_register_and_notify_observer(self):
        called = []
        def observer(frame):
            called.append(frame)
        self.aprs.register_observer("MYCALL", observer)
        frame = DummyFrame(info=b':MYCALL   :Hello{1')
        self.aprs._notify_observers(frame)
        self.assertIn(frame, called)

    def test_register_multiple_callbacks_same_call(self):
        called1, called2 = [], []
        def observer1(frame): called1.append(frame)
        def observer2(frame): called2.append(frame)
        self.aprs.register_observer("MYCALL", observer1)
        self.aprs.register_observer("MYCALL", observer2)
        frame = DummyFrame(info=b':MYCALL   :Hello{1')
        self.aprs._notify_observers(frame)
        self.assertIn(frame, called1)
        self.assertIn(frame, called2)

    def test_unregister_single_callback(self):
        called = []
        def observer(frame): called.append(frame)
        self.aprs.register_observer("MYCALL", observer)
        self.aprs.unregister_observer("MYCALL", observer)
        frame = DummyFrame(info=b':MYCALL   :Hello{1')
        self.aprs._notify_observers(frame)
        self.assertNotIn(frame, called)

    def test_unregister_all_callbacks_for_call(self):
        called1, called2 = [], []
        def observer1(frame): called1.append(frame)
        def observer2(frame): called2.append(frame)
        self.aprs.register_observer("MYCALL", observer1)
        self.aprs.register_observer("MYCALL", observer2)
        self.aprs.unregister_observer("MYCALL")  # Remove all for MYCALL
        frame = DummyFrame(info=b':MYCALL   :Hello{1')
        self.aprs._notify_observers(frame)
        self.assertNotIn(frame, called1)
        self.assertNotIn(frame, called2)

    def test_clear_observers(self):
        called = []
        def observer(frame): called.append(frame)
        self.aprs.register_observer("MYCALL", observer)
        self.aprs.clear_observers()
        frame = DummyFrame(info=b':MYCALL   :Hello{1')
        self.aprs._notify_observers(frame)
        self.assertNotIn(frame, called)

    def test_get_my_message_found(self):
        # Simulate a frame addressed to MYCALL
        info = b':MYCALL   :Hello{1'
        frame = DummyFrame(info=info)
        msg = self.aprs.get_my_message('MYCALL', frame)
        self.assertEqual(msg, 'Hello')

    def test_get_my_message_not_found(self):
        info = b':OTHER    :Hello{1'
        frame = DummyFrame(info=info)
        msg = self.aprs.get_my_message('MYCALL', frame)
        self.assertIsNone(msg)

    @patch('aprsrover.aprs.Frame')
    def test_acknowledge_sends_ack(self, mock_frame_class):
        # Setup
        frame = DummyFrame(info=b':MYCALL   :Hello{42', source='SRC')
        self.aprs.kiss_protocol = MagicMock()
        self.aprs.initialized = True
        mycall = 'MYCALL'
        path = ['WIDE1-1']
        # Patch Frame.ui to return a dummy frame
        dummy_ack_frame = object()
        mock_frame_class.ui.return_value = dummy_ack_frame

        # Call acknowledge
        self.aprs.acknowledge(frame, mycall, path)

        # Check that write was called with the dummy ack frame
        self.aprs.kiss_protocol.write.assert_called_once_with(dummy_ack_frame)

    def test_acknowledge_not_initialized(self):
        frame = DummyFrame(info=b':MYCALL   :Hello{42', source='SRC')
        self.aprs.kiss_protocol = MagicMock()
        self.aprs.initialized = False
        mycall = 'MYCALL'
        path = ['WIDE1-1']
        # Should not raise or call write
        self.aprs.acknowledge(frame, mycall, path)
        self.aprs.kiss_protocol.write.assert_not_called()

    def test_send_my_message_no_ack_valid(self):
        """Test sending a valid APRS message without ack."""
        self.aprs.send_my_message_no_ack(
            mycall="N0CALL-1",
            path=["WIDE1-1"],
            recipient="5B4AON-12",
            message="Hello APRS"
        )
        self.assertTrue(self.aprs.kiss_protocol.write.called)
        args, kwargs = self.aprs.kiss_protocol.write.call_args
        frame = args[0]
        self.assertIn(b':5B4AON-12:Hello APRS', frame.info)

    def test_send_my_message_no_ack_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )

    def test_send_my_message_no_ack_send_error(self):
        self.aprs.kiss_protocol.write.side_effect = Exception("fail")
        with self.assertRaises(AprsError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_mycall(self):
        # Not uppercase
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="n0call-1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )
        # Too short (less than 3 before dash)
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="AB-1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )
        # Too long (more than 6 before dash)
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="ABCDEFG-1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )
        # No dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL1",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )
        # Letters after dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-AA",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )
        # Too many digits after dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-123",
                path=["WIDE1-1"],
                recipient="5B4AON-9",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_recipient(self):
        # Not uppercase
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5b4aon-9",
                message="Hello"
            )
        # Too short (less than 3 before dash)
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="AB-1",
                message="Hello"
            )
        # Too long (more than 6 before dash)
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="ABCDEFG-1",
                message="Hello"
            )
        # No dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5B4AON9",
                message="Hello"
            )
        # Letters after dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5B4AON-AA",
                message="Hello"
            )
        # Too many digits after dash
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="N0CALL-1",
                path=["WIDE1-1"],
                recipient="5B4AON-123",
                message="Hello"
            )

    def test_send_my_message_no_ack_invalid_path(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="MYCALL",
                path="WIDE1-1",  # not a list
                recipient="DEST",
                message="Hello"
            )
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="MYCALL",
                path=[""],  # empty string in path
                recipient="DEST",
                message="Hello"
            )

    def test_send_my_message_no_ack_empty_message(self):
        """Test sending an empty message raises ValueError."""
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="MYCALL",
                path=["WIDE1-1"],
                recipient="DEST",
                message=""
            )

    def test_send_my_message_no_ack_message_too_long(self):
        """Test sending a message longer than 67 chars raises ValueError."""
        long_message = "A" * 68
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="MYCALL",
                path=["WIDE1-1"],
                recipient="DEST",
                message=long_message
            )

    def test_send_my_message_no_ack_message_not_str(self):
        """Test sending a non-string message raises ValueError."""
        with self.assertRaises(ValueError):
            self.aprs.send_my_message_no_ack(
                mycall="MYCALL",
                path=["WIDE1-1"],
                recipient="DEST",
                message=None
            )

    def test_send_my_object_no_course_speed_valid(self):
        self.aprs.send_my_object_no_course_speed(
            mycall="MYCALL",
            path=["WIDE1-1"],
            time_dhm="011234z",
            lat_dmm="5132.07N",
            long_dmm="00007.40W",
            symbol_id="/",
            symbol_code="O",
            comment="Test object"
        )
        self.assertTrue(self.aprs.kiss_protocol.write.called)
        args, kwargs = self.aprs.kiss_protocol.write.call_args
        frame = args[0]
        self.assertIn(b';MYCALL   *011234z5132.07N/00007.40WOTest object', frame.info)

    def test_send_my_object_no_course_speed_not_initialized(self):
        self.aprs.initialized = False
        with self.assertRaises(AprsError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_send_error(self):
        self.aprs.kiss_protocol.write.side_effect = Exception("fail")
        with self.assertRaises(AprsError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_mycall(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="mc",  # not uppercase
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_path(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path="WIDE1-1",  # not a list
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_time_dhm(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",  # missing 'z'
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="01123Az",  # not all digits before 'z'
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234zz",  # too long
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_lat_dmm(self):
        # Too short
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07",  # missing N/S and not 8 chars
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )
        # Wrong length
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.7N",  # only 7 chars
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )
        # Not ending with N/S
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="5132.07X",  # ends with X
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )
        # Not all digits before N/S (except dot)
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234z",
                lat_dmm="51A2.07N",  # contains A
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_long_dmm(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40",  # missing E/W
                symbol_id="/",
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_symbol_id(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="XY",  # too long
                symbol_code="O",
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_symbol_code(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="",  # too short
                comment="Test object"
            )

    def test_send_my_object_no_course_speed_invalid_comment(self):
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment="A" * 44  # too long
            )
        with self.assertRaises(ValueError):
            self.aprs.send_my_object_no_course_speed(
                mycall="MYCALL",
                path=["WIDE1-1"],
                time_dhm="011234",
                lat_dmm="5132.07N",
                long_dmm="00007.40W",
                symbol_id="/",
                symbol_code="O",
                comment=None  # not a string
            )

if __name__ == "__main__":
    unittest.main()