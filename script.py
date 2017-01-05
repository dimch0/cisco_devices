import os
import re
import sys
import xlsxwriter
from xlrd import open_workbook


# DEFINES:
master_file = 'PGiMaster.xls'
container_all_files = "/home/dimcho/PycharmProjects/dzhrt/cis/PGI_all"
extension = ".txt"
version_pattern = "(^.*(REV|rev|Rev)\s\d\d+)"


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


def cisco_vs_juniper_excel_entries(master_file):
    """
    :param file_name: takes the path to the excel master file
    :return: 3 lists for cisco, juniper and other devices,
             specified in column D from the master excelfile
    """
    cisco_names = []
    juniper_names = []
    other_devices = []
    for row in load_data_from_v_file(master_file):
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
            if name.endswith(extension):
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
    for file in get_all_files(container_all_files):
        if file.endswith(extension):
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
    file_name = os.path.basename(dir_to_file).replace(extension, '')
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
                    if re.match(version_pattern, item):
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
        name = os.path.basename(file).replace(extension, '')
        pairs = reader(file)
        result[name] = pairs
    return result


def write_missing_entries(missing_names_list, all_dict, wsheet, header):
    """
    This function writes a sheet in excel with the missing entries from the master
    :param missing_names_list: a list of the missing cisco or juniper entries
    :param wsheet: the sheet in the excel file to be written
    :param all_dict: a dict containing all the pid and SNs for cisco + juniper
    :return:
    """
    missing_entries = [["SystemName", "Component", "Component Serial"]]
    for name in all_dict.keys():
        if name in missing_names_list:
            missing_entries.append([name, "", ""])
            for pid, sn in all_dict[name]:
                missing_entries.append(["", pid, sn])

    for row in range(0, len(missing_entries)):
        for col in range(0, len(missing_entries[row])):
            if row == 0:
                wsheet.write(row, col, missing_entries[row][col], header)
            else:
                wsheet.write(row, col, missing_entries[row][col])
    return 1


def main():

    cisco_file_list, juniper_file_list = cisco_vs_juniper_files()
    cisco_names, juniper_names, other_devices = cisco_vs_juniper_excel_entries(master_file)

    set_cisco_files = set([os.path.basename(a).replace(extension, '') for a in cisco_file_list])
    set_juniper_files = set([os.path.basename(a).replace(extension, '') for a in juniper_file_list])
    set_cisco_names = set([os.path.basename(a).replace(extension, '') for a in cisco_names])
    set_juniper_names = set([os.path.basename(a).replace(extension, '') for a in juniper_names])
    missing_files_for_cisco = set_cisco_names - set_cisco_files
    missing_files_for_juniper = set_juniper_names - set_juniper_files
    missing_names_for_cisco = set_cisco_files - set_cisco_names
    missing_names_for_juniper = set_juniper_files - set_juniper_names


    cisco_dict = create_dict(cisco_file_list, cisco_reader)
    juniper_dict = create_dict(juniper_file_list, juniper_reader)


    all_dict = {}
    all_dict.update(cisco_dict)
    all_dict.update(juniper_dict)


    # Writing the updated file
    combined_file_name = "PGiMaster_UPDATED.xlsx"
    workbook = xlsxwriter.Workbook(combined_file_name)
    worksheet = workbook.add_worksheet()
    worksheet_c = workbook.add_worksheet("extra_cisco_files")
    worksheet_j = workbook.add_worksheet("extra_juniper_files")
    format_header = workbook.add_format({'bold': True, 'font_color': 'black'})
    master_data = load_data_from_v_file(master_file)
    updated_data = []
    pre_list = ['' for i in range(8)]
    post_list = ['' for i in range(7)]
    for row in master_data:
        system_name = row[4]
        if system_name:
            if system_name in all_dict.keys():
                updated_data.append(row)
                for pair in all_dict[system_name]:
                    mid_list = [pair[0], pair[1]]
                    updated_row = pre_list + mid_list + post_list
                    updated_data.append(updated_row)
            elif system_name not in all_dict.keys():
                if not row[8]:
                    row[8] = "NO_FILE"
                if not row[9]:
                    row[9] = "NO_FILE"
                updated_data.append(row)
            else:
                updated_data.append(row)

    # WRITING UPDATED FILE
    for row in range(0, len(updated_data)):
        for col in range(0, len(updated_data[row])):
            if row == 0:
                worksheet.write(row, col, updated_data[row][col], format_header)
            else:
                worksheet.write(row, col, updated_data[row][col])


    # WRITING MISSING CISCO ENTRIES
    write_missing_entries(missing_names_for_cisco, all_dict, worksheet_c, format_header)
    # WRITING MISSING JUNIPER ENTRIES
    write_missing_entries(missing_names_for_juniper, all_dict, worksheet_j, format_header)
    # MISSING CISCO ENTRIES


    # OTHER DEVICES CHECK
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
    print "\n" + "=" * 50
    print "cisco files:", len(cisco_file_list)
    print "juniper files:", len(juniper_file_list)
    print "total count files:", len(cisco_file_list) + len(juniper_file_list)
    print "=" * 50
    print "\n" + "=" * 50
    print "cisco entries in excel:", len(cisco_names)
    print "juniper entries in excel:", len(juniper_names)
    print "total count in excel:", len(cisco_names) + len(juniper_names)
    print "=" * 50
    print "\n" + "=" * 50
    print "missing files for cisco:", len(missing_files_for_cisco)
    print "missing files for juniper", len(missing_files_for_juniper)
    print "extra files for cisco:", len(missing_names_for_cisco)
    print "extra files for juniper:", len(missing_names_for_juniper)
    print "=" * 50


if __name__ == '__main__':
    main()
    sys.exit()
