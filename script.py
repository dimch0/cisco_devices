import os


# DEFINES
dir_all = "/home/dzhrt/cisco_devs/all"
extension = ".txt"
all_files = []

for root, dirs, files in os.walk(dir_all, topdown=False):
    for name in files:
        all_files.append(str(os.path.join(root, name)))

# print all_files

for file in all_files:
    if file.endswith(extension):

        with open(file, "r") as f:
            print "FILE", file
            for line in f:
                line = line.split()
                for i, item in enumerate(line):
                    if item == 'PID:':
                        PID = line[i+1]
                        print "PID", PID
                    if item == 'SN:':
                        SN = line[-1]
                        print "SN", SN





#1. TODO: from PGImaster.xls get: cisco_files = ["directory/file1", "directory/file2"...]
#2. TODO: from PGImaster.xls get: juniper_files = ["directory/file1", "directory/file2"...]
#3. TODO: from cisco files get: cisco_dict = {"SystemName": [(PID, SN), (PID, SN) ...]}
#4. TODO: from juniper_files get: juniper_dict = {"SystemName": [(PID, SN), (PID, SN) ...]}
#5. TODO:
#6. TODO:
#7. TODO:
#8. TODO:
