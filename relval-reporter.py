#!/usr/bin/python3

"""
Relval-Reporter is an application based on Fedora relval. RelVal can be used to report test results into release validation matrices interactively, following several steps, however it cannot report using a CLI command with arguments to report the results in one step. 
This application deals with the problem and introduces a way, how to report results from scripts, etc.
It is based on WikiTCMS Python module which is used to communicate with the Wiki pages.
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



class WikiSite:
    def __init__(self):
        self.site = Wiki()
        self.available_matrices = []
        self.last_sections = []
        self.last_resultrows = []

    def get_available_matrices(self):
        current = self.site.current_event
        available = current.result_pages
        for page in available:
            self.available_matrices.append(page.testtype)
        return self.available_matrices

    def get_matrix_sections(self, matrixtype):
        matrix = self.site.get_validation_page(matrixtype)
        sections = matrix.sections
        for section in sections:
            if section['level'] == '4':
                self.last_sections.append(section['line'])
        return self.last_sections
        
    def get_section_testcases(self, matrixtype, section):
        matrix = self.site.get_validation_page(matrixtype)
        rows = matrix.get_resultrows()
        for row in rows:
            if row.section == section:
                self.last_resultrows.append(row.testcase)
        return self.last_resultrows
        

    def get_testcase_columns(self, testcase):
        pass

class Parser:
    def __init__(self):
        """ Read the command line arguments and return them to the program. """
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--info', default="False", help="Return info about the current compose matrices.")
        parser.add_argument('-t', '--type', default="Installation", help="Type of matrix, such as Installation, Base, Desktop.")
        parser.add_argument('-m', '--milestone', default="Rawhide", help="Milestone")
        parser.add_argument('-r', '--release', default=None, help="The number of (upcoming) release, such as 32.")
        parser.add_argument('-c', '--compose', default=None, help="Compose ID, such as 20200116.n.0")
        parser.add_argument('-e', '--testcase', default=None, help="The name of the testcase.")
        parser.add_argument('-l', '--column', default=None, help="The name of the column in which you want to report.")
        parser.add_argument('-s', '--status', default="pass", help="The result of the test. Default is pass.")
        parser.add_argument('-b', '--bot', default="False", help="If the reporting user is a bot.")
        parser.add_argument('-u', '--user', default=None, help="Who reports the results.")
        parser.add_argument('-m', '--comment', default=None, help="Provide comment, if needed.")
        args = parser.parse_args()
        return args



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

if __name__ == '__main__':
    main()
