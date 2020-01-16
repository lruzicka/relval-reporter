#!/usr/bin/python3

"""
Checksum-Tester calculates the SHA256 and MD5 checksums for the Fedora image files and compares it with the officially provided checksums.
If the checksums match, this script reports PASSED, otherwise it reports FAILED.
The images are automatically downloaded from Koji, if they have not been previously downloaded into the working directory. If so, they
are not downloaded again, unless chosen so with a switch.
"""

import argparse
import datetime
import glob
import os
import fedfind.release
import subprocess
import sys
import wget
from wikitcms.wiki import Wiki
from wikitcms.wiki import ResTuple

def read_cli():
    """ Read the command line arguments and return them to the program. """
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--release', default="Rawhide", help="Fedora release")
    parser.add_argument('-c', '--compose', default=None, help="Compose identifier, YYYYMMDD for Rawhide.")
    parser.add_argument('-a', '--arch', default="x86_64", help="Architecture")
    parser.add_argument('-v', '--variant', default="Everything", help="Variant (Everything, Server, Workstation, Spins, Cloud")
    parser.add_argument('-s', '--subvariant', default=None, help="Subvariant (For spins: KDE, LXCD, XFCE)")
    parser.add_argument('-t', '--type', default=None, help="Type of image (For server: boot, dvd)")
    parser.add_argument('-p', '--purge', default="False", help="Use 'True' if you want to delete downloaded after testing.")
    parser.add_argument('-w', '--wiki', default="False", help="Use 'True' if you want to read the values from the current compose wiki page.")
    parser.add_argument('-e', '--report', default="False", help="Use 'True' if you want to report results.")
    parser.add_argument('-u', '--user', default=None, help="Who reports the results.")
    args = parser.parse_args()
    return args

def get_testpage():
    site = Wiki()
    page = site.get_validation_page('Installation')
    return page

def provide_compose(rel="Rawhide", comp=None, arch="x86_64", variant="Everything", subvariant=None, typ=None, wiki=False):
    """ Returns a compose download link base on given criteria. """
    # If the compose ID is not given, we will the latest compose according to the wiki page. 
    # However, for me, that only seems to be reliable with Rawhides.
    if not comp or str.lower(wiki) == "true":
        page = get_testpage()
        comp = page.compose.split('.')[0]
        rel = page.milestone
        print(f"The compose date were not given or wiki requested. Using current wiki value: {comp}")
    # Call fedfind to get the list of images in the compose.
    try:    
        composes = fedfind.release.get_release(release=rel, compose=comp)
    except NameError:
        print("fedfind is required to search for the images, you need to install it.")
    # We sort some of the images out of the list based on the requirements.
    if subvariant:
        images = [compose for compose in composes.all_images if compose['arch'] == arch and compose['variant'] == variant and compose['subvariant'] == subvariant]
    elif typ:
        images = [compose for compose in composes.all_images if compose['arch'] == arch and compose['variant'] == variant and compose['type'] == typ]
    else:
        images = [compose for compose in composes.all_images if compose['arch'] == arch and compose['variant'] == variant]
    return images

def return_iso_filename(url):
    """ Returns the filename from the url. """
    # The information about the image file name is only available as a download link. 
    # This method splits the link and takes the name out of it.
    filename = url.split('/')[-1]
    return filename

def download_iso(composes, forced="False"):
    """ Downloads the selected ISO images from Koji. """
    # We download all images in the list we obtained after we have reduced the fedfind results.
    for compose in composes:
        url = compose['url']
        filename = return_iso_filename(url)
        if filename in os.listdir():
            print(f"The ISO file {filename} seems to be downloaded already, skipping the download.")
        else:
            print("Downloading images:")
            try:
                wget.download(url)
            except NameError:
                print("Downloading uses the wget module, but it is not installed.")
            print("")

def purge_images(composes):
    """ Deletes all iso files from the working directory. """
    for compose in composes:
        url = compose['url']
        target = return_iso_filename(url)
        print(f"Deleting {target}")
        os.remove(target)

