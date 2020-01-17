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
        self.available_matrices = {}
        self.current = self.site.current_event
        available = self.current.result_pages
        for page in available:
            self.available_matrices[page.testtype] = page

    def get_available_matrices(self):
        availables = list(self.available_matrices.keys())
        return availables

    def get_matrix_sections(self, matrixtype):
        matrix = self.available_matrices[matrixtype]
        all_sections = matrix.sections
        sections = []
        for section in all_sections:
            if section['level'] == '4':
                sections.append(section['line'])
        return sections
        
    def get_section_testcases(self, matrixtype, section):
        matrix = self.available_matrices[matrixtype]
        all_rows = matrix.get_resultrows()
        rows = []
        for row in all_rows:
            if row.section == section:
                rows.append(row.testcase)
        return rows

    def get_testcase_columns(self, matrixtype, testcase):
        matrix = self.available_matrices[matrixtype]
        testcase = matrix.find_resultrow(testcase)
        columns = []
        for col in testcase.columns:
            if col != "Milestone" and col != "Test Case":
                columns.append(col)
        return columns

    def get_current(self, record=None):
        if record == "release":
            return self.current.release
        elif record == "compose":
            return self.current.compose
        elif record == "milestone":
            return self.current.milestone
        else:
            event = {"release": self.current.release, "milestone": self.current.milestone, "compose": self.current.compose}
            return event

class Parser:
    def __init__(self):
        """ Read the command line arguments and return them to the program. """
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--info', default="False", help="Return info about the current compose matrices.")
        parser.add_argument('-t', '--type', default=None, help="Type of matrix, such as Installation, Base, Desktop.")
        parser.add_argument('-m', '--milestone', default="Rawhide", help="Milestone, such as Rawhide, Branched")
        parser.add_argument('-r', '--release', default=None, help="The number of (upcoming) release, such as 32.")
        parser.add_argument('-c', '--compose', default=None, help="Compose ID, such as 20200116.n.0")
        parser.add_argument('-e', '--testcase', default=None, help="The name of the testcase.")
        parser.add_argument('-l', '--column', default=None, help="The name of the column in which you want to report.")
        parser.add_argument('-s', '--section', default=None, help="The section of the matrix page.")
        parser.add_argument('-a', '--status', default="pass", help="The result of the test. Default is pass.")
        parser.add_argument('-b', '--bot', default="False", help="If the reporting user is a bot.")
        parser.add_argument('-u', '--user', default=None, help="Who reports the results.")
        parser.add_argument('-n', '--comment', default=None, help="Provide comment, if needed.")
        self.args = parser.parse_args()

    def get_args(self):
        return self.args


class Printer:
    def __init__(self):
        pass

    def print_formatted(self, toprint, title=None):
        if title:
            print(f"########## {title} ##############################")
        if type(toprint) == list:
            for item in toprint:
                print(item)
        elif type(toprint) == str:
            print(toprint)
        elif type(toprint) == dict:
            for key in toprint.keys():
                print(f"{key}: {toprint[key]}")

class Reporter:
    def __init__(self):
        pass

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

###########################################################################################################################
                    
def main():
    """ Main program. """
    argparser = Parser()
    args = argparser.get_args()
    site = WikiSite()
    gutenberg = Printer()

    if str.lower(args.info) == "true":
        if not args.milestone or not args.compose or not args.release:
            event = site.get_current()
            gutenberg.print_formatted(event, 'Current Event')
        if not args.type:
            gutenberg.print_formatted(site.get_available_matrices(), 'Available Pages')
        if args.type and not args.section:
            gutenberg.print_formatted(site.get_matrix_sections(args.type), 'Available sections')
        if args.type and args.section and not args.testcase:
            gutenberg.print_formatted(site.get_section_testcases(args.type, args.section), 'Available TestCases')
        if args.type and args.section and args.testcase and not args.column:
            gutenberg.print_formatted(site.get_testcase_columns(args.type, args.testcase), 'Available Columns')

        
    else:
        pass

if __name__ == '__main__':
    main()
