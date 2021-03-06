import csv
import os
import sys
import io
import subprocess
import time
import datetime
import socket

if __name__ == '__main__':

  # Define the parser
  import argparse
  parser = argparse.ArgumentParser(description="QC8 data analysis step 5. Software alignment of the chambers in the stand. For any doubt: https://twiki.cern.ch/twiki/bin/view/CMS/GEMCosmicRayAnalysis")
  # Positional arguments
  parser.add_argument("run_number", type=int, help="Specify the run number")
  # Optional arguments
  parser.add_argument("--steps", type=int, default=5, help="You can set the preferred number of steps to be executed for the iterative alignment. If not specified, the default value is 5.")
  args = parser.parse_args()

  # Different paths definition
  srcPath = os.path.abspath("launcher_alignment.py").split('QC8Test')[0]+'QC8Test/src/'
  pyhtonModulesPath = os.path.abspath("launcher_alignment.py").split('QC8Test')[0]+'QC8Test/src/Analysis/GEMQC8/python/'
  runPath = os.path.abspath("launcher_alignment.py").split('QC8Test')[0] + 'QC8Test/src/Analysis/GEMQC8/test/'
  dataPath = os.path.abspath("launcher_alignment.py").split('QC8Test')[0] + 'QC8Test/src/Analysis/GEMQC8/data/'
  outDirPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0] + "Results_QC8_alignment_run_" + str(args.run_number)

  sys.path.insert(0,pyhtonModulesPath)

  import dumpDBtables
  import config_creator
  import geometry_files_creator
  import convertAlignmentTables

  # Retrieve start date and time of the run

  if (socket.gethostname()=="gem904qc8dqm"):

        fpath =  "/data/bigdisk/GEM-Data-Taking/GE11_QC8/Cosmics/run{:06d}/".format(int(args.run_number))
        for x in os.listdir(fpath):
            if x.endswith("ls0001_index000000.raw"):
                file0name = x
                break
            elif x.endswith("chunk_000000.dat"):
                file0name = x
                break
        if (not file0name.endswith("ls0001_index000000.raw") and not file0name.endswith("chunk_000000.dat")):
            print "Check the data files... First file (at least) is missing!"
        t = datetime.datetime.fromtimestamp(os.path.getmtime(fpath+file0name))
        startDateTime = str("{:04d}".format(int(t.year))) + "-" + str("{:02d}".format(int(t.month))) + "-" + str("{:02d}".format(int(t.day))) + "_" + str("{:02d}".format(int(t.hour))) + "-" + str("{:02d}".format(int(t.minute))) + "-" + str("{:02d}".format(int(t.second)))
        time.sleep(1)

  else:

      fpath =  "/eos/cms/store/group/dpg_gem/comm_gem/QC8_Commissioning/run{:06d}/".format(int(args.run_number))
      for x in os.listdir(fpath):
          if x.endswith("ls0001_allindex.raw"):
              file0name = x
              break
          elif x.endswith("chunk_000000.dat"):
              file0name = x
              break
      if (not file0name.endswith("ls0001_index000000.raw") and not file0name.endswith("chunk_000000.dat")):
          print "Check the data files... First file (at least) is missing!"
      startDateTime = file0name.split('_')[3] + "_" + file0name.split('_')[4]
      time.sleep(1)

  # Get stand configuration table from the DB
  if (int(args.run_number) > 237 and int(args.run_number) < 266) or (int(args.run_number) > 272):
      dumpDBtables.getConfigurationTable(args.run_number,startDateTime)

  # Generate configuration file
  config_creator.configMaker(args.run_number,"yesMasks")
  time.sleep(1)

  # Generate geometry files
  geometry_files_creator.geomMaker(args.run_number, "noAlignment")
  time.sleep(1)

  # Creating folder outside the CMMSW release to put the output files and plots
  #---# Remove old version if want to recreate
  if (os.path.exists(outDirPath)):
      rmDirCommand = "rm -rf "+outDirPath
      rmDir = subprocess.Popen(rmDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True)
      rmDir.communicate()
  #---# Create the new empty folder
  resDirCommand = "mkdir "+outDirPath
  resDir = subprocess.Popen(resDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True)
  resDir.communicate()
  time.sleep(1)

  for step in range(args.steps):

    # Compiling after the generation of the geometry files
    scramCommand = "scram build -j 4"
    scramming = subprocess.Popen(scramCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=srcPath)
    while scramming.poll() is None:
      line = scramming.stdout.readline()
      print(line)
    print scramming.stdout.read()
    scramming.communicate()
    time.sleep(1)

    # Running the CMSSW code
    runCommand = "cmsRun -n 8 runGEMCosmicStand_alignment.py"
    running = subprocess.Popen(runCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=runPath)
    while running.poll() is None:
        line = running.stdout.readline()
        print(line)
    print running.stdout.read()
    running.communicate()
    time.sleep(1)

    # Create the new empty folder for this step
    outDirPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0] + "Results_QC8_alignment_run_" + str(args.run_number) + "/AlignmentStep" + str(step)
    resDirCommand = "mkdir "+outDirPath
    resDir = subprocess.Popen(resDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True)
    resDir.communicate()
    time.sleep(1)

    # Selecting the correct output file, changing the name and moving to the output folder
    out_name = 'out_run_'
    for i in range(6-len(str(args.run_number))):
      out_name = out_name + '0'
    out_name = out_name + str(args.run_number) + '.root'

    mvToDirCommand = "mv alignment_" + out_name + " " + outDirPath + "/alignment_" + out_name
    movingToDir = subprocess.Popen(mvToDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=runPath)
    movingToDir.communicate()
    time.sleep(1)

    # Alignment computation & output
    alignCommand = "root -l -q -b " + runPath + "macro_alignment.c(" + str(args.run_number) + ",\"" + dataPath + "\"," + str(step) + ")"
    alignment = subprocess.Popen(alignCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=outDirPath)
    while alignment.poll() is None:
      line = alignment.stdout.readline()
      print(line)
    print alignment.stdout.read()
    alignment.communicate()
    time.sleep(1)

    # Moving the output of the root analysis to the folder in GEMQC8/data/..
    out_name = 'StandAlignmentValues_run' + str(args.run_number) + '_ToDB.csv'
    mvToDirCommand = "cp " + outDirPath + "/" + out_name + " " + dataPath + "StandAligmentTables/" + out_name
    movingToDir = subprocess.Popen(mvToDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=runPath)
    movingToDir.communicate()
    time.sleep(1)

    # Converting tables ToDB-like into FromDB-like
    convertAlignmentTables.convertAlignment(args.run_number,"alignment")

    # Generate geometry files
    geometry_files_creator.geomMaker(args.run_number, "yesAlignment")
    time.sleep(1)
