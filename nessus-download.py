'''
Using the Nessus API to export all the scans in a given folder
'''
import sys
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Assume Nessus is in the default location, if not you'll need to change this
URLBASE = "https://localhost:8834"

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def print_message(message, level="Info", errors_fatal=True):
    '''
    Output Formatting
    '''
    if level == "Info":
        prefix = "[\033[1;32m+\033[m]"
    elif level == "Error":
        prefix = "[\033[1;31m!\033[m]"
    elif level == "Warn":
        prefix = "[\033[1;33m*\033[m]"
    else:
        prefix = "[?]"

    print(f"{prefix} {message}")
    if level == "Error" and errors_fatal:
        sys.exit()

def export_scans(urlbase, foldername, username, password, targetfolder):
    '''
    Export Scans from folder foldername using API at urlbase
    Authenticating as username, password
    '''
    response = requests.post(f"{urlbase}/session", data={"username":username,"password":password},
        verify=False)

    if response.status_code != 200:
        print_message("Login Failed", "Error")

    token = response.json()['token']
    print_message(f"Got token '{token[0:3]}...{token[-3:]}'")

    response = requests.get(f"{urlbase}/folders?token={token}", verify=False)

    folderid = -1
    for folder in response.json()['folders']:
        print_message(f"Found folder: {folder['name']} [{folder['id']}]")
        if folder['name'] == foldername:
            folderid = folder['id']

    if folderid > 0:
        print_message(f"Opening Folder ID {folderid} ...")
        response = requests.get(f"{urlbase}/scans?token={token}&folder_id={folderid}", verify=False)

        print_message(f"... Found {len(response.json()['scans'])} Scans")
        for scan in response.json()['scans']:
            print_message(f"Triggered export for Scan ID {scan['id']}")
            response = requests.post(f"{urlbase}/scans/{scan['id']}/export?token={token}",
                    data={"format":"nessus"},
                    verify=False)
            file = response.json()['file']
            # token2= response.json()['token'] # Don't seem to need this??
            # We have to wait until file is ready to download, API returns 409's if we're too keen
            print("[\033[1;33m*\033[m] Waiting ", end="")
            while True:
                response = requests.get(
                        f"{urlbase}/scans/{scan['id']}/export/{file}/download?token={token}",
                        verify=False)
                if response.status_code != 409:
                    break
                print(".", end="", flush=True)
                time.sleep(0.1) # Wait a bit before we try again
            print()

            cdheader = response.headers["Content-Disposition"]
            if cdheader[:22] == "attachment; filename=\"":
                report_filename = targetfolder + "/" + cdheader[22:-1]
                print_message(f"Writing file '{report_filename}'")
                with open(report_filename, "wb") as file:
                    file.write(response.content)
            else:
                print_message("No Content-Disposition Match", "Error")
    else:
        print_message(f"Failed to find the '{foldername}' folder!", "Error")

def usage():
    print(f"{sys.argv[0]}: Nessus Bulk Scan Downloader")
    print()
    print(f"{sys.argv[0]} folder username password [targetfolder]")
    print("\tfolder: Nessus Scan Folder to Download")
    print("\ttargetfolder: Folder to save Nessus XMLS to (defaults to .)")


if __name__ == '__main__':
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        usage()
        exit()

    foldername = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    if len(sys.argv) == 5:
        targetfolder = sys.argv[4]
    else:
        print_message("No target folder supplied, will write files to current directory", "Warn")
        targetfolder = "."

    export_scans(URLBASE, foldername, username, password, targetfolder)
   
