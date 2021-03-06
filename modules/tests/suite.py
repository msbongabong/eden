# This script is designed to be run as a Web2Py application:
# python web2py.py -S eden -M -R applications/eden/modules/tests/suite.py
# or
# python web2py.py -S eden -M -R applications/eden/modules/tests/suite.py -A testscript

import sys
import re
import time
import unittest
import argparse

#from s3 import s3_debug

# Set up the command line arguments
desc = "Script to run the Sahana Eden test suite."
parser = argparse.ArgumentParser(description = desc)
parser.add_argument("-C", "--class", help = "Name of class to run")
method_desc = """Name of method to run, this is used in conjunction with the
class argument or with the name of the class followed by the name of the method
separated with a period, class.period.
"""
parser.add_argument("-M", "--method", "--test", help = method_desc)
parser.add_argument("-V", "--verbose",
                    type = int,
                    default = 1,
                    help = "The level of verbose reporting")
parser.add_argument("--nohtml", help = "Disable HTML reporting.")
parser.add_argument("--html-path", help = "Path where the HTML report will be saved.")
parser.add_argument("--html-name-date", help = "Include just the date in the name of the HTML report.")
suite_desc = """This will execute a standard testing schedule. The valid values
are, smoke, quick, complete and full. If a method or class options is selected
the the suite will be ignored.

The suite options can be described as follows:

 smoke: This will run the broken link test
 quick: This will run all the tests marked as essential
 complete: This will run all tests except those marked as long
 full: This will run all test
"""
parser.add_argument("--suite",
                    help = suite_desc,
                    choices = ["smoke", "quick", "complete", "full"],
                    default = "quick")
parser.add_argument("--link-depth",
                    type = int,
                    default = 3,
                    help = "The recursive depth when looking for links")
parser.add_argument("--keep-browser-open",
                    help = "Keep the browser open once the tests have finished running",
                    type = bool,
                    default = False)
argsObj = parser.parse_args()
args = argsObj.__dict__

# Selenium WebDriver
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from gluon import current
from gluon.storage import Storage

current.data = Storage()

# S3 Tests
from tests.web2unittest import *
from tests import *

# Read Settings
current.deployment_settings.ui.navigate_away_confirm = False
settings = current.deployment_settings
public_url = settings.get_base_public_url()
base_url = "%s/%s" % (public_url, current.request.application)
system_name = settings.get_system_name()

# Store these to be available to modules
config = current.test_config = Storage()
config.system_name = system_name
config.timeout = 5 # seconds
config.url = base_url

base_dir = os.path.join(os.getcwd(), "applications", current.request.application)
test_dir = os.path.join(base_dir, "modules", "tests")
config.base_dir = base_dir


# Shortcut
loadTests = unittest.TestLoader().loadTestsFromTestCase
loadNamedTests = unittest.TestLoader().loadTestsFromName

config.verbose = args["verbose"]
browser_open = False
# @todo test with invalid class and methods passed as CLA
if args["method"]:
    browser = config.browser = webdriver.Firefox()
    browser.implicitly_wait(config.timeout)
    browser_open = True
    if args["class"]:
        name = "%s.%s" % (args["class"], args["method"])
    else:
        name = args["method"]
    suite = loadNamedTests(args["method"], globals()[args["class"]])
elif args["class"]:
    browser = config.browser = webdriver.Firefox()
    browser.implicitly_wait(config.timeout)
    browser_open = True
    suite = loadTests(globals()[args["class"]])
elif args["suite"] == "smoke":
#    try:
    from tests.smoke import *
    broken_links = BrokenLinkTest()
    broken_links.setDepth(args["link_depth"])
    broken_links.run()
#    except NameError as msg:
#        s3_debug("%s, unable to run the smoke tests." % msg)
#        pass
    exit()

else:
    browser = config.browser = webdriver.Firefox()
    browser.implicitly_wait(config.timeout)
    browser_open = True
    # Run all Tests

    # Create Organisation
    suite = loadTests(CreateOrganisation)
    
    # Shortcut
    addTests = suite.addTests
    
    # Create Office
    addTests(loadTests(CreateOffice))
    
    # Setup Staff
    addTests(loadTests(CreateStaff))
    
    # Setup New Volunteer
    addTests(loadTests(CreateVolunteer))
    
    # Create Staff & Volunteer Training
    addTests(loadTests(CreateStaffTraining))
    addTests(loadTests(CreateVolunteerTraining))

    # Inventory tests
    addTests(loadTests(SendItem))
    addTests(loadTests(ReceiveItem))
    addTests(loadTests(SendReceiveItem))
    
    # Project Tests
    addTests(loadTests(CreateProject))

    # Asset Tests
    addTests(loadTests(CreateAsset))

    # Assign Staff to Organisation
    addTests(loadTests(AddStaffToOrganisation))
    
    # Assign Staff to Office
    addTests(loadTests(AddStaffToOffice))
    
    # Assign Staff to Warehouse
    addTests(loadTests(AddStaffToWarehouse))
    # Delete a prepop organisation
#    addTests(loadTests(DeleteOrganisation))

try:
    path = args["html_path"]
    if args["html_name_date"]:
        filename = "Sahana-Eden-Test-Result-%s.html" % current.request.now.date()
    else:
        filename = "Sahana-Eden-Test-Result-%s.html" % current.request.now
    fullname = os.path.join(path,filename)
    fp = file(fullname, "wb")

    import HTMLTestRunner
    runner = HTMLTestRunner.HTMLTestRunner(
                                           stream=fp,
                                           title="Sahana Eden Test Result",
                                          )
    runner.run(suite)
except:
    unittest.TextTestRunner(verbosity=2).run(suite)

# Cleanup
if browser_open and not args["keep_browser_open"]:
    browser.close()

# END =========================================================================