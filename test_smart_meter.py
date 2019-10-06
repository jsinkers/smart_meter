import datetime as dt
from glob import glob
import os
import tempfile
import unittest

from smart_meter import download_meter_csv, parse_nem12_csv, parse_nem12_200record, parse_nem12_300record


class TestDownloadCSV(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_download_meter_csv(self):
        download_meter_csv(self.temp_dir.name)
        # check csv present
        self.assertTrue(glob(os.path.join(self.temp_dir.name, "*.csv")))

    def test_parse_nem12_csv(self):
        csv_file = os.path.join("test", "61029204720_20190809_20190913_20190913090841_CITIPOWER_DETAILED.csv")
        output = parse_nem12_csv(csv_file)
        self.assertEqual(output.nem12_300_records[-1].energy_usage[-1].timestamp,
                         dt.datetime(year=2019, month=9, day=12, hour=23, minute=30))
        self.assertEqual(output.nem12_300_records[-1].energy_usage[-1].usage, 0.121)

    def test_parse_nem12_200record(self):
        row = "200, 6102920472, E1, E1, E1,, A0804565, KWH, 30,".split(',')
        row = [item.strip() for item in row]
        smart_meter = parse_nem12_200record(row)
        self.assertEquals(smart_meter.nmi, 6102920472)
        self.assertEquals(smart_meter.meter_serial_num, "A0804565")
        self.assertEquals(smart_meter.units_of_measure, "KWH")
        self.assertEquals(smart_meter.interval_length, dt.timedelta(seconds=30*60))
        self.assertEquals(smart_meter.num_readings, 48)
        self.assertEquals(smart_meter.nem12_300_records, [])

    def test_parse_nem12_300record(self):
        # read in 300 record
        row = "300,20190809,0.435,0.673,0.048,0.053,0.025,0.044,0.874,0.042,0.020,0.042,0.021,0.041,0.027,0.034,0.032,0.031,1.554,0.140,0.045,0.028,0.056,0.071,0.089,0.084,0.032,0.064,0.623,1.015,0.594,0.550,0.541,0.506,0.161,0.823,0.063,0.398,0.715,0.694,0.733,0.699,0.729,0.710,0.719,0.623,1.301,1.431,0.794,0.807,A,,,20190810040147,"
        row = row.split(',')
        record = parse_nem12_300record(row, dt.timedelta(seconds=30*60))
        self.assertEqual(record.quality_method, "A")
        self.assertEqual(record.energy_usage[0].timestamp, dt.datetime(year=2019, month=8, day=9, hour=0, minute=0,
                                                                       second=0))
        self.assertEqual(record.energy_usage[0].usage, 0.435)
        self.assertEqual(record.energy_usage[-1].timestamp, dt.datetime(year=2019, month=8, day=9, hour=23, minute=30,
                                                                        second=0))
        self.assertEqual(record.energy_usage[-1].usage, 0.807)


if __name__ == '__main__':
    unittest.main()
