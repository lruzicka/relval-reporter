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
        self.site.login()
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
                if row.testcase != row.name:
                    rows.append(f"{row.testcase} {row.name}")
                else:
                    rows.append(row.testcase)
        return rows

    def get_testcase_columns(self, matrixtype, section, test, name):
        matrix = self.available_matrices[matrixtype]
        #all_rows = matrix.get_resultrows()
        #for row in all_rows:
        #    if row.section == section:
        #        if row.testcase == test:
        #            if test != row.name:
        #                testname = row.name
        #            else:
        #                testname = test
        print(test, name)
        if name:
            testcase = matrix.find_resultrow(test, section, testname=name)
        else:
            testcase = matrix.find_resultrow(test, section)
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

    def override_current(self, release, milestone, compose):
        pass

    def report_results(self, results):
        self.site.report_validation_results(results)

class Parser:
    def __init__(self):
        """ Read the command line arguments and return them to the program. """
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--info', action='store_true', help="Return info about the current compose matrices.")
        parser.add_argument('-t', '--type', default=None, help="Type of matrix, such as Installation, Base, Desktop.")
        parser.add_argument('-m', '--milestone', default="Rawhide", help="Milestone, such as Rawhide, Branched")
        parser.add_argument('-r', '--release', default=None, help="The number of (upcoming) release, such as 32.")
        parser.add_argument('-c', '--compose', default=None, help="Compose ID, such as 20200116.n.0")
        parser.add_argument('-e', '--testcase', default=None, help="The name of the testcase page.")
        parser.add_argument('-n', '--testname', default=None, help="The name of the testcase.")
        parser.add_argument('-l', '--column', default=None, help="The name of the column in which you want to report.")
        parser.add_argument('-s', '--section', default=None, help="The section of the matrix page.")
        parser.add_argument('-a', '--status', default="pass", help="The result of the test. Default is pass.")
        parser.add_argument('-b', '--bot', default="False", help="If the reporting user is a bot.")
        parser.add_argument('-u', '--user', default=None, help="Who reports the results.")
        parser.add_argument('-o', '--comment', default=None, help="Provide comment, if needed.")
        parser.add_argument('-x', '--interactive', action='store_true', help="Report results interactively.")
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
                if type(item) == tuple:
                    print(f"{item[0]}: {item[1]}")
                else:
                    print(item)
        elif type(toprint) == str:
            print(toprint)
        elif type(toprint) == dict:
            for key in toprint.keys():
                print(f"{key}: {toprint[key]}")

    def make_menu(self, items):
        menu = {}
        key = 1
        for item in items:
            menu[key] = item
            key += 1
        return menu


class Collector:
    def __init__(self, wiki, printer):
        self.release = None
        self.milestone = None
        self.compose = None
        self.type = None
        self.section = None
        self.testcase = None
        self.column = None
        self.status = None
        self.comment = None
        self.user = None
        self.bot = False
        self.wiki = wiki
        self.gutenberg = printer

    def collect_data(self, release=None, milestone=None, compose=None, user=None):
        current = self.wiki.get_current()
        if release:
            self.release = release
        else:
            self.release = current['release']

        if milestone:
            self.milestone = milestone
        else:
            self.milestone = current['milestone']

        if compose:
            self.compose = compose
        else:
            self.compose = current['compose']
        
        menu = self.gutenberg.make_menu(self.wiki.get_available_matrices())
        self.gutenberg.print_formatted(menu, 'Matrix type: ')
        choice = int(input("Choose one of the above: "))
        self.type = menu[choice]

        menu = self.gutenberg.make_menu(self.wiki.get_matrix_sections(self.type))
        self.gutenberg.print_formatted(menu, "Available sections")
        choice = int(input("Choose one of the above: "))
        self.section = menu[choice]

        menu = self.gutenberg.make_menu(self.wiki.get_section_testcases(self.type, self.section))
        self.gutenberg.print_formatted(menu, "Available testcases")
        choice = int(input("Choose one of the above: "))
        self.testcase = menu[choice]
        
        menu = self.gutenberg.make_menu(self.wiki.get_testcase_columns(self.type, self.section, self.testcase))
        self.gutenberg.print_formatted(menu, "Available columns")
        choice = int(input("Choose one of the above: "))
        self.column = menu[choice]

        menu = self.gutenberg.make_menu(["pass", "fail", "inprogress"])
        self.gutenberg.print_formatted(menu, "Result")
        choice = int(input("Choose one of the above: "))
        self.status = menu[choice]
        
        comment = input("Do you want to add some comment (hit enter to skip): ")
        if not comment:
            self.comment = ''
        else:
            self.comment = f"<ref>{comment}</ref>"

        if not user:
            user = input("No user was given, write the user name or hit enter for a default user: ")
            if not user:
                self.user = "donkey"
                self.bot = True
        else:
            self.user = user

        data = [self.release, self.milestone, self.compose, self.type, self.section, self.testcase, self.column, self.status, self.comment, self.user, self.bot]
        return data


    def provide_data(self):
        result = ResTuple(
                    testtype = self.type,
                    release = self.release,
                    milestone = self.milestone,
                    compose = self.compose,
                    testcase = self.testcase,
                    section = self.section,
                    env = self.column,
                    status = self.status,
                    user = self.user,
                    bot = self.bot,
                    comment = self.comment)
        return result



class Reporter:
    def __init__(self, wiki):
        self.site = wiki
        self.results = []

    def add_to_results(self, result):
        self.results.append(result)

    def report_wiki_results(self):
        self.site.report_results(self.results)

###########################################################################################################################
                    
def main():
    """ Main program. """
    argparser = Parser()
    args = argparser.get_args()
    site = WikiSite()
    gutenberg = Printer()
    gatherer = Collector(site, gutenberg)
    bluejay = Reporter(site)


    if args.info:
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
            gutenberg.print_formatted(site.get_testcase_columns(args.type, args.section, args.testcase, args.testname), 'Available Columns')
        if args.type and args.section and args.testcase and args.testname and not args.column:
            gutenberg.print_formatted(site.get_testcase_columns(args.type, args.section, args.testcase, name=args.testname), 'Available Columns')

    elif str.lower(args.interactive) == "true":
        data = gatherer.collect_data(user=args.user)
        #gutenberg.print_formatted(data, "Collected data")
        toreport = gatherer.provide_data()
        bluejay.add_to_results(toreport)
        bluejay.report_wiki_results()
        print("The result was reported.")

        
    else:
        pass

if __name__ == '__main__':
    main()
