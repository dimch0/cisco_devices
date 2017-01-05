import os
import re
import sys
import xlsxwriter
from xlrd import open_workbook


# DEFINES:
MASTER_FILE = 'PGiMaster.xls'
CONTAINER_ALL_FILES = "/home/dzhrt/PycharmProjects/untitled/pyt/cisco_devices/PGI"
EXTENSION = ".txt"
VERSION_PATTERN = "(^.*(REV|rev|Rev)\s\d\d+)"


def load_data_from_v_file(file_name):
    """
    :param file_name:  takes the path to the excel master file
    :return: a list of lists for each row in the excel master file
    """
    wb = open_workbook(file_name)
    first_sheet = wb.sheet_by_index(0)
    num_rows = first_sheet.nrows
    data = []
    for row in range(0, num_rows):
        data.append(first_sheet.row_values(row))
    return data


def cisco_vs_juniper_excel_entries(MASTER_FILE):
    """
    :param file_name: takes the path to the excel master file
    :return: 3 lists for cisco, juniper and other devices,
             specified in column D from the master excelfile
    """
    cisco_names = []
    juniper_names = []
    other_devices = []
    for row in load_data_from_v_file(MASTER_FILE):
        device_type = row[3]
        system_name = row[4]
        if 'Cisco' in device_type:
            cisco_names.append(system_name.strip())
        elif 'Juniper' in device_type:
            juniper_names.append(system_name.strip())
        else:
            other_devices.append(system_name.strip())

    return cisco_names, juniper_names, other_devices

def get_all_files(path_to_folder):
    """
    :param path_to_folder: full path to the folder to be searched for all files
    :return:  a list, with all full paths to each of the files inside the folder
    """
    result = []
    for root, dirs, files in os.walk(path_to_folder, topdown=False):
        for name in files:
            if name.endswith(EXTENSION):
                result.append(str(os.path.join(root, name)))
    return result


def cisco_vs_juniper_files():
    """
    Checks all the files for a indicating string
    :return: two lists (for cisco and juniper) with the full paths to each of the files
    """
    indicating_string = "Hardware inventory:"
    cisco_file_list = []
    juniper_file_list = []
    for file in get_all_files(CONTAINER_ALL_FILES):
        if file.endswith(EXTENSION):
            with open(file, "r") as f:
                content = f.read()
                if indicating_string in content:
                    juniper_file_list.append(file)
                else:
                    cisco_file_list.append(file)
    return cisco_file_list, juniper_file_list


def cisco_reader(dir_to_file):
    """
    :param dir_to_file: path to cisco file be checked
    :return:  a list of tuples with PIDs and SNs: [(pid, sn), (pid, sn), (pid, sn)...]
    """
    file_name = os.path.basename(dir_to_file).replace(EXTENSION, '')
    result = []
    with open(dir_to_file, "r") as f:
        for line in f:
            pid = None
            sn = None
            line = line.split()
            for i, item in enumerate(line):
                try:
                    if item == 'PID:':
                        pid = line[i+1]
                    if item == 'SN:' and len(line) > i + 1:
                        sn = line[i+1]
                except Exception as e:
                    print "Error: Could not print cisco PID, SN", e, "in file: ", file_name
            if pid or sn:
                if not sn:
                    sn = "Unspecified"
                if not pid:
                    pid = "Unspecified"
                result.append((pid, sn))
    return result


def juniper_reader(dir_to_file):
    """
    :param dir_to_file: path to cisco file be checked
    :return:  a list of tuples with PIDs and SNs: [(pid, sn), (pid, sn), (pid, sn)...]
    """
    result = []
    with open(dir_to_file, "r") as f:
        for line in f:
            pid = None
            sn = None
            line = line.split('   ')
            for i, item in enumerate(line):
                try:
                    if re.match(VERSION_PATTERN, item):
                        pid, sn = line[i+1], line[i+2]
                        sn = line[i+2]
                except Exception as e:
                    print "Error: Could not print juniper PID, SN", e, "in file: ", file_name
            if pid or sn:
                if not sn:
                    sn = "Unspecified"
                if not pid:
                    pid = "Unspecified"
                result.append((pid, sn))
    return result


def create_dict(file_list, reader):
    """
    :param file_list: list of cisco or juniper files
    :param reader: function that reads cisco or juniper files
    :return:  a dict with the name of the file as a key and list of paris (pid, sn) for value:
    {"file_name_1": [(pid, sn),(pid, sn),(pid, sn)...]}
    """
    result = {}
    for file in file_list:
        name = os.path.basename(file).replace(EXTENSION, '')
        pairs = reader(file)
        result[name] = pairs
    return result


