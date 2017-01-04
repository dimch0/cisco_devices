import os
import re
import sys
from xlrd import open_workbook


# DEFINES:
master_file = 'PGiMaster.xls'
dir_all = "/home/dimcho/Desktop/c/PGI_all"
extension = ".txt"
wb = open_workbook(master_file)
version_pattern = "(^.*(REV|rev|Rev)\s\d\d+)"


def read_master_excel(wb):
    excel_rows = []
    for s in wb.sheets():
        for row in range(1, s.nrows):
            col_names = s.row(0)
            col_value = []
            for name, col in zip(col_names, range(s.ncols)):
                value  = (s.cell(row,col).value)
                try : value = str(int(value))
                except : pass
                col_value.append((name.value, value))
            excel_rows.append(col_value)
    return excel_rows


def cisco_vs_juni_names(wb):
    cisco_names = []
    juniper_names = []
    other_devices = []
    for row in read_master_excel(wb):
        device_type = row[3][1]
        system_name = row[4][1]
        if 'Cisco' in device_type:
            cisco_names.append(system_name)
        elif 'Juniper' in device_type:
            juniper_names.append(system_name)
        else:
            other_devices.append(system_name)

    return cisco_names, juniper_names, other_devices


all_files = []
for root, dirs, files in os.walk(dir_all, topdown=False):
    for name in files:
        if name.endswith(extension):
            all_files.append(str(os.path.join(root, name)))


def cisco_vs_juniper_files():
    cisco_file_list = []
    juniper_file_list = []
    for file in all_files:
        if file.endswith(extension):
            with open(file, "r") as f:
                content = f.read()
                if "Hardware inventory:" in content:
                    juniper_file_list.append(file)
                else:
                    cisco_file_list.append(file)
    return cisco_file_list, juniper_file_list


def cisco_reader(dir_to_file):
    file_name = os.path.basename(dir_to_file).replace(extension, '')
    print file_name
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
                    print "Error: Could not print PID, SN", e, "in file: ", file_name
            if pid or sn:
                if not sn:
                    sn = "NO_SN_FOUND"
                print "space", pid, sn


def juniper_reader(dir_to_file):
    with open(dir_to_file, "r") as f:
        file_name = os.path.basename(dir_to_file).replace(extension, '')
        print file_name
        for line in f:
            line = line.split('   ')
            for i, item in enumerate(line):
                if re.match(version_pattern, item):
                    print "space", line[i+1], line[i+2]




def main():

    cisco_file_list, juniper_file_list = cisco_vs_juniper_files()
    set_cisco_files = set([os.path.basename(a).replace(extension, '') for a in cisco_file_list])
    set_juniper_files = set([os.path.basename(a).replace(extension, '') for a in juniper_file_list])


    cisco_names, juniper_names, other_devices = cisco_vs_juni_names(wb)
    set_cisco_names = set([os.path.basename(a).replace(extension, '') for a in cisco_names])
    set_juniper_names = set([os.path.basename(a).replace(extension, '') for a in juniper_names])


    missing_files_for_cisco = set_cisco_names - set_cisco_files
    missing_files_for_juniper = set_juniper_names - set_juniper_files

    missing_names_for_cisco = set_cisco_files - set_cisco_names
    missing_names_for_juniper = set_juniper_files - set_juniper_names



    # cisco_file_list, juniper_file_list = cisco_vs_juniper_files()
    # set_cisco_files = set([os.path.basename(a).replace(extension, '') for a in cisco_file_list])
    # set_juniper_files = set([os.path.basename(a).replace(extension, '') for a in juniper_file_list])
    #
    #
    # cisco_names, juniper_names, other_devices = cisco_vs_juni_names(wb)
    # set_cisco_names = set([os.path.basename(a).replace(extension, '') for a in cisco_names])
    # set_juniper_names = set([os.path.basename(a).replace(extension, '') for a in juniper_names])





    # print "missing_names_for_cisco"
    # for file in missing_names_for_cisco:
    #     cisco_reader(file)

    # print "missing_names_for_juniper"
    # for file in missing_names_for_juniper:
    #     cisco_reader(file)

    # print "missing_files_for_cisco"
    # for file in missing_files_for_cisco:
    #     print file

    # print "missing_files_for_juniper"
    # for file in missing_files_for_juniper:
    #     print file

    # print "CISCO FILES"
    # for file in cisco_file_list:
    #     cisco_reader(file)

    # print "JUNIPER FILES"
    # for file in juniper_file_list:
    #     juniper_reader(file)


    print "\n" + "="*50 + "\nChecking for non-Cisco non-Juniper devices..."
    other_devices_found = False
    for device in other_devices:
        if device:
            other_devices_found = True
            print device
    if not other_devices_found:
        print "No other devices found"
    print "="*50


    print "\n" + "=" * 22
    print "all_files:", len(all_files)
    print "cisco_file_list:", len(cisco_file_list)
    print "juniper_file_list:", len(juniper_file_list)
    print "sum files =", len(cisco_file_list) + len(juniper_file_list)
    print "\n"
    print "cisco_names:", len(cisco_names)
    print "juniper_names:", len(juniper_names)
    print "sum names =", len(cisco_names) + len(juniper_names)
    print "\n"
    print "missing_files_for_cisco:", len(missing_files_for_cisco)
    print "missing_files_for_juniper:", len(missing_files_for_juniper)
    print "missing_names_for_cisco:", len(missing_names_for_cisco)
    print "missing_names_for_juniper:", len(missing_names_for_juniper)



if __name__ == '__main__':
    main()
    sys.exit()
