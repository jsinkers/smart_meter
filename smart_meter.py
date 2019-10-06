import csv
import datetime as dt
import glob
import os
import tempfile

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from config import email, password
from models import session, Nem12Record300, Nem12Record200, EnergyUsage


def get_num_readings(interval):
    return int(1440 / interval)


def enable_download_in_headless_chrome(browser, download_dir):
    """
    https://bugs.chromium.org/p/chromium/issues/detail?id=696481#c86
    add missing support for chrome "send_command"  to selenium webdriver
    :param browser: webdriver.Chrome instance
    :param download_dir: path to directory for downloads
    """
    browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

    params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    browser.execute("send_command", params)


def download_meter_csv(download_dir):
    """ Downloads smart meter CSV data to specified directory """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=960x540")
    driver = webdriver.Chrome(options=options)
    enable_download_in_headless_chrome(driver, download_dir)

    # log in
    driver.get("https://customermeterdata.portal.powercor.com.au/customermeterdata/")
    driver.find_element_by_class_name("ux-uPswd").send_keys(password)
    driver.find_element_by_class_name("ux-uName").send_keys(email)
    driver.find_element_by_xpath("//input[@value='Login']").click()

    # go to smart meter report page - goes to default NMI
    wait = WebDriverWait(driver, 30)
    btn_download_data = wait.until(ec.element_to_be_clickable((By.XPATH, "//button[text()='Download Data']")))
    btn_download_data.click()

    # request report
    wait = WebDriverWait(driver, 30)
    dropdown = wait.until(ec.element_to_be_clickable((By.ID, "reportType")))
    report = dropdown.find_element(By.XPATH,"//option[. = 'Detailed Report (CSV)']")
    report.click()

    # download CSV
    wait = WebDriverWait(driver, 30)
    request_meter_data = wait.until(ec.element_to_be_clickable((By.XPATH, "//input[@value='Request Meter Data']")))
    request_meter_data.click()
    wait = WebDriverWait(driver, 30)
    wait.until(ec.element_to_be_clickable((By.XPATH, "//input[@value='Request Meter Data']")))

    driver.quit()


def get_latest_file(pattern):
    """ find the most recent file using the search pattern """
    list_of_files = glob.iglob(pattern)
    return max(list_of_files, key=os.path.getctime)


def parse_nem12_csv(file):
    """
    Parse the NEM12 format csv file, add new data to the database
    :param file: filename
    """
    with open(file, newline='') as csv_file:
        reader = csv.reader(csv_file)
        unparsed_rows = []
        for row in reader:
            if row:
                print(row)
                # NMI data details
                if row[0] == "200":
                    smart_meter = parse_nem12_200record(row)
                # Interval data
                elif row[0] == "300":
                    parse_nem12_300record(row, smart_meter)
                else:
                    # handle other rows with headers.  add them to a list for later inspection
                    unparsed_rows.append(row)


def parse_nem12_200record(row):
    """ Parse an NMI details (200) record from a row of a NEM12 file"""
    record_indicator, nmi, _, _, _, _, meter_serial_num, units_of_measure, interval_length, _ = row
    assert (record_indicator == '200')
    assert (units_of_measure == "KWH")
    nem12_record200 = Nem12Record200(nmi=int(nmi),
                                     meter_serial_num=meter_serial_num,
                                     units_of_measure=units_of_measure,
                                     interval_length=int(interval_length))

    # check if it is in the database already.  add it if it isn't
    q = session.query(Nem12Record200).filter_by(nmi=nem12_record200.nmi)
    if q.count():
        nem12_record200 = q.first()
    else:
        session.add(nem12_record200)
        session.commit()

    return nem12_record200


def parse_nem12_300record(row, record_200):
    """ Parse an interval data (300) record from a row of a NEM12 file"""
    record_indicator, interval_date, *interval_vals, quality_method, reason_code, reason_description, update_datetime, \
    msats_load_datetime = row

    assert (record_indicator == '300')
    interval_length = record_200.interval_length
    num_readings = get_num_readings(interval_length)
    interval = dt.timedelta(seconds=60*interval_length)
    assert (len(interval_vals) == num_readings)

    # get timestamps for each interval value
    interval_date = dt.datetime.strptime(interval_date, "%Y%m%d")
    interval_dt = [interval_date + interval*i for i in range(0, num_readings)]

    reason_code = int(reason_code) if reason_code else None
    update_datetime = dt.datetime.strptime(update_datetime, "%Y%m%d%H%M%S")
    msats_load_datetime = dt.datetime.strptime(msats_load_datetime, "%Y%m%d%H%M%S") if msats_load_datetime else None

    kwargs = {"quality_method": quality_method,
              "reason_code": reason_code,
              "reason_description": reason_description,
              "update_datetime": update_datetime,
              "msats_load_datetime": msats_load_datetime}

    # check if it is in the database already.  add it if it isn't
    q = session.query(Nem12Record300).filter_by(record_200_id=record_200.id, update_datetime=update_datetime)
    if q.count():
        record_300 = q.first()
    else:
        record_300 = record_200.add_record300(**kwargs)
        for (timestamp, usage) in zip(interval_dt, interval_vals):
            kwargs = {"timestamp": timestamp, "energy_usage": float(usage)}
            record_300.add_energy_usage(**kwargs)

    return record_300


def main():
    temp_dir = tempfile.TemporaryDirectory()
    download_dir = temp_dir.name

    download_meter_csv(download_dir)

    # find downloaded csv by getting latest file
    meter_csv = get_latest_file(os.path.join(download_dir, "*.csv"))
    print(meter_csv)

    # read in csv and update database
    parse_nem12_csv(meter_csv)
    temp_dir.cleanup()

    # TODO: add price calculations
    # TODO: add CO2 calculations


if __name__ == "__main__":
    main()
