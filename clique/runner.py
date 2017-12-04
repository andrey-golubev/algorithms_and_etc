import argparse
import os
import csv
from enum import Enum

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-binary_exe', default='mlp',
                    help='Binary file that will be executed')
parser.add_argument('-data_folder', default='data',
                    help='Folder where data files (that describe graphs) are located')
parser.add_argument('-time_limit',
                    help='Integer value in [seconds] specifying time to wait for each run to finish')
parser.add_argument('-out_csv_file', default='mlp_res.csv',
                    help='File path which run results will be saved to')

if __name__ == "__main__":
    args = parser.parse_args()
    binary_path = os.path.abspath(args.binary_exe)
    data_path = os.path.abspath(args.data_folder)
    data_files = []
    for file in os.listdir(data_path):
        data_files.append(os.path.join(data_path, file))

    outputs = []
    import subprocess
    for file in data_files:
        print(file, "is started")
        startup_args = [binary_path, file, args.time_limit]
        popen = subprocess.Popen(startup_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        popen.wait()
        output, error = popen.communicate()
        if error:
            print("Error during run: ", error)
            continue
        outputs.append(output.decode('ascii'))
        print(file, "is finished")

    with open(args.out_csv_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')#fieldnames=list(row.keys()))
        writer.writerow(['File','Time(sec)','Max found clique size',"File Description"])
        file_num = 1
        for out, file in zip(outputs, data_files):
            time_and_max_size = out.split(" ")[:2]
            if len(time_and_max_size) < 2:
                print("Failed on file:", file)
                continue
            time, max_size = time_and_max_size
            import ntpath
            writer.writerow([ntpath.basename(file), time, max_size, ""])
