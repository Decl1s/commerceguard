"""Я проверяю границу stdin импорта, не финансовые правила повторно."""
import io
from pathlib import Path
import struct
import tempfile
import unittest
from deploy.transfer import receive,send

class TransferTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'m').write_bytes(b'{}');(root/'d').write_bytes(b'row\n')
            data=io.BytesIO();send(data,root/'m',root/'d');data.seek(0)
            out=root/'out';out.mkdir();paths=receive(data,out)
            self.assertEqual([p.read_bytes() for p in paths],[b'{}',b'row\n'])
    def test_rejects_invalid_frames(self):
        for raw in (b'CGI1',b'XXXX'+b'0'*8,b'CGI1'+struct.pack('!II',64001,0),b'CGI1'+struct.pack('!II',0,0)+b'extra'):
            with self.subTest(raw=raw),tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):receive(io.BytesIO(raw),Path(tmp))