def write_to_excel_file(data, sheet, header):
    """
    :param data: list of lists for each row to be written in xls file
    :param sheet: sheet to be written
    :param header: format the header for columns in the excel
    :return:
    """
    for row in range(0, len(data)):
        for col in range(0, len(data[row])):
            if row == 0:
                sheet.write(row, col, data[row][col], header)
            else:
                sheet.write(row, col, data[row][col])
    return 1


def write_missing_entries(missing_names_list, all_dict, sheet, header):
    """
    This function writes a sheet in excel with the missing entries from the master
    :param missing_names_list: a list of the missing cisco or juniper entries
    :param sheet: the sheet in the excel file to be written
    :param all_dict: a dict containing all the pid and SNs for cisco + juniper
    :return:
    """
    missing_entries = [["SystemName", "Component", "Component Serial"]]
    for name in all_dict.keys():
        if name in missing_names_list:
            missing_entries.append([name, "", ""])
            for pid, sn in all_dict[name]:
                missing_entries.append(["", pid, sn])

    write_to_excel_file(missing_entries, sheet, header)


def main():
    # CREATING CISCO AND JUNIPER FILE LISTS
    cisco_file_list, juniper_file_list = cisco_vs_juniper_files()
    cisco_names, juniper_names, other_devices = cisco_vs_juniper_excel_entries(MASTER_FILE)

    # CREATING SETS FOR CISCO AND JUNIPER TO FIND DIFF
    set_cisco_files = set(os.path.basename(item).replace(EXTENSION, '') for item in cisco_file_list)
    set_juniper_files = set(os.path.basename(item).replace(EXTENSION, '') for item in juniper_file_list)
    missing_names_for_cisco = set_cisco_files - set(cisco_names)
    missing_names_for_juniper = set_juniper_files - set(juniper_names)

    # CREATING DICT WITH ALL ENTRIES FOR CISCO AND JUNIPER
    all_dict = {}
    all_dict.update(create_dict(cisco_file_list, cisco_reader))
    all_dict.update(create_dict(juniper_file_list, juniper_reader))

    # PREPARING TO WRITE NEW DATA
    combined_file_name = "PGiMaster_UPDATED.xlsx"
    workbook = xlsxwriter.Workbook(combined_file_name)
    worksheet = workbook.add_worksheet()
    worksheet_2 = workbook.add_worksheet("extra_cisco_files")
    worksheet_3 = workbook.add_worksheet("extra_juniper_files")
    format_header = workbook.add_format({'bold': True, 'font_color': 'black'})

    # CREATING THE UPDATED DATA FILE LIST TO BE WRITTEN
    old_data = load_data_from_v_file(MASTER_FILE)
    updated_data = []
    pre_row = ['' for i in range(8)]
    post_row = ['' for i in range(7)]
    for row in old_data:
        SYSTEM_NAME = row[4]
        COMPONENT = row[8]
        COMPONENT_SERIAL = row[9]
        if SYSTEM_NAME:
            if SYSTEM_NAME in all_dict.keys():
                updated_data.append(row)
                for pair in all_dict[SYSTEM_NAME]:
                    mid_list = [pair[0], pair[1]]
                    updated_row = pre_row + mid_list + post_row
                    updated_data.append(updated_row)
            elif SYSTEM_NAME not in all_dict.keys():
                if not COMPONENT:
                    COMPONENT = "NO_FILE"
                if not COMPONENT_SERIAL:
                    COMPONENT_SERIAL = "NO_FILE"
                updated_data.append(row)
            else:
                updated_data.append(row)

    # WRITING UPDATED FILE
    write_to_excel_file(updated_data, worksheet, format_header)

    # WRITING MISSING CISCO ENTRIES
    write_missing_entries(missing_names_for_cisco, all_dict, worksheet_2, format_header)
    
    # WRITING MISSING JUNIPER ENTRIES
    write_missing_entries(missing_names_for_juniper, all_dict, worksheet_3, format_header)

    # CHECK FOR OTHER DEVICES
    print "\n" + "="*50 + "\nChecking for non-Cisco non-Juniper devices..."
    other_devices_found = False
    for device in other_devices:
        if device:
            other_devices_found = True
            print "Other devices found:"
            print device
    if not other_devices_found:
        print "No other devices found"
    print "="*50
    # STATISTICS
    print "\n"+"="*50
    print "cisco files: {}".format(len(cisco_file_list))
    print "juniper files: {}".format(len(juniper_file_list))
    print "="*50
    print "\n"+"="*50
    print "cisco entries in excel: {}".format(len(cisco_names))
    print "juniper entries in excel: {}".format(len(juniper_names))
    print "="*50


if __name__ == '__main__':
    main()
    sys.exit()
