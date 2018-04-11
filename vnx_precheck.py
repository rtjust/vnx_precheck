#!/usr/bin/env python
# *-* coding:utf-8 *-*

import subprocess
import re
from datetime import timedelta, datetime
import time
import sys
import os
import getpass
import shutil


if 'nt' in os.name:
    # Windows Naviseccli paths
    naviBase = r'"C:\Program Files (x86)\EMC\Navisphere CLI\NaviSECCli.exe" -h {} -t {} {}'
    naviBaseSec = r'"C:\Program Files (x86)\EMC\Navisphere CLI\NaviSECCli.exe" -addusersecurity -user {} -password "{}" -scope 2'
else:
    # Linux Naviseccli paths
    naviBase = '/opt/Navisphere/bin/naviseccli -h {} -t {} {}'
    naviBaseSec = '/opt/Navisphere/bin/naviseccli -addusersecurity -user {} -scope 2'


def naviseccli(ip, command, timeout=60):
    """
    Runs the naviseccli command against the given IP.
    return: tuple (stdout, stderr)
    """
    try:
        process = subprocess.Popen(
            naviBase.format(ip, timeout, command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        out, err = process.communicate()
    except Exception as e:
        raise Exception(e)
    return (out.decode(encoding='UTF-8'), err.decode(encoding='UTF-8'))


def download_spc_parallel(spa_ip, spb_ip, spa_filename, spb_filename, timeout=60):
    try:
        process_spa = subprocess.Popen(
            naviBase.format(spa_ip, timeout, 'managefiles -retrieve -file ' + spa_filename + ' -o'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        process_spb = subprocess.Popen(
            naviBase.format(spb_ip, timeout, 'managefiles -retrieve -file ' + spb_filename + ' -o'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        out_spa, err_spa = process_spa.communicate()
        out_spb, err_spb = process_spb.communicate()
    except Exception as e:
        raise Exception(e)
    return out_spa.decode(encoding='UTF-8'), err_spa.decode(encoding='UTF-8'), out_spb.decode(encoding='UTF-8'), err_spb.decode(encoding='UTF-8')


def setsecurity(user, password):
    """
    Runs the naviseccli AddUserSecurity command to generate security file for given user\pass.
    return: tuple (stdout, stderr)
    """
    try:
        process = subprocess.Popen(
            naviBaseSec.format(user, password),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        out, err = process.communicate()
    except Exception as e:
        raise Exception(e)
    return (out.decode(encoding='UTF-8'), err.decode(encoding='UTF-8'))


def get_spc_re(date):
    return re.compile(r'([A-Z]{3}[0-9]{11}[_][A-Z]{3}[_]' + date.strftime('%Y-%m-%d') +
                       r'[_][0-9]+[-][0-9]+[-][0-9]+[_].+[_]data.zip)+')


def get_latest_spc_filename(managefiles_str):

    today = datetime.today()
    prev_day = datetime.today() - timedelta(days=1)
    next_day = datetime.today() + timedelta(days=1)

    today_re =  get_spc_re(today)
    prev_day_re = get_spc_re(prev_day)
    next_day_re = get_spc_re(next_day)

    sp_collect_patterns = (prev_day_re, today_re, next_day_re)

    result = []
    latest = None
    for day in sp_collect_patterns:
        search_results = day.findall(managefiles_str)
        if search_results:
            result.append(search_results.pop())
    if result:
        latest = result.pop()

    return latest


def get_managefiles(sp_ip):
    managefiles_result = naviseccli(sp_ip, 'managefiles -list')
    managefiles = ''
    for line in managefiles_result:
        managefiles += line
    return managefiles


def run_triiage(spa_filename, spb_filename, device_number, username):
    today = datetime.today()
    dir_name = os.path.join(username, device_number + today.strftime('_%m.%d.%y_%H.%M.%S'))
    os.makedirs(dir_name, exist_ok=True)
    shutil.move(spa_filename, dir_name)
    shutil.move(spb_filename, dir_name)
    process = subprocess.Popen('triage', cwd=dir_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    return (out.decode(encoding='UTF-8'), err.decode(encoding='UTF-8'), dir_name)


def main_menu():
    print('Please choose an option below:')
    print('1. Run Triiage')
    print('    Gathers SP Collects and runs Triiage automatically.\n')
    print('2. Run maintenance prechecks')
    print('    Login to the array and verify that all initiators are logged-in with 4 paths without any issues.')
    print('    Verify if the is array is operating normally without any hardware issues.')
    print('    Verify if there is no trespassed LUNs.')
    print('    Verify if there are any on-going LUN migrations or rebalances.')
    print('3. Run Triiage and run maintenance prechecks\n')
    selection = input('Enter 1, 2, or 3: ')
    return selection

'somestring'.format()
def gather_array_info():
    pass


def compare_serials(spa_ip, spb_ip):
    sp_serial_re = re.compile('([A-Z]{3}[0-9]{11})')

    spa_getagent = naviseccli(spa_ip, 'getagent')
    spa_serial = ''
    for line in spa_getagent:
        search = sp_serial_re.search(line)
        if search is not None and spa_serial == '':
            spa_serial = search.group(0)

    spb_getagent = naviseccli(spb_ip, 'getagent')
    spb_serial = ''
    for line in spb_getagent:
        search = sp_serial_re.search(line)
        if search is not None and spb_serial == '':
            spb_serial = search.group(0)

    match = False

    if spa_serial is not '' and spb_serial is not '' and spa_serial == spb_serial:
        match = True

    return spa_serial, spb_serial, match

if __name__ == '__main__':
    print('\nVNX Precheck 1.1a')
    print('\nThis script is used to automatically generate, download, and run Triiage against SP collects for the given array.')
    print('\nTo run this script, your storage domain user\pass will be encrypted in a naviseccli security file.\nIt will be saved in your Windows profile only.')
    print('\nBe sure to enter the correct username and password as it is not validated.\nThe script will fail to work otherwise.')
    user = input('\nStorage Domain username: ')
    print()
    password = getpass.getpass()
    print()
    print('Creating naviseccli security file...')
    print()
    setsecurity(user, password)
    device_num = input('DPE Device Number: ')
    print()
    spa_ip = input('SP A IP Address: ')
    print()
    spb_ip = input('SP B IP Address: ')
    print('')
    print('Running getagent against SP A and SP B to compare serial numbers...')
    print('')
    compare_result = compare_serials(spa_ip, spb_ip)
    print('SP A serial: ' + compare_result[0])
    print('SP B serial: ' + compare_result[1])

    if compare_result[2]:
        print('SP serials match, continuing...')
    else:
        print('SP serials do not match or could not be obtained via getagent. Aborting script.')
        sys.exit()
    print('')

    # Get initial managefile list before generating SP collects, to compare with after SP collects requested
    initial_spa_managefiles = get_managefiles(spa_ip)
    initial_spa_filename = get_latest_spc_filename(initial_spa_managefiles)
    initial_spb_managefiles = get_managefiles(spb_ip)
    initial_spb_filename = get_latest_spc_filename(initial_spb_managefiles)


    print('Requesting SP collects be generated on both SPs...')
    print()
    naviseccli(spa_ip, 'spcollect')
    naviseccli(spb_ip, 'spcollect')
    spa_managefiles = ''
    spb_managefiles = ''
    spa_filename = ''
    spb_filename = ''
    files_ready = False
    print('Checking if SP collects are finished, once every minute.\nPlease wait as this may take 10-15 minutes...')
    print()
    while not files_ready:
        print('.')
        time.sleep(60)
        spa_managefiles = get_managefiles(spa_ip)
        spb_managefiles = get_managefiles(spb_ip)
        spa_filename = get_latest_spc_filename(spa_managefiles)
        spb_filename = get_latest_spc_filename(spb_managefiles)
        if spa_filename != initial_spa_filename and spb_filename != initial_spb_filename:
            files_ready = True
            print('SP collects have finished on both SPs.')
            print()
            print('Downloading SP collects...')
            download_spc_parallel(spa_ip, spb_ip, spa_filename, spb_filename)
            print('Download completed.')
            print()
            print('Running Triiage in background.\n When completed, a text file will be created and opened with the summary output.')
            print()
            print('Please wait as this will take several minutes...')
            print()
            triiage_output = run_triiage(spa_filename, spb_filename, device_num, user)
            if triiage_output[0]:
                with open(triiage_output[2] + '\\VNX_Precheck.txt', 'w') as file:
                    file.writelines(triiage_output[0])
                    subprocess.Popen('notepad.exe ' + 'VNX_Precheck.txt', cwd=triiage_output[2])
                print('Triiage has completed. If the text file was not automatically opened please see: \n' + os.path.join(os.getcwd(), triiage_output[2], 'VNX_Precheck.txt'))
                print('\n**** Please remember to clean up your directory when finished. Each Triiage can take ~1GB of space. ****')
            else:
                print('Triiage has failed, reason: ')
                for line in triiage_output[1]:
                    print(line)

