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
    parser = argparse.ArgumentParser(description="QC8 data analysis step 6. Efficiency calculation with track-based analysis. For any doubt: https://twiki.cern.ch/twiki/bin/view/CMS/GEMCosmicRayAnalysis")
    # Positional arguments
    parser.add_argument("run_number", type=int, help="Specify the run number")
    parser.add_argument("alignmentDone", type=str, choices=["noAlignment","yesAlignment"], help="Specify if there is alignment done or not")
    parser.add_argument("hotdeadStripsMasking", type=str, choices=["noMasks","yesMasks"], help="Specify if there hot/dead strips masking has to be performed or not")
    args = parser.parse_args()

    # Different paths definition
    srcPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0]+'QC8Test/src/'
    pyhtonModulesPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0]+'QC8Test/src/Analysis/GEMQC8/python/'
    runPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0] + 'QC8Test/src/Analysis/GEMQC8/test/'
    dataPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0] + 'QC8Test/src/Analysis/GEMQC8/data/'
    outDirPath = os.path.abspath("launcher_validation.py").split('QC8Test')[0] + "Results_QC8_validation_run_"+str(args.run_number)+"_"+str(args.hotdeadStripsMasking)

    sys.path.insert(0,pyhtonModulesPath)

    import dumpDBtables
    import config_creator
    import geometry_files_creator

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
    config_creator.configMaker(args.run_number,args.hotdeadStripsMasking)
    time.sleep(1)

    # Generate geometry files
    geometry_files_creator.geomMaker(args.run_number,args.alignmentDone)
    time.sleep(1)

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
    runCommand = "cmsRun -n 8 runGEMCosmicStand_validation.py"
    running = subprocess.Popen(runCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=runPath)
    while running.poll() is None:
        line = running.stdout.readline()
        print(line)
    print running.stdout.read()
    running.communicate()
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

    # Create folders for ouput plots per chamber
    import configureRun_cfi as runConfig
    SuperChType = runConfig.StandConfiguration
    ChID = runConfig.ChamberIDs
    for i in range (0,30):
        if (SuperChType[int(i/2)] != '0'):
            plotsDirCommand = "mkdir outPlots_Chamber_Pos_" + str(i) + "_" + ChID[i]
            plotsDirChamber = subprocess.Popen(plotsDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=outDirPath)
            plotsDirChamber.communicate()
    time.sleep(1)

    # Selecting the correct output file, changing the name and moving to the output folder
    out_name = 'out_run_'
    for i in range(6-len(str(args.run_number))):
        out_name = out_name + '0'
    out_name = out_name + str(args.run_number) + '.root'

    mvToDirCommand = "mv validation_" + out_name + " " + outDirPath + "/validation_" + out_name
    movingToDir = subprocess.Popen(mvToDirCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=runPath)
    movingToDir.communicate()
    time.sleep(1)

    # Efficiency computation & output
    rootMacroCommand = "root -l -q -b " + runPath + "macro_validation.c(" + str(args.run_number) + ",\"" + dataPath + "\",\"" + startDateTime + "\")"
    rootMacroProcess = subprocess.Popen(rootMacroCommand.split(),stdout=subprocess.PIPE,universal_newlines=True,cwd=outDirPath)
    while rootMacroProcess.poll() is None:
        line = rootMacroProcess.stdout.readline()
        print(line)
    print rootMacroProcess.stdout.read()
    rootMacroProcess.communicate()
    time.sleep(1)