def test_compose_sha256(composes):
    """ Checks if the SHA256 checksums match. """
    results = {}
    for compose in composes:
        url = compose['url']
        filename = return_iso_filename(url)
        expected_sha = compose['checksums']['sha256']
        # The test requires the sha256sum to calculate the checksum from the iso files, 
        # so we use it externally.
        calculate = subprocess.run(['sha256sum', filename], capture_output=True)
        if calculate.returncode != 0:
            print(calculate.stderr.decode('utf-8'))
        # If we have obtained the calculations successfully, we can compare the checksums.    
        else:
            calculated_sha = calculate.stdout.decode('utf-8').split(" ")
            calculated_sha = calculated_sha[0].strip()
        if expected_sha == calculated_sha:
        # Report results    
            results[filename] = "PASSED"
        else:
            results[filename] = "FAILED"
    return results

def test_compose_md5(composes):
    """ Checks if the MD5 checksum is correct. """
    results = {}
    for compose in composes:
        url = compose['url']
        filename = return_iso_filename(url)
        # The test requires the checkisomd5 program so lets use it.
        checkmd = subprocess.run(['checkisomd5', filename], capture_output=True)
        output = checkmd.stdout.decode('utf-8')
        # Report results if went ok.
        if checkmd.returncode == 0:
            results[filename] = "PASSED"
        elif checkmd.returncode == 1:
            results[filename] = "FAILED"
        elif checkmd.returncode == 2:
            results[filename] == "SKIPPED"
        else:
            print(checkmd.stderr.decode('utf-8'))
    return results

def print_results(field, results):
    """ Prints results of the tests. """
    print(f"================ {field} RESULTS ============================")
    print("")
    for result in results.keys():
        print(f"{result}: {results[result]}")
    print("")
    
def print_available_composes(composes):
    """ Prints a list of available ISO files to test. """
    if len(composes) > 1:
        message = f"{len(composes)} image files matching the criteria found: "
    elif len(composes) == 1:
        message = "One image file matching the criteria found: "
    else:
        message = "No image file matching the criteria found."
    print(message)
    print("")
    for compose in composes:
        url = compose['url']
        print(url)
    print("")

def report_wiki_results(column, result, user=None, comment=''):
    site = Wiki()
    page = get_testpage()
    test = page.find_resultrow('QA:Testcase_Mediakit_Checksums')
    if not user:
        user = "donkey"
        bot = True
    else:
        bot = False
    result = ResTuple(
                testtype = page.testtype,
                release = page.release,
                milestone = page.milestone,
                compose = page.compose,
                testcase = test.testcase,
                section = test.section,
                testname = test.name,
                env = column,
                status = result,
                user = user,
                bot = bot,
                comment = comment)
    site.login()
    site.report_validation_results([result])
    print(f"Results reported to: {test.name}.")
                    
def main():
    """ Main program. """
    args = read_cli()
    composes = provide_compose(rel=args.release, comp=args.compose, arch=args.arch, variant=args.variant, subvariant=args.subvariant, typ=args.type, wiki=args.wiki)
    purge = args.purge
    print_available_composes(composes)
    download_iso(composes)
    sha_results = test_compose_sha256(composes)
    print_results("SHA256 CHECKSUM", sha_results)
    md_results = test_compose_md5(composes)
    print_results("MD5 CHECKSUM", md_results)
    if str.lower(purge) == "true":
        purge_images(composes)
    if str.lower(args.report) == "true":
        if args.subvariant:
            comment = f"<ref>{args.subvariant}, {args.arch} image</ref>"
        elif args.type:
            comment = f"<ref>{args.type}, {args.arch} image</ref>"
        else:
            comment = f"<ref>{args.arch} image</ref>" 
    if "FAILED" in sha_results.values() or "FAILED" in md_results.values():
        if str.lower(args.report) == "true":
            report_wiki_results(args.variant, 'fail', args.user, comment)
        sys.exit(1)
    else:
        if str.lower(args.report) == "true":
            report_wiki_results(args.variant, 'pass', args.user, comment)

if __name__ == '__main__':
    main()
