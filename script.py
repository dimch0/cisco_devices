import os
from xlrd import open_workbook


master_file = 'PGiMaster.xls'
excel_rows = []
cisco_files = []
juniper_files = []
other_devices = []
dir_all = "/home/dzhrt/cisco"
extension = ".txt"
all_files = []
wb = open_workbook(master_file)


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


for row in excel_rows:
    device_type = row[3][1]
    system_name = row[4][1]
    if 'Cisco' in device_type:
        cisco_files.append(system_name)
    elif 'Juniper' in device_type:
        juniper_files.append(system_name)
    else:
        other_devices.append(system_name)

for root, dirs, files in os.walk(dir_all, topdown=False):
    for name in files:
        all_files.append(str(os.path.join(root, name)))


def cisco_reader(dir_to_file):
    result = {}
    with open(dir_to_file, "r") as f:
        file_name = os.path.basename(dir_to_file).replace(extension, '')
        for line in f:
            pid = None
            sn = None
            line = line.split()
            for i, item in enumerate(line):
                if item == 'PID:':
                    pid = line[i+1]
                    print "pid", pid
                try:
                    if item == 'SN:':
                        sn = line[i+1]
                        print "sn", sn
                except Exception as e:
                    print "KURWA", e

            if not file_name in result:
                result[file_name] = []
            if pid or sn:
                result[file_name].append((pid, sn))
    return result


# for c_file in cisco_files:
#     print c_file


for c in cisco_files:
    for dir_file in all_files:
        if c in os.path.basename(dir_file).replace(extension, ''):
            print cisco_reader(dir_file)
        # else:
        #     print "Nema bace"

