# wagetheft_report_2020_v2
# Python 3.9.7
# Last updated
# 3/3/2019 by F. Peterson first file--170 lines
# 7/8/2019 by F. Peterson
# 9/7/2019 by F. Peterson (v2)
# 1/14/2020 by F. Peterson
# 2/4/2020 by F. Peterson
# 5/1/2019 by F. Peterson numerous updates
# 2/25/2020 by F. Peterson
# 3/5/2020 by F. Peterson locked code before forking into OLSE and SCC WTC versions (donation of ~1,500 lines--@$73,500--from WTC to OLSE)
# 10/11/2020 by F. Peterson
# 10/22/2020 by F. Peterson
# 10/26/2020 by F. Peterson (finally debugged 4am on 10/30/2020)
# 11/1/2020 by F. Peterson still working on this a week later
# 11/9/2020 by F. Peterson fixed infer zip code and added proximity match to allow filtering unpaid theft
# 11/15/2020 by F. Peterson removed duplicates
# 11/16/2020 by F. Peterson adjusted care home keywords
# 11/21/2020 by F. Peterson add name of highest theft business to city summary
# 11/22/2020 by F. Peterson add hospital/care signatory employer list
# 12/16/2020 by F. Peterson add revised industry keyword exclusion function, and revise NAICS library
# 12/24/2020 by F. Peterson revised industry NAICS keyword library w/ regexp and update industry label function to include state NAICS labels
# 1/8/2021 by F. Peterson revised city and zipcode summary per Michael Tayag edits to text (2,711 lines)
# 1/12/2021 by F. Peterson added signatory by industry label (does not work?) --> works 1/13/2021
# 1/13/2021 by F. Peterson added industry summary to regional summary (2,867 lines)
# 1/14/2021 by F. Peterson added a summary of ratio of union to non-union company wage theft (2,880 lines-->@$140k in work with $5 per line and ~10 lines per 8hr day)
# 1/22/2021 by F. Peterson careful output check with 100 x 1,000 dataset
# 1/24/2021 by F. Peterson debug details in signatory library access to industry labels (2,969 lines)
# 9/21/2021 by F. Peterson
# 10/25/2021 by F. Peterson added summary block 1/0 triggers, 4 LoC and added formating to prev wage table
# 2/3/2022 by F. Peterson added organization filter -- add State filter, added new WHD file and debugged, fix date bug, industry lebel adjusted (3,195 lines)
# 2/14/2022 by F. Peterson add WHD prevailing wage inference
# 3/3/2022 by F. Peterson added exclusion terms to construction industry
# 3/4/2022 by F. Peterson fixed a bug with trade/industry header mixup
# 3/4/2022 by F. Peterson fixed a bug with double output
# 3/7/2022 by F. Peterson added county of San Diego
# 6/28/2022 by F. Peterson started adding API (does not run)
# 6/29/2022 by I. Kolli added parameters to API code
# 7/2/2022 by F. Peterson added several more parameters to API code and create output folder if missing: tested and works
# 7/2/2022 by F. Peterson added url pulls for WHD and DOL violations
# 7/14/2022 by F. Peterson update DOL WHD url to updated url 7/13/2022
# 8/10/2022 by F. Peterson resolve several bugs-- incomplete but runs without crash
# 8/13/2022 see Git log for update record
# 10/26/2022 by F. Peterson -- debug hang on State and Fed reports -- casued by zipcode bug (old school but I like the log here)

# Note: add an edit distance comparison
# to fix replace() https://stackoverflow.com/questions/64843109/compiler-issue-assertionerror-on-replace-given-t-or-f-condition-with-string/64856554#64856554

# DUPLICTAE CHECKS:
# duplicated values for ee_pmt_due are zeroed
# no duplicate by case numbers
# no duplicate by legal or trade names
# no duplicates by bw_amt
# no duplicates by ee_pmt_recv (duplicated zero false positives but nbd)

import re
import pandas as pd
import numpy as np
import math
from datetime import datetime
import os
import platform
from string import ascii_letters
import warnings
import time
import requests
import io

#moved down one directory
if platform.system() == 'Windows' or platform.system() =='Darwin':
    #for desktop testing--"moved down one directory"
    from constants.zipcodes import stateDict
    from constants.zipcodes import countyDict
    from constants.zipcodes import cityDict
    from constants.industries import industriesDict
    from constants.prevailingWageTerms import prevailingWageTermsList
    from constants.signatories import signatories
else:
    from api.constants.zipcodes import stateDict
    from api.constants.zipcodes import countyDict
    from api.constants.zipcodes import cityDict
    from api.constants.industries import industriesDict
    from api.constants.prevailingWageTerms import prevailingWageTermsList
    from api.constants.signatories import signatories

warnings.filterwarnings("ignore", 'This pattern has match groups')


def main():
    # settings****************************************************
    PARAM_1_TARGET_STATE = "" #"California"
    PARAM_1_TARGET_COUNTY = "Santa_Clara_County"
    PARAM_1_TARGET_ZIPCODE = "" #for test use "All_Zipcode"
    PARAM_2_TARGET_INDUSTRY = 'WTC NAICS' #"Janitorial" #"Construction" #for test use 'WTC NAICS' or "All NAICS"
    OPEN_CASES = 1 # 1 for open cases only (or nearly paid off), 0 for all cases
    USE_ASSUMPTIONS = 1  # 1 to fill violation and ee gaps with assumed values
    INFER_NAICS = 1  # 1 to infer code by industry NAICS sector
    INFER_ZIP = 1  # 1 to infer zip code
    federal_data = 1  # 1 to include federal data
    state_data = 1  # 1 to include state data
    # report output block settings****************************************************
    All_Industry_Summary_Block = 0
    TABLES = 1  # 1 for tables and 0 for just text description
    SUMMARY = 1  # 1 for summaries and 0 for none
    SUMMARY_SIG = 1 # 1 for summaries only of regions with significant wage theft (more than $10,000), 0 for all
    TOP_VIOLATORS = 1  # 1 for tables of top violators and 0 for none
    prevailing_wage_report = 0 # 1 to label prevailing wage violation records and list companies with prevailing wage violations, 0 not to
    signatories_report = 0 # 1 to include signatories (typically, this report is only for union compliance officers) 0 to exclude signatories

    #!!!manually add to report***********************************************************
    # (1)generate report from http://wagetheftincitieslikemine.site/
    # (2)geocode data https://www.geocod.io
    # (3)generate Tableau bubble plot with location data https://public.tableau.com/profile/forest.peterson#!

    # checks
    # https://webapps.dol.gov/wow/
    # https://www.goodjobsfirst.org/violation-tracker

    # API call***************************************************************************
    generateWageReport(PARAM_1_TARGET_STATE, PARAM_1_TARGET_COUNTY, PARAM_1_TARGET_ZIPCODE, PARAM_2_TARGET_INDUSTRY,
                       federal_data, state_data, INFER_ZIP, prevailing_wage_report, signatories_report,
                       All_Industry_Summary_Block, OPEN_CASES, TABLES, SUMMARY, SUMMARY_SIG,
                       TOP_VIOLATORS, USE_ASSUMPTIONS, INFER_NAICS)

# Functions*************************************************


def generateWageReport(target_state, target_county, target_city, target_industry, 
                        includeFedData, includeStateData, infer_zip, prevailing_wage_report, signatories_report,
                        all_industry_summary_block, open_cases_only, include_tables, include_summaries, only_sig_summaries,
                        include_top_viol_tables, use_assumptions, infer_by_naics):

    warnings.filterwarnings("ignore", category=UserWarning)
    start_time = time.time()

    # Settings External - start
    
    TARGET_ZIPCODES = search_Dict_tree(target_state, target_county, target_city, stateDict, countyDict, cityDict)
    TARGET_INDUSTRY = industriesDict[target_industry]
    # Settings External - end

    # Settings Internal - start
    TEST_ = 0 # see Read_Violation_Data() -- 
    # 0 for normal run w/ all records
    # 1 for custom test dataset (url0 = "https://stanford.edu/~granite/DLSE_no_returns_Linux_TEST.csv" <-- open and edit this file with test data)
    # 2 for small dataset (first 100 of each file)
    RunFast = False  # True skip slow formating; False run normal
    New_Data_On_Run_Test = False #to generate a new labeled dataset on run
    LOGBUG = True #True to log, False to not
    FLAG_DUPLICATE = 0  # 1 FLAG_DUPLICATE duplicate, #0 drop duplicates
    # Settings Internal - end

    # Settings Internal that will Move to UI Options - start
    ORGANIZATION_FILTER = False # True to filter, False no filter for specific organizantion name, see TARGET_ORGANIZATIONS
    TARGET_ORGANIZATIONS = [['organizations'], ['GOODWILL']]  # use uppercase
    Nonsignatory_Ratio_Block = False
    # Settings Internal that will Move to UI Options - end

    #LIBRARIES - start
    prevailing_wage_terms = prevailingWageTermsList #from prevailingWageTerms.py
    SIGNATORY_INDUSTRY = signatories #from signatories.py
    #LIBRARIES - end
    
    # TEST_ PARAMETERS
    if TEST_ == 0 or TEST_ == 1:
        TEST_CASES = 1000000000  # read all records
    else:  # TEST_ == 2 #short set--use first 1000 for debugging
        TEST_CASES = 100

    # SET OUTPUT FILE NAME AND PATH: ALL FILE NAMES AND PATHS DEFINED HERE **********************************
    # report main output file -- change to PDF option
    # relative path
    rel_path = 'report_output_/'
    # <-- dir the script is in (import os) plus up one
    script_dir = os.path.dirname(os.path.dirname(__file__))
    abs_path = os.path.join(script_dir, rel_path)
    if not os.path.exists(script_dir):  # create folder if necessary
        os.makedirs(script_dir)

    file_name = TARGET_ZIPCODES[0] + "_" + target_industry

    file_type = '.html'
    out_file_report = '_theft_summary_'
    temp_file_name = os.path.join(abs_path, (file_name+out_file_report).replace(
        ' ', '_') + file_type)  # <-- absolute dir and file name

    file_type = '.csv'
    temp_file_name_csv = os.path.join(abs_path, (file_name+out_file_report).replace(
        ' ', '_') + file_type)  # <-- absolute dir and file name

    out_file_report = '_signatory_wage_theft_'
    sig_file_name_csv = os.path.join(abs_path, (file_name+out_file_report).replace(
        ' ', '_') + file_type)  # <-- absolute dir and file name

    out_file_report = '_prevailing_wage_theft_'
    prev_file_name_csv = os.path.join(abs_path, (file_name+out_file_report).replace(
        ' ', '_') + file_type)  # <-- absolute dir and file name

    file_name = 'log_'
    out_file_report = '_bug_'
    file_type = '.txt'
    # <-- absolute dir and file name
    bug_log = os.path.join(
        abs_path, (file_name+out_file_report).replace(' ', '_') + file_type)
    file_type = '.csv'
    # <-- absolute dir and file name
    bug_log_csv = os.path.join(
        abs_path, (file_name+out_file_report).replace(' ', '_') + file_type)

    bugFile = ""
    log_number = 0
    if LOGBUG: 
        bugFile = open(bug_log, 'w')
        debug_fileSetup_def(bugFile)
        bugFile.close()

    # region definition*******************************************************************
    time_1 = time.time()
    # <--revise to include other juriscition types such as County
    JURISDICTON_NAME = " "
    if TARGET_ZIPCODES[0].find("County"): "DO_NOTHING"
    else: JURISDICTON_NAME = "City of "
    
    # target jurisdiction: Report Title block and file name "<h1>DRAFT REPORT: Wage Theft in the jurisdiction of... "
    target_jurisdition = JURISDICTON_NAME + TARGET_ZIPCODES[0].replace("_"," ")
    target_industry = TARGET_INDUSTRY[0][0]
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n") 
    # endregion definition*******************************************************************

    # Read data***************************************************************************
    time_0 = time.time()
    time_1 = time.time()

    # from os.path import exists # for relative path
    # violation_report_folder = "dlse_judgements/"
    # if exists(violation_report_folder + "unified_no_WHD_20190629.csv"):
    #     read_file0 = violation_report_folder + \
    #         "unified_no_WHD_20190629.csv"  # mixed SJOE, SCCBTC, DLSE
    # if exists(violation_report_folder + "whd_whisard_02052022.csv"):
    #     read_file1 = violation_report_folder + \
    #         "whd_whisard_02052022.csv"  # US DOL WHD website
    # if exists(violation_report_folder + "HQ20009-HQ2ndProduction8.13.2019_no_returns_Linux.csv"): #10/2/2022 added _Linux
    #     read_file2 = violation_report_folder + \
    #         "HQ20009-HQ2ndProduction8.13.2019_no_returns.csv"  # CA DIR DSLE PRA

    url0 = "https://stanford.edu/~granite/DLSE_no_returns_Linux_TEST.csv" #<-- open and edit this file with test data
    url1 = "https://enfxfr.dol.gov/data_catalog/WHD/whd_whisard_20221006.csv.zip"
    # url2 = "https://www.researchgate.net/profile/Forest-Peterson/publication/357767172_California_Dept_of_Labor_Standards_Enforcement_DLSE_PRA_Wage_Claim_Adjudications_WCA_for_all_DLSE_offices_from_January_2001_to_July_2019/data/61de6b974e4aff4a643603ae/HQ20009-HQ-2nd-Production-8132019.csv"
    # url2 = "https://drive.google.com/file/d/1TRaixcwTg08bEyPSchyHntkkktG2cuc-/view?usp=sharing"
    url2 = "https://stanford.edu/~granite/HQ20009-HQ2ndProduction8.13.2019_no_returns_Linux.csv" #10/2/2022 added _Linux
    
    includeTestData = False
    if (TEST_ == 1): 
        includeTestData = 1
        includeFedData = 0
        includeStateData = 0
        #includeLocalData = False -- unused
        #includeOfficeData = False -- unused
    url_list = [
        [url0, includeTestData,'TEST'], 
        [url1, includeFedData,'DOL_WHD'], 
        [url2, includeStateData,'DIR_DLSE']
        #includeLocalData = False -- unused
        #includeOfficeData = False -- unused
        ]
    
    DF_OG = pd.DataFrame()

    url_backup_file = 'url_backup'
    url_backup_path = url_backup_file + '/'
    script_dir0 = os.path.dirname(os.path.dirname(__file__))
    abs_path0 = os.path.join(script_dir0, url_backup_path)

    OLD_DATA = False
    if New_Data_On_Run_Test: OLD_DATA = True #reset for testing
    PATH_EXISTS = os.path.exists(abs_path0)
    if PATH_EXISTS: #check file age
        dir = os.listdir(abs_path0)
        if len(dir) == 0: OLD_DATA = True
        import glob
        csv_files = glob.glob(os.path.join(abs_path0, "*.csv"))
        for f in csv_files:
            if time.time() - os.path.getmtime(f) > (1 * 30 * 24 * 60 * 60): #if older than one month
                OLD_DATA = True
                os.remove(f) #remove and make new

    if PATH_EXISTS and not OLD_DATA: #cleaned files exist and newer than one month
        import glob
        csv_files = glob.glob(os.path.join(abs_path0, "*.csv"))
        for f in csv_files:
            df_backup = pd.read_csv(f, encoding = "ISO-8859-1", low_memory=False, thousands=',', nrows=TEST_CASES, dtype={'zip_cd': 'str'} )
            DF_OG = pd.concat([df_backup, DF_OG], ignore_index=True)
        
    else: #read new files from url source
        count = 1
        for n in url_list:
            url = n[0]
            out_file_report = n[2]
            df_url = pd.DataFrame()
            df_url = Read_Violation_Data(TEST_CASES, url, out_file_report)
            df_url = df_url.replace('\s', ' ', regex=True)  # remove line returns
            df_url = clean_function(RunFast, df_url, FLAG_DUPLICATE, bug_log, LOGBUG, log_number)
            df_url = inference_function(df_url, infer_zip, cityDict, infer_by_naics, TARGET_INDUSTRY, 
                prevailing_wage_report, includeFedData, SIGNATORY_INDUSTRY, prevailing_wage_terms, bug_log, LOGBUG, log_number)
            save_backup_to_folder(df_url, url_backup_file+str(count), url_backup_path)
            count += 1
            DF_OG = pd.concat([df_url, DF_OG], ignore_index=True)
            
    time_2 = time.time()
    append_log(bug_log, LOGBUG, f"Time to read csv(s) " + "%.5f" % (time_2 - time_1) + "\n")

    out_target = DF_OG.copy()  # new df -- hold df_csv as a backup and only df from this point on
    
    for n in url_list: #filter dataset for this run -- example, remove fed and state
        if n[1] == 0: out_target = out_target[out_target.juris_or_proj_nm != n[2]]

    out_target = filter_function(out_target, TARGET_ZIPCODES, TARGET_INDUSTRY, open_cases_only,
                    ORGANIZATION_FILTER, TARGET_ORGANIZATIONS, bug_log, LOGBUG, log_number)

    # note--estimate back wage, penaly, and interest, based on violation
    time_1 = time.time()
    total_ee_violtd = out_target['ee_violtd_cnt'].sum()
    total_bw_atp = out_target['bw_amt'].sum()
    total_case_violtn = out_target['violtn_cnt'].sum()
    if use_assumptions: 
        out_target = calculate_interest_owed(out_target)
        #NEED TO DEBUG out_target = infer_wage_penalty(out_target)  # B backwage, M monetary penalty
        out_target = backwages_owed(out_target)
        out_target = compute_and_add_violation_count_assumptions(out_target)
        # out_target.to_csv(bug_log_csv) #debug outfile
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # filter
    time_1 = time.time()
    unique_legalname_sig = GroupByX(out_target, 'legal_nm')
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    #unique_legalname_sig  = unique_legalname_sig[~unique_legalname_sig.index.duplicated()]
    time_1 = time.time()
    if 'Prevailing' in out_target.columns:
        out_prevailing_target = unique_legalname_sig.loc[unique_legalname_sig['Prevailing'] == 1]
    if "Signatory" in out_target.columns:
        out_signatory_target = unique_legalname_sig.loc[unique_legalname_sig["Signatory"] == 1]
    if signatories_report == 0 and 'Signatory' and 'legal_nm' and 'trade_nm' in out_target.columns:
        # unused out_target = out_target.loc[out_target['Signatory']!=1] #filter
        out_target['legal_nm'] = np.where(
            out_target['Signatory'] == 1, "masked", out_target['legal_nm'])
        out_target['trade_nm'] = np.where(
            out_target['Signatory'] == 1, "masked", out_target['trade_nm'])
        out_target['street_addr'] = np.where(
            out_target['Signatory'] == 1, "masked", out_target['street_addr'])
        out_target['case_id'] = np.where(
            out_target['Signatory'] == 1, "masked", out_target['case_id'])
        if 'DIR_Case_Name' in out_target.columns:
            out_target['DIR_Case_Name'] = np.where(
                out_target['Signatory'] == 1, "masked", out_target['DIR_Case_Name'])
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")
    # create csv output file**********************************
    # option to_csv_test_header = ['trade_nm','legal_nm','industry']
    # option out_target[to_csv_test_header]
    
    time_1 = time.time()
    # added to prevent bug that outputs 2x
    out_target = out_target.drop_duplicates(keep='last')
    out_target.to_csv(temp_file_name_csv, encoding="utf-8-sig")
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")
    
    # summary
    time_1 = time.time()
    all_unique_legalname = GroupByMultpleCases(out_target, 'legal_nm')
    all_unique_legalname = all_unique_legalname.sort_values(
        by=['records'], ascending=False)
    all_agency_df = GroupByMultpleAgency(out_target)
    all_agency_df = all_agency_df.sort_values(by=['records'], ascending=False)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # group repeat offenders************************************
    time_1 = time.time()
    out_counts = out_target.copy()  # hold for case counts

    unique_legalname = GroupByX(out_target, 'legal_nm')

    unique_address = GroupByMultpleCases(out_target, 'street_addr')
    unique_legalname2 = GroupByMultpleCases(out_target, 'legal_nm')
    unique_tradename = GroupByMultpleCases(out_target, 'trade_nm')
    unique_agency = GroupByMultpleCases(out_target, 'juris_or_proj_nm')
    unique_owner = GroupByMultpleCases(
        out_target, 'Jurisdiction_region_or_General_Contractor')
    agency_df = GroupByMultpleAgency(out_target)

    out_target = unique_legalname.copy()
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # sort and format************************************

    # sort for table
    time_1 = time.time()
    out_sort_ee_violtd = out_target.sort_values(
        by=['ee_violtd_cnt'], ascending=False)
    out_sort_bw_amt = out_target.sort_values(by=['bw_amt'], ascending=False)
    out_sort_repeat_violtd = out_target.sort_values(
        by=['records'], ascending=False)

    unique_address = unique_address.sort_values(
        by=['records'], ascending=False)
    unique_legalname = unique_legalname.sort_values(
        by=['records'], ascending=False)
    unique_legalname2 = unique_legalname2.sort_values(
        by=['records'], ascending=False)
    unique_tradename = unique_tradename.sort_values(
        by=['records'], ascending=False)
    unique_agency = unique_agency.sort_values(by=['records'], ascending=False)
    unique_owner = unique_owner.sort_values(by=['records'], ascending=False)
    agency_df = agency_df.sort_values(by=['records'], ascending=False)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # Format for summary
    time_1 = time.time()
    
    DF_OG_ALL = DF_OG.copy()
    DF_OG_ALL = DropDuplicateRecords(DF_OG_ALL, FLAG_DUPLICATE)

    DF_OG_VLN = DF_OG.copy()
    DF_OG_VLN = DropDuplicateRecords(DF_OG_VLN, FLAG_DUPLICATE)
    DF_OG_VLN = Clean_Summary_Values(DF_OG_VLN)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # report headers***************************************************
    # note that some headers have been renamed at the top of this program
    time_1 = time.time()
    header_two_way_table = ["violtn_cnt",
                            "ee_violtd_cnt", "bw_amt", "records", "ee_pmt_recv"]
    header = ["legal_nm", "trade_nm", "cty_nm"] + header_two_way_table
    header_two_way = header_two_way_table + \
        ["zip_cd", 'legal_nm', "juris_or_proj_nm", 'case_id',
            'violation', 'violation_code', 'backwage_owed']

    header += ["naics_desc."]

    prevailing_header = header + ["juris_or_proj_nm", "Note"]

    if signatories_report == 1:
        header += ["Signatory"]
        prevailing_header += ["Signatory"]

    dup_header = header + ["street_addr"]
    dup_agency_header = header_two_way_table + ["juris_or_proj_nm"]
    dup_owner_header = header_two_way_table + \
        ["Jurisdiction_region_or_General_Contractor"]

    multi_agency_header = header + ["agencies", "agency_names", "street_addr"]
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # textfile output***************************************
    # HTML opening
    time_1 = time.time()

    # report main file--`w' create/zero text file for writing: the stream is positioned at the beginning of the file.
    textFile = open(temp_file_name, 'w')
    textFile.write("<!DOCTYPE html> \n")
    textFile.write("<html><body> \n")

    Title_Block(TEST_, DF_OG_VLN, DF_OG_ALL, target_jurisdition, TARGET_INDUSTRY,
                prevailing_wage_report, includeFedData, includeStateData, textFile)

    if all_industry_summary_block == 1:
        #Regional_All_Industry_Summary_Block(DF_OG, DF_OG, total_ee_violtd, total_bw_atp, total_case_violtn, 
        #    all_unique_legalname, all_agency_df, open_cases_only, textFile)
        do_nothing = "<p>Purposful Omission of All Industry Summary Block</p>"

    if Nonsignatory_Ratio_Block == True:
        #Signatory_to_Nonsignatory_Block(DF_OG, DF_OG, textFile)
        do_nothing = "<p>Purposful Omission of Nonsignatory Ratio Block</p>"

    if math.isclose(DF_OG['bw_amt'].sum(), out_counts['bw_amt'].sum(), rel_tol=0.03, abs_tol=0.0):
        do_nothing = "<p>Purposful Omission of Industry Summary Block</p>"
    else:
        Industry_Summary_Block(out_counts, out_counts, total_ee_violtd, total_bw_atp,
            total_case_violtn, unique_legalname, agency_df, open_cases_only, textFile)

    textFile.write("<HR> </HR>")  # horizontal line

    Notes_Block(textFile)

    Methods_Block(textFile)

    Footer_Block(TEST_, textFile)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # HTML closing
    time_1 = time.time()
    textFile.write("<P style='page-break-before: always'>")
    textFile.write("</html></body>")
    textFile.close()
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    # TABLES
    time_1 = time.time()
    if include_tables == 1: 
        print_table_html_by_industry_and_city(temp_file_name, unique_legalname, header_two_way_table)
        print_table_html_by_industry_and_zipcode(temp_file_name, unique_legalname, header_two_way_table)
        print_table_html_Text_Summary(include_summaries, temp_file_name, unique_legalname, header_two_way, header_two_way_table,
            total_ee_violtd, total_case_violtn, only_sig_summaries, TARGET_INDUSTRY)

        if include_top_viol_tables == 1:
            print_top_viol_tables_html(out_target, unique_address, unique_legalname2, 
                unique_tradename, unique_agency, unique_owner, agency_df, out_sort_ee_violtd, 
                out_sort_bw_amt, out_sort_repeat_violtd, temp_file_name, signatories_report,
                out_signatory_target, sig_file_name_csv, prevailing_header, header, multi_agency_header, 
                dup_agency_header, dup_header, dup_owner_header, prevailing_wage_report, out_prevailing_target, 
                prev_file_name_csv, TEST_)
    time_2 = time.time()
    # updated 8/10/2022 by f. peterson to .format() per https://stackoverflow.com/questions/18053500/typeerror-not-all-arguments-converted-during-string-formatting-python
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} " + "%.5f" % (time_2 - time_1) + "\n")

    append_log(bug_log, LOGBUG, f"Time to finish report " + "%.5f" % (time_2 - time_0) + "\n")
    append_log(bug_log, LOGBUG, "<h1>DONE</h1> \n" + "</html></body> \n") #CLOSE
    # updated 8/10/2022 by f. peterson to .format() per https://stackoverflow.com/questions/18053500/typeerror-not-all-arguments-converted-during-string-formatting-python
    return temp_file_name  # the temp json returned from API




def search_Dict_tree(target_state, target_county, target_city, stateDict, countyDict, cityDict):

    #check to verify that only lowest level has data
    #initialize lists
    STATE_LIST = []
    COUNTY_LIST = []
    CITY_LIST = []
    ZIPCODE_LIST = []

    target_region = target_state #temp hack to make a regional list
    if target_region == "": STATE_LIST = []
    else: 
        STATE_LIST = [target_region, target_region][1:] #dummy of nationDict[target_region]
        ZIPCODE_LIST = [[target_region, target_region][0]]
        target_state = ""
        target_county = ""
        target_city = ""
    if target_state == "": COUNTY_LIST = []
    else: 
        COUNTY_LIST = stateDict[target_state][1:]
        ZIPCODE_LIST = [stateDict[target_state][0]]
        target_county = ""
        target_city = ""
    if target_county == "": CITY_LIST = []
    else: 
        CITY_LIST = countyDict[target_county][1:]
        ZIPCODE_LIST = [countyDict[target_county][0]]
        target_city = ""
    if target_city == "": "DO_NOTHING" #base case passes through last for loop
    else: 
        ZIPCODE_LIST = cityDict[target_city]
        #target_precinct = ""
        
    for states in STATE_LIST if STATE_LIST else range(1):
        if STATE_LIST: 
            COUNTY_LIST.extend(stateDict[states][1:]) # [1:] to skip region name in cell one
    
    for counties in COUNTY_LIST if COUNTY_LIST else range(1):
        if COUNTY_LIST: 
            CITY_LIST.extend(countyDict[counties][1:]) # [1:] to skip region name in cell one
        
    for city in CITY_LIST if CITY_LIST else range(1):
        if CITY_LIST: 
            ZIPCODE_LIST.extend(cityDict[city][1:]) #[1:] to skip region name in cell one
            
            tempA = cityDict[city][len(cityDict[city]) - 1] #take the last zipcode for region and modify w/ ending 'xx'

            ZIPCODE_LIST.append(generate_generic_zipcode_for_city(tempA) )

                ##add precinct level loop which replaces zipcode level and adds mass confusion

    ZIPCODE_LIST = list( dict.fromkeys(ZIPCODE_LIST) ) #remove duplicates created in defualt region generation

    return ZIPCODE_LIST


def generate_generic_zipcode_for_city(tempA, n_char = 1):
    #add a generic zipcode for each city -- used later to filter records:
    position = len(tempA)
    # n_char -- replace just last zip code char seems to work best
    suffix = "X" * n_char
    tempB = tempA[:position-n_char] + suffix
    return tempB


def clean_function(RunFast, df, FLAG_DUPLICATE, bug_log, LOGBUG, log_number):

    function_name = "clean_function"

    if not RunFast:
        time_1 = time.time()
        df = Define_Column_Types(df)
        time_2 = time.time()
        log_number+=1
        append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

        # remove duplicate cases using case_id and violation as a unique key
        time_1 = time.time()
        df = DropDuplicateRecords(df, FLAG_DUPLICATE)
        df = DropDuplicateBackwage(df, FLAG_DUPLICATE)
        time_2 = time.time()
        log_number+=1
        append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

        time_1 = time.time()
        df = Cleanup_Number_Columns(df)
        df = Cleanup_Text_Columns(df)
        time_2 = time.time()
        log_number+=1
        append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

        time_1 = time.time()
        df = CleanUpAgency(df, 'juris_or_proj_nm')
        time_2 = time.time()
        log_number+=1
        append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    return df


def inference_function(df, infer_zip, cityDict, infer_by_naics, TARGET_INDUSTRY, 
        prevailing_wage_report, includeFedData, SIGNATORY_INDUSTRY, prevailing_wage_terms, bug_log, LOGBUG, log_number):

    function_name = "inference_function"

    # zip codes infer *********************************
    time_1 = time.time()
    #if infer_zip == 1: 
    InferZipcode(df, cityDict)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    time_1 = time.time()
    df = Infer_Industry(df, infer_by_naics, TARGET_INDUSTRY)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")
    # unused df = Filter_for_Target_Industry(df,TARGET_INDUSTRY) ##debug 12/23/2020 <-- run here for faster time but without global summary
    
    time_1 = time.time()
    df = InferAgencyFromCaseIDAndLabel(df, 'juris_or_proj_nm')
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")
    # use for debugging df.to_csv(bug_log_csv) #debug outfile

    # PREVAILING WAGE
    time_1 = time.time()
    df = infer_prevailing_wage_cases(df, includeFedData, prevailing_wage_terms)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    # infer signatories
    time_1 = time.time()
    df = infer_signatory_cases(df, SIGNATORY_INDUSTRY)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    time_1 = time.time()
    df = wages_owed(df)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    return df


def filter_function(df, TARGET_ZIPCODES, TARGET_INDUSTRY, open_cases_only,
    ORGANIZATION_FILTER, TARGET_ORGANIZATIONS, bug_log, LOGBUG, log_number):

    function_name = "filter_function"

    # unused df = FilterForDate(df, YEAR_START, YEAR_END) #filter for date
    
    df.to_csv("test_out_A.csv") #temp debug 2/1/2023

    # zip codes filter *********************************
    time_1 = time.time()
    df = Filter_for_Zipcode(df, TARGET_ZIPCODES)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    df.to_csv("test_out_B.csv") #temp debug 2/1/2023

    time_1 = time.time()
    df = Filter_for_Target_Industry(df, TARGET_INDUSTRY)
    if open_cases_only == 1: df = RemoveCompletedCases(df)
    if ORGANIZATION_FILTER: df = Filter_for_Target_Organization(df, TARGET_ORGANIZATIONS)
    time_2 = time.time()
    log_number+=1
    append_log(bug_log, LOGBUG, f"Time to finish section {log_number} in {function_name} " + "%.5f" % (time_2 - time_1) + "\n")

    return df



def InferZipcode(df, cityDict):
    if not df.empty:
        df = InferZipcodeFromCityName(df, cityDict)  # zipcodes by city name
        df = InferZipcodeFromCompanyName(df, cityDict) #zipcodes by company name
        df = InferZipcodeFromJurisdictionName(df, cityDict) #zipcodes by jurisdiction name -- many false positive -- last ditch if no city name
        df = FillBlankZipcodes(df)
    return df


def infer_signatory_cases(df, SIGNATORY_INDUSTRY):
    if "Signatory" not in df.columns:
        df["Signatory"] = 0
    if 'signatory_industry' not in df.columns:
        df['signatory_industry'] = ""
    df = InferSignatoriesFromNameAndFlag(df, SIGNATORY_INDUSTRY)
    df = InferSignatoryIndustryAndLabel(df, SIGNATORY_INDUSTRY)
    # unused df_temp_address = InferSignatoriesFromAddressAndFlag(df, signatory_address_list)
    # unused df = InferSignatoriesFromNameAndAddressFlag(df, signatory_list, signatory_address_list)
    # unused df = df.append(df_temp_address)
    return df


def infer_prevailing_wage_cases(df, includeFedData, prevailing_wage_terms):
    if includeFedData == 1:
        df = infer_WHD_prevailing_wage_violation(df)
    df = InferPrevailingWageAndColumnFlag(df, prevailing_wage_terms)
    return df


def print_table_html_by_industry_and_city(temp_file_name, unique_legalname, header_two_way_table):

    # report main file--'a' Append, the file is created if it does not exist: stream is positioned at the end of the file.
    textFile = open(temp_file_name, 'a')
    textFile.write("<h2>Wage theft by industry and city region</h2> \n")
    textFile.close()

    df_all_industry = unique_legalname.groupby(['industry', pd.Grouper(key='cty_nm')]).agg({  # https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
        "bw_amt": 'sum',
        "violtn_cnt": 'sum',
        "ee_violtd_cnt": 'sum',
        "ee_pmt_recv": 'sum',
        "records": 'sum',
    }).reset_index().sort_values(['industry', 'cty_nm'], ascending=[True, True])

    df_all_industry = df_all_industry.set_index(['industry', 'cty_nm'])
    df_all_industry = df_all_industry.sort_index()

    df_all_industry = df_all_industry.reindex(columns=header_two_way_table)
    for industry, new_df in df_all_industry.groupby(level=0):

        new_df = pd.concat([
            new_df,
            new_df.sum().to_frame().T.assign(
                industry='', cty_nm='COUNTYWIDE').set_index(['industry', 'cty_nm'])
        ], sort=True).sort_index()

        new_df["bw_amt"] = new_df.apply(
            lambda x: "{0:,.0f}".format(x["bw_amt"]), axis=1)
        new_df["violtn_cnt"] = new_df.apply(
            lambda x: "{0:,.0f}".format(x["violtn_cnt"]), axis=1)
        new_df["ee_violtd_cnt"] = new_df.apply(
            lambda x: "{0:,.0f}".format(x["ee_violtd_cnt"]), axis=1)
        new_df["ee_pmt_recv"] = new_df.apply(
            lambda x: "{0:,.0f}".format(x["ee_pmt_recv"]), axis=1)
        new_df["records"] = new_df.apply(
            lambda x: "{0:,.0f}".format(x["records"]), axis=1)

        write_to_html_file(new_df, header_two_way_table,
                            "", file_path(temp_file_name))


def print_table_html_by_industry_and_zipcode(temp_file_name, unique_legalname, header_two_way_table):

    textFile = open(temp_file_name, 'a')  # append to main report file
    textFile.write(
        "<h2>Wage theft by zip code region and industry</h2> \n")
    textFile.close()

    df_all_industry_3 = unique_legalname.groupby(["zip_cd", pd.Grouper(key='industry')]).agg({  # https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
        "bw_amt": 'sum',
        "violtn_cnt": 'sum',
        "ee_violtd_cnt": 'sum',
        "ee_pmt_recv": 'sum',
        "records": 'sum',
    }).reset_index().sort_values(['zip_cd', 'industry'], ascending=[True, True])

    df_all_industry_3 = df_all_industry_3.set_index(['zip_cd', 'industry'])
    df_all_industry_3 = df_all_industry_3.sort_index()

    df_all_industry_3 = df_all_industry_3.reindex(columns=header_two_way_table)
    for zip_cd, new_df_3 in df_all_industry_3.groupby(level=0):

        new_df_3 = pd.concat([
            new_df_3,
            new_df_3.sum().to_frame().T.assign(
                zip_cd='', industry='ZIPCODEWIDE').set_index(['zip_cd', 'industry'])
        ], sort=True).sort_index()

        new_df_3["bw_amt"] = new_df_3.apply(
            lambda x: "{0:,.0f}".format(x["bw_amt"]), axis=1)
        new_df_3["ee_pmt_recv"] = new_df_3.apply(
            lambda x: "{0:,.0f}".format(x["ee_pmt_recv"]), axis=1)
        new_df_3["records"] = new_df_3.apply(
            lambda x: "{0:,.0f}".format(x["records"]), axis=1)
        new_df_3["violtn_cnt"] = new_df_3.apply(
            lambda x: "{0:,.0f}".format(x["violtn_cnt"]), axis=1)
        new_df_3["ee_violtd_cnt"] = new_df_3.apply(
            lambda x: "{0:,.0f}".format(x["ee_violtd_cnt"]), axis=1)

        write_to_html_file(new_df_3, header_two_way_table,
                            "", file_path(temp_file_name))


def print_table_html_Text_Summary(include_summaries, temp_file_name, unique_legalname, header_two_way, header_two_way_table,
    total_ee_violtd, total_case_violtn, only_sig_summaries, TARGET_INDUSTRY):
    if include_summaries == 1:
        
        if 'backwage_owed' not in unique_legalname.columns: unique_legalname['backwage_owed'] = 0 #hack bug fix 10/29/2022

        df_all_industry_n = unique_legalname.groupby(["cty_nm", pd.Grouper(key="zip_cd"), pd.Grouper(key='industry'),  pd.Grouper(key='legal_nm')]).agg({  # https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
            "bw_amt": 'sum',
            "violtn_cnt": 'sum',
            "ee_violtd_cnt": 'sum',
            "ee_pmt_recv": 'sum',
            'backwage_owed': 'sum',
            "records": 'sum',
        }).reset_index().sort_values(['cty_nm', "zip_cd", 'industry', 'legal_nm'], ascending=[True, True, True, True])

        df_all_industry_n = df_all_industry_n.set_index(
            ['cty_nm', "zip_cd", 'industry', 'legal_nm'])
        df_all_industry_n = df_all_industry_n.sort_index()

        df_all_industry_n = df_all_industry_n.reindex(columns=header_two_way)
    
        RunHeaderOnce = True
        for cty_nm, new_df_n, in df_all_industry_n.groupby(level=0):

            # new_df_2 = new_df_n.reset_index(level=1, drop=True).copy() #make a copy without zipcode level 0
            new_df_2 = new_df_n.droplevel("zip_cd").copy()

            new_df_legal_nm = new_df_2.drop(
                columns=['legal_nm'])  # delete empty column
            # pull out legal_nm column from level
            new_df_legal_nm = new_df_legal_nm.reset_index()
            city_unique_legalname = GroupByX(new_df_legal_nm, 'legal_nm')
            city_total_bw_atp = new_df_2['bw_amt'].sum()
            # debug 10/30/2020 this is an approximation based on records which is actually an overtstated mix of case and violations counts
            city_cases = new_df_2['records'].sum()

            new_df_drop1 = new_df_n.droplevel("zip_cd").copy()
            new_df_drop1 = new_df_drop1.droplevel('legal_nm')
            city_agency_df = GroupByMultpleAgency(new_df_drop1)

            #PRINT SECTION HEADER
            if RunHeaderOnce and (only_sig_summaries == 0 or city_cases > 10 or city_total_bw_atp > 10000):
                RunHeaderOnce = False
                textFile = open(temp_file_name, 'a')  # append to report main file
                textFile.write("<h2>Wage theft by city and industry</h2> \n")
                textFile.close()

            #PRINT SUMMARY BLOCK
            if only_sig_summaries == 0 or (city_cases > 10 or city_total_bw_atp > 10000):
                City_Summary_Block(city_cases, new_df_2, total_ee_violtd, city_total_bw_atp, total_case_violtn,
                                city_unique_legalname, city_agency_df, cty_nm, only_sig_summaries, file_path(temp_file_name))
                City_Summary_Block_4_Zipcode_and_Industry(
                    new_df_n, df_all_industry_n, TARGET_INDUSTRY, only_sig_summaries, file_path(temp_file_name))

                #Industry_Summary_Block(city_cases, new_df_2, total_ee_violtd, city_total_bw_atp, total_case_violtn, city_unique_legalname, city_agency_df, cty_nm, SUMMARY_SIG, file_path(temp_file_name))
                #Industry_Summary_Block_4_Zipcode_and_City(new_df_n, df_all_industry_n, TARGET_INDUSTRY, SUMMARY_SIG, file_path(temp_file_name) )

            new_df_2 = new_df_2.groupby(["cty_nm", 'industry']).agg({  # https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
                "bw_amt": 'sum',
                "violtn_cnt": 'sum',
                "ee_violtd_cnt": 'sum',
                "ee_pmt_recv": 'sum',
                "records": 'sum',
            }).reset_index().sort_values(['cty_nm', 'industry'], ascending=[True, True])

            new_df_2 = new_df_2.set_index(['cty_nm', 'industry'])
            new_df_2 = new_df_2.sort_index()

            #commented out to test 1/29/2023
            
            new_df_2 = pd.concat([
                new_df_2.sum().to_frame().T.assign(
                    cty_nm='', industry='CITYWIDE').set_index(['cty_nm', 'industry'])
                , new_df_2
            ], sort=True).sort_index()
            

            # new_df_2 = new_df_2.loc[:,~new_df_2.columns.duplicated()] #https://stackoverflow.com/questions/14984119/python-pandas-remove-duplicate-columns

            new_df_2["bw_amt"] = new_df_2.apply(
                lambda x: "{0:,.0f}".format(x["bw_amt"]), axis=1)
            new_df_2["ee_pmt_recv"] = new_df_2.apply(
                lambda x: "{0:,.0f}".format(x["ee_pmt_recv"]), axis=1)
            new_df_2["records"] = new_df_2.apply(
                lambda x: "{0:,.0f}".format(x["records"]), axis=1)
            new_df_2["violtn_cnt"] = new_df_2.apply(
                lambda x: "{0:,.0f}".format(x["violtn_cnt"]), axis=1)
            new_df_2["ee_violtd_cnt"] = new_df_2.apply(
                lambda x: "{0:,.0f}".format(x["ee_violtd_cnt"]), axis=1)

            #PRINT DATA TABLE
            if only_sig_summaries == 0 or (city_cases > 10 or city_total_bw_atp > 10000):
                write_to_html_file(new_df_2, header_two_way_table,
                                "", file_path(temp_file_name))


def print_top_viol_tables_html(df, unique_address, unique_legalname2, 
    unique_tradename, unique_agency, unique_owner, agency_df, out_sort_ee_violtd, 
    out_sort_bw_amt, out_sort_repeat_violtd, temp_file_name, signatories_report,
    out_signatory_target, sig_file_name_csv, prevailing_header, header, multi_agency_header, dup_agency_header, dup_header, 
    dup_owner_header, prevailing_wage_report, out_prevailing_target, prev_file_name_csv, TEST):

    if not df.empty:
        import matplotlib

        # format
        unique_address = Clean_Repeat_Violator_HTML_Row(
            unique_address, 'street_addr')
        unique_address = FormatNumbersHTMLRow(unique_address)

        unique_legalname2 = Clean_Repeat_Violator_HTML_Row(
            unique_legalname2, 'legal_nm')
        unique_legalname2 = FormatNumbersHTMLRow(unique_legalname2)

        unique_tradename = Clean_Repeat_Violator_HTML_Row(
            unique_tradename, 'trade_nm')
        unique_tradename = FormatNumbersHTMLRow(unique_tradename)

        unique_agency = Clean_Repeat_Violator_HTML_Row(
            unique_agency, 'juris_or_proj_nm')
        unique_agency = FormatNumbersHTMLRow(unique_agency)

        unique_owner = Clean_Repeat_Violator_HTML_Row(
            unique_owner, 'Jurisdiction_region_or_General_Contractor')
        unique_owner = FormatNumbersHTMLRow(unique_owner)

        agency_df = FormatNumbersHTMLRow(agency_df)

        out_sort_ee_violtd = FormatNumbersHTMLRow(out_sort_ee_violtd)
        out_sort_bw_amt = FormatNumbersHTMLRow(out_sort_bw_amt)
        out_sort_repeat_violtd = FormatNumbersHTMLRow(out_sort_repeat_violtd)

        df.plot()  # table setup

        # tables top 10 violators

        with open(temp_file_name, 'a', encoding='utf-8') as f:  # append to report main file

            if not out_sort_bw_amt.empty:
                # by backwages
                f.write(
                    "<h2>Top violators by amount of backwages stolen (by legal name)</h2> \n")
                out_sort_bw_amt.head(6).to_html(f, columns=header, index=False)
                f.write("\n")

            if not out_sort_ee_violtd.empty:
                # by employees
                f.write(
                    "<h2>Top violators by number of employees violated (by legal name)</h2> \n")
                out_sort_ee_violtd.head(6).to_html(
                    f, columns=header, index=False)
                f.write("\n")

            if not out_sort_repeat_violtd.empty:
                # by repeated
                f.write(
                    "<h2>Top violators by number of repeat violations (by legal name)</h2> \n")
                out_sort_repeat_violtd.head(6).to_html(
                    f, columns=header, index=False)
                f.write("\n")

            # by repeat violators******************
            row_head = 24
            if not unique_address.empty:
                # by unique_address
                f.write("<h2>Group by address and sort by records</h2> \n")
                unique_address.head(row_head).to_html(
                    f, columns=dup_header, index=False)
                f.write("\n")
            else:
                f.write("<p> There are no groups by address to report</p> \n")

            if not unique_legalname2.empty:
                # by 'legal_name'
                f.write("<h2>Group by legal name and sort by records</h2> \n")
                unique_legalname2.head(row_head).to_html(
                    f, columns=dup_header, index=False)
                f.write("\n")
            else:
                f.write("<p> There are no groups by legal name to report</p> \n")

            if not unique_tradename.empty and TEST != 3:
                # by unique_trade_nm
                f.write("<h2>Group by trade name and sort by records</h2> \n")
                unique_tradename.head(row_head).to_html(
                    f, columns=dup_header, index=False)
                f.write("\n")
            else:
                f.write("<p> There are no groups by trade name to report</p> \n")

            if not agency_df.empty:
                # report for cases from multiple agencies
                f.write(
                    "<h2>Group by company and sort by number of agencies involved</h2> \n")
                agency_df.head(row_head).to_html(
                    f, columns=multi_agency_header, index=False)
                f.write("\n")
            else:
                f.write(
                    "<p> There are no groups by companies with violations by multiple agencies to report</p> \n")

            if not unique_agency.empty:
                # report agency counts
                # by unique_agency
                f.write("<h2>Cases by agency or owner</h2> \n")
                unique_agency.head(row_head).to_html(
                    f, columns=dup_agency_header, index=False)
                f.write("\n")
            else:
                f.write(
                    "<p> There are no case groups by agency or owner to report</p> \n")

            if not unique_owner.empty:
                # by 'unique_owner'
                f.write(
                    "<h2>Cases by jurisdiction (includes private jurisdictions)</h2> \n")
                unique_owner.head(row_head).to_html(
                    f, columns=dup_owner_header, index=False)
                f.write("\n")
            else:
                f.write(
                    "<p> There are no case groups by jurisdiction to report</p> \n")

            # signatory
            if signatories_report == 1 and not out_signatory_target.empty:

                out_sort_signatory = pd.DataFrame()
                out_sort_signatory = out_signatory_target.sort_values(
                    'legal_nm', ascending=True)

                out_sort_signatory['violtn_cnt'] = out_sort_signatory.apply(
                    lambda x: "{0:,.0f}".format(x['violtn_cnt']), axis=1)
                out_sort_signatory['ee_pmt_recv'] = out_sort_signatory.apply(
                    lambda x: "{0:,.0f}".format(x['ee_pmt_recv']), axis=1)

                f.write("<P style='page-break-before: always'>")
                out_sort_signatory.to_csv(sig_file_name_csv)

                f.write("<h2>All signatory wage violators</h2> \n")

                if not len(out_sort_signatory.index) == 0:
                    f.write("<p>Signatory wage theft cases: ")
                    f.write(str.format('{0:,.0f}', len(
                        out_sort_signatory.index)))
                    f.write("</p> \n")

                if not out_sort_signatory['bw_amt'].sum() == 0:
                    f.write("<p>Total signatory wage theft: $")
                    f.write(str.format(
                        '{0:,.0f}', out_sort_signatory['bw_amt'].sum()))
                    f.write("</p> \n")
                '''
                if not out_sort_signatory['ee_violtd_cnt'].sum()==0:
                    f.write("<p>Signatory wage employees violated: ")
                    out_sort_signatory['ee_violtd_cnt'] = pd.to_numeric(out_sort_signatory['ee_violtd_cnt'], errors = 'corece')
                    f.write(str.format('{0:,.0f}',out_sort_signatory['ee_violtd_cnt'].sum() ) )
                    f.write("</p> \n")

                if not out_sort_signatory['violtn_cnt'].sum()==0:
                    f.write("<p>Signatory wage violations: ")
                    out_sort_signatory['violtn_cnt'] = pd.to_numeric(out_sort_signatory['violtn_cnt'], errors = 'corece')
                    f.write(str.format('{0:,.0f}',out_sort_signatory['violtn_cnt'].sum() ) )
                    f.write("</p> \n")
                '''

                f.write("\n")

                out_sort_signatory.to_html(
                    f, max_rows=3000, columns=prevailing_header, index=False)

                f.write("\n")

            # prevailing wage
            if prevailing_wage_report == 1 and not out_prevailing_target.empty:
                out_sort_prevailing_wage = pd.DataFrame()
                #out_sort_prevailing_wage = out_prevailing_target.sort_values('records', ascending=False)
                out_sort_prevailing_wage = out_prevailing_target.sort_values(
                    'legal_nm', ascending=True)

                out_sort_prevailing_wage['violtn_cnt'] = out_sort_prevailing_wage.apply(
                    lambda x: "{0:,.0f}".format(x['violtn_cnt']), axis=1)
                out_sort_prevailing_wage['ee_pmt_recv'] = out_sort_prevailing_wage.apply(
                    lambda x: "{0:,.0f}".format(x['ee_pmt_recv']), axis=1)

                f.write("<P style='page-break-before: always'>")
                out_sort_prevailing_wage.to_csv(prev_file_name_csv)

                f.write("<h2>All prevailing wage violators</h2> \n")

                f.write("<p>Prevailing wage theft cases: ")
                f.write(str.format('{0:,.0f}', len(
                    out_sort_prevailing_wage.index)))
                #f.write(str.format('{0:,.0f}',len(out_sort_prevailing_wage['records'].sum() ) ) )
                f.write("</p> \n")

                f.write("<p>Total prevailing wage theft: $")
                f.write(str.format(
                    '{0:,.0f}', out_sort_prevailing_wage['bw_amt'].sum()))
                f.write("</p> \n")

                f.write("<p>Total prevailing wage theft: $")
                f.write(str.format(
                    '{0:,.0f}', out_sort_prevailing_wage['bw_amt'].sum()))
                f.write("</p> \n")

                # buggy 6/14/2021
                # f.write("<p>Prevailing wage employees violated: ")
                # out_sort_prevailing_wage['ee_violtd_cnt'] = pd.to_numeric(out_sort_prevailing_wage['ee_violtd_cnt'], errors = 'corece')
                # f.write(str.format('{0:,.0f}',out_sort_prevailing_wage['ee_violtd_cnt'].sum() ) )
                # f.write("</p> \n")

                # f.write("<p>Prevailing wage violations: ")
                # out_sort_prevailing_wage['violtn_cnt'] = pd.to_numeric(out_sort_prevailing_wage['violtn_cnt'], errors = 'corece')
                # f.write(str.format('{0:,.0f}',out_sort_prevailing_wage['violtn_cnt'].sum() ) )
                # f.write("</p> \n")

                f.write("\n")
                # 12/25/2021 added "float_format=lambda x: '%10.2f' % x" per https://stackoverflow.com/questions/14899818/format-output-data-in-pandas-to-html
                out_sort_prevailing_wage.to_html(
                    f, max_rows=3000, columns=prevailing_header, index=False, float_format=lambda x: '%10.2f' % x)

                f.write("\n")


def Clean_Repeat_Violator_HTML_Row(df, COLUMN_NAME):
    # df = df.dropna(subset=[COLUMN_NAME]) #drop NAs
    # https://stackoverflow.com/questions/18172851/deleting-dataframe-row-in-pandas-based-on-column-value
    df = df[df.records > 1]

    if df.empty:
        df = df.append({
            COLUMN_NAME: "no records",
        }, ignore_index=True)
    return df


def GroupByX(df, COLUMN_NAME):

    if COLUMN_NAME in df.columns and not df[COLUMN_NAME].isnull().all():

        df = df[df[COLUMN_NAME].notnull()]
        df = df[df[COLUMN_NAME] != 'nan']
        df = df[df[COLUMN_NAME] != 'NAN']
        df = df[df[COLUMN_NAME] != '']
        df = df[df[COLUMN_NAME] != 0]
        df = df[df[COLUMN_NAME] != False]

        df[COLUMN_NAME] = df[COLUMN_NAME].str.upper()

        df['records'] = 1
        df['records'] = df.groupby(COLUMN_NAME)[COLUMN_NAME].transform(
            'count')  # count duplicates

        df['bw_amt'] = df.groupby(COLUMN_NAME)["bw_amt"].transform('sum')
        #df['ee_pmt_due'] = df.groupby(COLUMN_NAME)["ee_pmt_due"].transform('sum')
        #df['backwage_owed'] = df.groupby(COLUMN_NAME)['backwage_owed'].transform('sum')
        df['violtn_cnt'] = df.groupby(
            COLUMN_NAME)["violtn_cnt"].transform('sum')
        df['ee_violtd_cnt'] = df.groupby(
            COLUMN_NAME)["ee_violtd_cnt"].transform('sum')
        df['ee_pmt_recv'] = df.groupby(
            COLUMN_NAME)["ee_pmt_recv"].transform('sum')

        df = df.drop_duplicates(subset=[COLUMN_NAME], keep='first')

        #df[COLUMN_NAME] = df[COLUMN_NAME].str.title()
    return df


def GroupByMultpleCases(df, COLUMN_NAME):

    if COLUMN_NAME in df.columns and not df[COLUMN_NAME].isnull().all():

        df = df[df[COLUMN_NAME].notnull()]
        df = df[df[COLUMN_NAME] != 'nan']
        df = df[df[COLUMN_NAME] != 'NAN']
        df = df[df[COLUMN_NAME] != '']
        df = df[df[COLUMN_NAME] != 0]
        df = df[df[COLUMN_NAME] != False]

        df[COLUMN_NAME] = df[COLUMN_NAME].str.upper()

        df['records'] = 1
        df['records'] = df.groupby(COLUMN_NAME)[COLUMN_NAME].transform(
            'count')  # count duplicates

        df['bw_amt'] = df.groupby(COLUMN_NAME)["bw_amt"].transform('sum')
        #df['ee_pmt_due'] = df.groupby(COLUMN_NAME)["ee_pmt_due"].transform('sum')
        df['backwage_owed'] = df.groupby(
            COLUMN_NAME)['backwage_owed'].transform('sum')
        df['violtn_cnt'] = df.groupby(
            COLUMN_NAME)["violtn_cnt"].transform('sum')
        df['ee_violtd_cnt'] = df.groupby(
            COLUMN_NAME)["ee_violtd_cnt"].transform('sum')
        df['ee_pmt_recv'] = df.groupby(
            COLUMN_NAME)["ee_pmt_recv"].transform('sum')

        df = df.drop_duplicates(subset=[COLUMN_NAME], keep='first')
        df = df[df.records > 1]

        #df[COLUMN_NAME] = df[COLUMN_NAME].str.title()
    return df


def GroupByMultpleAgency(df):

    df['legal_nm'] = df['legal_nm'].astype(str).str.upper()
    df['juris_or_proj_nm'] = df['juris_or_proj_nm'].astype(str).str.upper()

    df = df[df['legal_nm'].notnull()]
    df = df[df['legal_nm'] != 'nan']
    df = df[df['legal_nm'] != 'NAN']
    df = df[df['legal_nm'] != '']

    df = df[df['juris_or_proj_nm'].notnull()]
    df = df[df['juris_or_proj_nm'] != 'nan']
    df = df[df['juris_or_proj_nm'] != 'NAN']
    df = df[df['juris_or_proj_nm'] != '']

    df['records'] = 1
    df['records'] = df.groupby(['legal_nm', 'juris_or_proj_nm'])[
        'legal_nm'].transform('count')
    df['bw_amt'] = df.groupby(['legal_nm', 'juris_or_proj_nm'])[
        "bw_amt"].transform('sum')
    df['violtn_cnt'] = df.groupby(['legal_nm', 'juris_or_proj_nm'])[
        "violtn_cnt"].transform('sum')
    df['ee_violtd_cnt'] = df.groupby(['legal_nm', 'juris_or_proj_nm'])[
        "ee_violtd_cnt"].transform('sum')
    df['ee_pmt_recv'] = df.groupby(['legal_nm', 'juris_or_proj_nm'])[
        "ee_pmt_recv"].transform('sum')

    df = df.drop_duplicates(
        subset=['legal_nm', 'juris_or_proj_nm'], keep='first')

    df['agencies'] = 0
    df['agencies'] = df.groupby('legal_nm')['legal_nm'].transform(
        'count')  # count duplicates across agencies
    df['records'] = df.groupby('legal_nm')['records'].transform('sum')
    df['bw_amt'] = df.groupby('legal_nm')["bw_amt"].transform('sum')
    df['violtn_cnt'] = df.groupby('legal_nm')["violtn_cnt"].transform('sum')
    df['ee_violtd_cnt'] = df.groupby(
        'legal_nm')["ee_violtd_cnt"].transform('sum')
    df['ee_pmt_recv'] = df.groupby('legal_nm')["ee_pmt_recv"].transform('sum')

    df['agency_names'] = np.nan
    if not df.empty:
        df['agency_names'] = df.groupby('legal_nm')['juris_or_proj_nm'].transform(
            ", ".join)  # count duplicates across agencies

    df = df.drop_duplicates(subset=['legal_nm'], keep='first')
    df = df[df.agencies > 1]

    #df['legal_nm'] = df['legal_nm'].str.title()
    df['juris_or_proj_nm'] = df['juris_or_proj_nm'].str.title()

    return df


def FilterForDate(df, YEAR_START, YEAR_END):
    df = df[
        ((pd.to_datetime(df['findings_start_date'], dayfirst=True) > YEAR_START) & (pd.to_datetime(df['findings_start_date'], dayfirst=True) < YEAR_END)) |
        (pd.isnull(df['findings_start_date']) & (pd.to_datetime(df['findings_end_date'], dayfirst=True) > YEAR_START) & (pd.to_datetime(df['findings_end_date'], dayfirst=True) < YEAR_END)) |
        (pd.isnull(df['findings_start_date'])
         & pd.isnull(df['findings_end_date']))
    ]
    return df


def Filter_for_Target_Industry(df, TARGET_INDUSTRY):
    appended_data = pd.DataFrame()
    # https://stackoverflow.com/questions/28669482/appending-pandas-dataframes-generated-in-a-for-loop
    for x in range(len(TARGET_INDUSTRY)):
        temp_term = TARGET_INDUSTRY[x][0]
        df_temp = df.loc[df['industry'].str.upper() == temp_term.upper()]
        appended_data = pd.concat([appended_data, df_temp])
    return appended_data


def Filter_for_Target_Organization(df, TARGET_ORGANIZATIONS):

    df_temp_0 = df.loc[df['legal_nm'].str.contains(
        '|'.join(TARGET_ORGANIZATIONS[1]))]
    df_temp_1 = df.loc[df['trade_nm'].str.contains(
        '|'.join(TARGET_ORGANIZATIONS[1]))]

    df_temp = pd.concat([df_temp_0, df_temp_1], ignore_index=True)
    return df_temp


def Filter_for_Zipcode(df, TARGET_ZIPCODES):
    if TARGET_ZIPCODES[0] != '00000': # faster run for "All_Zipcode" condition
        # Filter on region by zip code
        df = df.loc[df['zip_cd'].isin(TARGET_ZIPCODES)] #<-- DLSE bug here is not finding zipcodes
    return df



def RemoveCompletedCases(df):
    '''
    DLSE categories
    'Closed - Paid in Full (PIF)/Satisfied'
    'Full Satisfaction'
    'Open'
    'Open - Bankruptcy Stay'
    'Open - Payment Plan'
    'Partial Satisfaction'
    'Pending/Open'
    'Preliminary'
    'Vacated'
    '''

    if "Note" in df:
        df = df.loc[
            (df["Note"] != 'Closed - Paid in Full (PIF)/Satisfied') &
            (df["Note"] != 'Full Satisfaction') &
            (df["Note"] != 'Vacated')
        ]

    df['bw_amt'] = df['bw_amt'].replace('NaN', 0).astype(float)
    df['ee_pmt_recv'] = df['ee_pmt_recv'].replace('NaN', 0).astype(float)

    df['bw_amt'] = df['bw_amt'].fillna(0).astype(float)
    df['ee_pmt_recv'] = df['ee_pmt_recv'].fillna(0).astype(float)

    df = df[df['bw_amt'] != df['ee_pmt_recv']]

    bw = df['bw_amt'].tolist()
    pmt = df['ee_pmt_recv'].tolist()

    # df.index # -5 fixes an over count bug and is small eough that it wont introduce that much error into reports
    for i in range(0, len(bw)-5):
        if math.isclose(bw[i], pmt[i], rel_tol=0.10, abs_tol=0.0):  # works
            # if math.isclose(df['bw_amt'][i], df['ee_pmt_recv'][i], rel_tol=0.10, abs_tol=0.0): #error
            # if math.isclose(df.loc[i].at['bw_amt'], df.loc[i].at['ee_pmt_recv'], rel_tol=0.10, abs_tol=0.0): #error
            # if math.isclose(df.at[i,'bw_amt'], df.at[i,'ee_pmt_recv'], rel_tol=0.10, abs_tol=0.0): #error
            try:
                df.drop(df.index[i], inplace=True)
            except IndexError:
                dummy = ""

    return df


def InferPrevailingWageAndColumnFlag(df, prevailing_wage_terms):

    df['Prevailing'] = df.Prevailing.fillna("0")

    prevailing_wage_pattern = '|'.join(prevailing_wage_terms)
    found_prevailing = (
        ((df['violation_code'].astype(str).str.contains(prevailing_wage_pattern, na=False, flags=re.IGNORECASE, regex=True))) |
        ((df['violation'].astype(str).str.contains(prevailing_wage_pattern, na=False, flags=re.IGNORECASE, regex=True))) |
        ((df['Note'].astype(str).str.contains(prevailing_wage_pattern, na=False, flags=re.IGNORECASE, regex=True))) |
        ((df['juris_or_proj_nm'].astype(str).str.contains(
            prevailing_wage_pattern, na=False, flags=re.IGNORECASE, regex=True)))
    )
    df['Prevailing'] = pd.to_numeric(df['Prevailing'], errors='coerce')
    df.loc[found_prevailing, 'Prevailing'] = 1

    return df


def InferAgencyFromCaseIDAndLabel(df, LABEL_COLUMN):

    if LABEL_COLUMN in df.columns:
        # find case IDs with a hyphen
        foundAgencybyCaseID_1 = pd.isna(df[LABEL_COLUMN])
        # df[LABEL_COLUMN] = df[LABEL_COLUMN].fillna(foundAgencybyCaseID_1.replace( (True,False), (df['case_id'].astype(str).apply(lambda st: st[:st.find("-")]), df[LABEL_COLUMN]) ) ) #https://stackoverflow.com/questions/51660357/extract-substring-between-two-characters-in-pandas
        # https://stackoverflow.com/questions/51660357/extract-substring-between-two-characters-in-pandas
        df.loc[foundAgencybyCaseID_1, LABEL_COLUMN] = df['case_id'].astype(
            str).apply(lambda st: st[:st.find("-")])

        # cind case ID when no hyphen
        foundAgencybyCaseID_2 = pd.isna(df[LABEL_COLUMN])
        #df[LABEL_COLUMN] = df[LABEL_COLUMN].fillna(foundAgencybyCaseID_2.replace( (True,False), (df['case_id'].astype(str).str[:3], df[LABEL_COLUMN]) ) )
        df.loc[foundAgencybyCaseID_2, LABEL_COLUMN] = df['case_id'].astype(
            str).str[:3]

        # hardcode for DLSE nomemclature with a note * for assumed
        DLSE_terms = ['01', '04', '05', '06', '07', '08', '09', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '23', '32', '35', 'WC']
        pattern_DLSE = '|'.join(DLSE_terms)
        found_DLSE = (df[LABEL_COLUMN].str.contains(pattern_DLSE))
        #df[LABEL_COLUMN] = found_DLSE.replace( (True,False), ("DLSE", df[LABEL_COLUMN] ) )
        df.loc[found_DLSE, LABEL_COLUMN] = "DLSE"

    return df


def InferSignatoriesFromNameAndFlag(df, SIGNATORY_INDUSTRY):

    if 'legal_nm' and 'trade_nm' in df.columns:
        if "Signatory" not in df.columns:
            df["Signatory"] = 0

        

        for x in range(1, len(SIGNATORY_INDUSTRY)):
            PATTERN_EXCLUDE = EXCLUSION_LIST_GENERATOR(
                SIGNATORY_INDUSTRY[x][1])
            PATTERN_IND = '|'.join(SIGNATORY_INDUSTRY[x][1])

            foundIt_sig = (
                (
                    df['legal_nm'].str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                    ~df['legal_nm'].str.contains(PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True)) |
                (
                    df['trade_nm'].str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                    ~df['trade_nm'].str.contains(PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True))
            )
            df.loc[foundIt_sig, "Signatory"] = 1

    return df


def InferSignatoriesFromNameAndAddressFlag(df, signatory_name_list, signatory_address_list):

    if "Signatory" not in df.columns:
        df["Signatory"] = 0

    pattern_signatory_name = '|'.join(signatory_name_list)
    pattern_signatory_add = '|'.join(signatory_address_list)

    foundIt_sig = (
        ((df['legal_nm'].str.contains(pattern_signatory_name, na=False, flags=re.IGNORECASE, regex=True)) &
            (df['street_addr'].str.contains(
                pattern_signatory_add, na=False, flags=re.IGNORECASE, regex=True))
         ) |
        ((df['trade_nm'].str.contains(pattern_signatory_name, na=False, flags=re.IGNORECASE, regex=True)) &
         (df['street_addr'].str.contains(
             pattern_signatory_add, na=False, flags=re.IGNORECASE, regex=True))
         )
    )
    df.loc[foundIt_sig,"Signatory"] = 1

    return df


def InferSignatoriesFromAddressAndFlag(df, signatory_address_list):

    if "Signatory" not in df.columns:
        df["Signatory"] = 0

    pattern_signatory = '|'.join(signatory_address_list)
    foundIt_sig = (
        (df['street_addr'].str.contains(
            pattern_signatory, na=False, flags=re.IGNORECASE, regex=True))
        #(df['street_addr'].str.match(pattern_signatory, na=False, flags=re.IGNORECASE) )
    )
    df.loc[foundIt_sig, "Signatory"] = 1

    return df


def Infer_Industry(df, INFER, TARGET_INDUSTRY):
    if 'industry' not in df.columns:
        df['industry'] = "" 
    if 'trade2' not in df.columns:
        df['trade2'] = "" #inferred industry

    if not df.empty:  # filter out industry rows
        # exclude cell 0 that contains an industry label cell
        for x in range(1, len(TARGET_INDUSTRY)):
            # add a levinstein distance with distance of two and match and correct: debug 10/30/2020
            PATTERN_IND = '|'.join(TARGET_INDUSTRY[x])
            PATTERN_EXCLUDE = EXCLUSION_LIST_GENERATOR(TARGET_INDUSTRY[x])

            if INFER == 1 and ('legal_nm' and 'trade_nm' in df.columns): #uses legal and trade names to infer industry
                foundIt_ind1 = (

                    (
                        df['legal_nm'].astype(str).str.contains(
                            PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True)
                        &
                        ~df['legal_nm'].astype(str).str.contains(PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True))

                    |

                    (
                        df['trade_nm'].astype(str).str.contains(
                            PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True)
                        &
                        ~df['trade_nm'].astype(str).str.contains(PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True))

                )

                df.loc[foundIt_ind1, 'trade2'] = TARGET_INDUSTRY[x][0]

            # uses the exisiting NAICS coding
            foundIt_ind2 = (
                df['naic_cd'].astype(str).str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                ~df['naic_cd'].astype(str).str.contains(
                    PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True)
            )
            df.loc[foundIt_ind2, 'industry'] = TARGET_INDUSTRY[x][0]

            foundIt_ind3 = (  # uses the exisiting NAICS descriptions to fill gaps in the data
                (df['industry'] == "") &
                df['naics_desc.'].astype(str).str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                ~df['naics_desc.'].astype(str).str.contains(
                    PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True)
            )
            df.loc[foundIt_ind3, 'industry'] = TARGET_INDUSTRY[x][0]

        # uses the existing NAICS coding and fill balnks with infered

        df['industry'] = df.apply(
            lambda row:
            row['trade2'] if (row['industry'] == '') and (row['trade2'] != '') #take guessed industry if NAICS is missing
            else row['industry'], axis=1 
        )

        # if all fails, assign 'Undefined' so it gets counted
        df['industry'] = df['industry'].replace(
            r'^\s*$', 'Undefined', regex=True)
        df['industry'] = df['industry'].fillna('Undefined')
        df['industry'] = df['industry'].replace(np.nan, 'Undefined')

        #'trade2' is not used outside this function other than in the print to csv 

    return df


def InferSignatoryIndustryAndLabel(df, SIGNATORY_INDUSTRY):
    if 'signatory_industry' not in df.columns:
        df['signatory_industry'] = ""

    if not df.empty and 'legal_nm' and 'trade_nm' in df.columns:  # filter out industry rows
        for x in range(1, len(SIGNATORY_INDUSTRY)):

            PATTERN_EXCLUDE = EXCLUSION_LIST_GENERATOR(
                SIGNATORY_INDUSTRY[x][1])
            PATTERN_IND = '|'.join(SIGNATORY_INDUSTRY[x][1])

            foundIt_ind1 = (
                (
                    df['legal_nm'].astype(str).str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                    ~df['legal_nm'].astype(str).str.contains(
                        PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True)
                ) |
                (
                    df['trade_nm'].astype(str).str.contains(PATTERN_IND, na=False, flags=re.IGNORECASE, regex=True) &
                    ~df['trade_nm'].astype(str).str.contains(
                        PATTERN_EXCLUDE, na=False, flags=re.IGNORECASE, regex=True)
                ) |
                (df['Signatory'] == 1) &
                (df['industry'] == SIGNATORY_INDUSTRY[x][0][0])
            )
            df.loc[foundIt_ind1, 'signatory_industry'] = SIGNATORY_INDUSTRY[x][0][0]

        # if all fails, assign 'other' so it gets counted
        df['signatory_industry'] = df['signatory_industry'].replace(
            r'^\s*$', 'Undefined', regex=True)
        df['signatory_industry'] = df['signatory_industry'].fillna('Undefined')
        df['signatory_industry'] = df['signatory_industry'].replace(
            np.nan, 'Undefined')

    return df


def InferZipcodeFromCityName(df, cityDict):

    if 'cty_nm' in df.columns: #if no city column then skip

        #check if column is in df
        if 'zip_cd' not in df.columns:
            df['zip_cd'] = '99999'
        df.zip_cd = df.zip_cd.astype(str)

        for city in cityDict:
            #upper_region = city.upper()
            #PATTERN_CITY = '|'.join(upper_region)

            zipcode_is_empty = (
                ((df['zip_cd'] == '0' ) | (df['zip_cd'] == '99999' ) |(df['zip_cd'] == 0 ) | pd.isna(df['zip_cd']) | 
                    (df['zip_cd'] == False) | (df['zip_cd'] == "" ) )  
            )

            test = cityDict[city][0]
            foundZipbyCity = (
                ((df['cty_nm'].astype(str).str.contains(test, na=False, 
                    case=False, flags=re.IGNORECASE)))  # flags=re.IGNORECASE
                #((df['cty_nm'].astype(str).str.contains(PATTERN_CITY, na=False, 
                #    case=False, flags=re.IGNORECASE)))  # flags=re.IGNORECASE
            )

            tempA = cityDict[city][len(cityDict[city]) - 1] #take last zipcode
            tempB = generate_generic_zipcode_for_city(tempA)
            df.loc[zipcode_is_empty * foundZipbyCity, "zip_cd"] = tempB
    
    return df

def FillBlankZipcodes (df):

    zipcode_is_empty = (
        ((df['zip_cd'] == '0' ) | (df['zip_cd'] == 0 ) | pd.isna(df['zip_cd']) | 
        (df['zip_cd'] == False) | (df['zip_cd'] == "" ) )  
    )
    
    df.loc[zipcode_is_empty, "zip_cd"] = "99999"

    return df


def InferZipcodeFromCompanyName(df, cityDict):
    # fill nan zip code by assumed zip by city name in trade name; ex. "Cupertino Elec."
    if 'cty_nm' not in df.columns:
        df['cty_nm'] = ''
    if 'trade_nm' not in df.columns:
        df['trade_nm'] = ""
    if 'legal_nm' not in df.columns:
        df['legal_nm'] = ""
    if 'zip_cd' not in df.columns:
        df['zip_cd'] = '99999'

    for city in cityDict:
        #PATTERN_CITY = '|'.join(cityDict[city][0])

        zipcode_is_empty = (
            (pd.isna(df['cty_nm'])) &
            ((df['zip_cd'] == '0') | (df['zip_cd'] == '99999') |(df['zip_cd'] == "") | pd.isna(df['zip_cd']) | (df['zip_cd'] == 0)) #10/27/2022 changed False to 0
        )
        
        test = cityDict[city][0]

        foundZipbyCompany2 = (
            ((df['trade_nm'].astype(str).str.contains(test, na=False, case=False, flags=re.IGNORECASE))) |
            ((df['legal_nm'].astype(str).str.contains(
                test, na=False, case=False, flags=re.IGNORECASE)))
            #((df['trade_nm'].astype(str).str.contains(PATTERN_CITY, na=False, case=False, flags=re.IGNORECASE))) |
            #((df['legal_nm'].astype(str).str.contains(
            #    PATTERN_CITY, na=False, case=False, flags=re.IGNORECASE)))
        )

        tempA = cityDict[city][len(cityDict[city]) - 1] #take last zipcode
        tempB = generate_generic_zipcode_for_city(tempA)
        df.loc[zipcode_is_empty * foundZipbyCompany2,'zip_cd'] = tempB

    return df


def InferZipcodeFromJurisdictionName(df, cityDict):

    if 'cty_nm' not in df.columns:
        df['cty_nm'] = ''
    if 'juris_or_proj_nm' not in df.columns:
        df['juris_or_proj_nm'] = ""
    if 'Jurisdiction_region_or_General_Contractor' not in df.columns:
        df['Jurisdiction_region_or_General_Contractor'] = ""
    if 'zip_cd' not in df.columns:
        df['zip_cd'] = '99999'

    df.juris_or_proj_nm = df.juris_or_proj_nm.astype(str)
    df.Jurisdiction_region_or_General_Contractor = df.Jurisdiction_region_or_General_Contractor.astype(
        str)

    for city in cityDict:

        #PATTERN_CITY = '|'.join(cityDict[city][0])

        zipcode_is_empty = (
            (pd.isna(df['cty_nm'])) &
            ((df['zip_cd'] == '0') | (df['zip_cd'] == '99999') | (df['zip_cd'] == "") | (df['zip_cd'] == 0)) #10/27/2022 changed False to 0
        )

        test = cityDict[city][0]

        foundZipbyCompany2 = (
            (df['juris_or_proj_nm'].str.contains(test, na=False, flags=re.IGNORECASE, regex=True)) |
            (df['Jurisdiction_region_or_General_Contractor'].str.contains(
                    test, na=False, flags=re.IGNORECASE, regex=True))
            #(df['juris_or_proj_nm'].str.contains(PATTERN_CITY, na=False, flags=re.IGNORECASE, regex=True)) |
            #(df['Jurisdiction_region_or_General_Contractor'].str.contains(
            #        PATTERN_CITY, na=False, flags=re.IGNORECASE, regex=True))
        )

        tempA = cityDict[city][len(cityDict[city]) - 1] #take last zipcode
        tempB = generate_generic_zipcode_for_city(tempA)
        df.loc[zipcode_is_empty * foundZipbyCompany2, 'zip_cd'] = tempB

    return df


def EXCLUSION_LIST_GENERATOR(SIGNATORY_INDUSTRY):
    target = pd.Series(SIGNATORY_INDUSTRY)
    # https://stackoverflow.com/questions/28679930/how-to-drop-rows-from-pandas-data-frame-that-contains-a-particular-string-in-a-p
    target = target[target.str.contains("!") == True]
    target = target.str.replace('[\!]', '', regex=True)
    if len(target) > 0:
        PATTERN_EXCLUDE = '|'.join(target)
    else:
        PATTERN_EXCLUDE = "999999"
    return PATTERN_EXCLUDE


def infer_WHD_prevailing_wage_violation(df):
    #dbra_cl_violtn_cnt, dbra_bw_atp_amt, dbra_ee_atp_cnt
    if "dbra_cl_violtn_cnt" in df.columns:
        df.loc[df["dbra_cl_violtn_cnt"] > 0, "violation_code"] = "DBRA"
    # if "dbra_bw_atp_amt" in df.columns:
        #df.loc[df["dbra_bw_atp_amt"] > 0, "violation_code"] = "DBRA"
    # if "dbra_ee_atp_cnt" in df.columns:
        #df.loc[df["dbra_ee_atp_cnt"] > 0, "violation_code"] = "DBRA"

    return df


def lookuplist(trade, list_x, col):
    import os

    trigger = True
    if pd.isna(trade):
        trade = ""
    for x in list_x:
        if x[0].upper() in trade.upper():
            value_out = + x[col]  # += to capture cases with multiple scenarios
            trigger = False
            # break
    if trigger:  # if true then no matching violations
        Other = ['Generic', 26.30, 33.49, 50.24, 50.24]
        # if value not found then return 0 <-- maybe this should be like check or add to a lrearning file
        value_out = Other[col]

        rel_path1 = 'report_output_/'
        # <-- dir the script is in (import os) plus up one
        script_dir1 = os.path.dirname(os.path.dirname(__file__))
        abs_path1 = os.path.join(script_dir1, rel_path1)
        if not os.path.exists(abs_path1):  # create folder if necessary
            os.makedirs(abs_path1)

        log_name = 'log_'
        out_log_report = 'new_trade_names_'
        log_type = '.txt'
        log_name_trades = os.path.join(abs_path1, log_name.replace(
            ' ', '_')+out_log_report + log_type)  # <-- absolute dir and file name

        # append/create log file with new trade names
        tradenames = open(log_name_trades, 'a')

        tradenames.write(trade)
        tradenames.write("\n")
        tradenames.close()
    return value_out


def wages_owed(df):
    
    # backwage estimate
    # df['bw_amt'] = df['bw_amt'].fillna(estimated_bw_plug) #assume mean or $1000 minimum to estimate in zero situation
    # df['bw_amt'] = np.where(df['bw_amt'] == "", estimated_bw_plug, df['bw_amt']) # catch if na misses
    # df['bw_amt'] = np.where(df['bw_amt'] == 0, estimated_bw_plug, df['bw_amt']) # catch if na misses
    # df['bw_amt'] = np.where(df['bw_amt'] == False, estimated_bw_plug, df['bw_amt']) # catch if na misses
    # total_bw_atp = df['bw_amt'].sum() #overwrite

    df['wages_owed'] = (df['bw_amt'] - df["ee_pmt_recv"])
    df['wages_owed'] = np.where((df['wages_owed'] < 0), 0, df['wages_owed'])  # overwrite

    return df


def backwages_owed(df):

    #estimated_bw_plug = max(total_bw_atp//total_ee_violtd,1000)

    # montetary penalty only if backwage is zero -- often penalty is in the backwage column
    # df['cmp_assd_cnt'] = np.where(df['bw_amt'] == "", estimated_bw_plug * 0.25, df['cmp_assd_cnt'])
    # df['cmp_assd_cnt'] = np.where(df['bw_amt'] == 0, estimated_bw_plug * 0.25, df['cmp_assd_cnt'])
    # df['cmp_assd_cnt'] = np.where(df['bw_amt'] == False, estimated_bw_plug * 0.25, df['cmp_assd_cnt'])
    if 'cmp_assd_cnt' not in df.columns: df['cmp_assd_cnt'] = 0

    df['backwage_owed'] = df['wages_owed'] + \
        df['cmp_assd_cnt'] + df['interest_owed'] #fill backwages as sum of wages, penalty, and interest

    # add ee_pmt_due check if equal ?
    if 'Paid' in df.columns:
        # zero out if documented as paid
        df['backwage_owed'] = np.where(
            df['Paid'] == 'Y', 0, df['backwage_owed'])
        # zero out if documented as paid
        df['cmp_assd_cnt'] = np.where(df['Paid'] == 'Y', 0, df['cmp_assd_cnt'])
        # zero out if documented as paid
        df['interest_owed'] = np.where(
            df['Paid'] == 'Y', 0, df['interest_owed'])

    # at some point, save this file for quicker reports and only run up to here when a new dataset is introduced
    return df


def calculate_interest_owed(df):
    if 'findings_start_date' and 'findings_end_date' in df.columns:
        df['wages_owed'] = np.where(df['wages_owed'] < 0, 0, df['wages_owed'])

        df['findings_start_date'] = pd.to_datetime(
            df['findings_start_date'], errors='coerce')
        # crashed here 2/5/2022 "Out of bounds nanosecond timestamp: 816-09-12 00:00:00"
        df['findings_end_date'] = pd.to_datetime(
            df['findings_end_date'], errors='coerce')
        df['Calculate_start_date'] = df['findings_start_date'].fillna(
            df['findings_end_date'])
        df['Days_Unpaid'] = pd.to_datetime(
            'today') - df['Calculate_start_date']
        # df['Days_Unpaid'] = np.where(df['Days_Unpaid'] < pd.Timedelta(0,errors='coerce'), (pd.Timedelta(0, errors='coerce')), df['Days_Unpaid'] )

        df['Years_Unpaid'] = df['Days_Unpaid'].dt.days.div(365)
        r = 10
        n = 365
        df['Interest_Accrued'] = (
            df['wages_owed'] * (((1 + ((r/100.0)/n)) ** (n*df['Years_Unpaid'])))) - df['wages_owed']
        df['Interest_Accrued'] = df['Interest_Accrued'].fillna(
            df['Interest_Accrued'])
        if 'Interest_Balance_Due' not in df.columns: df['Interest_Balance_Due'] = 0
        df['Interest_Balance_Due'] = np.where(
            df['Interest_Balance_Due'] == "", df['Interest_Accrued'], df['Interest_Balance_Due'])
        # df['Interest_Balance_Due'] = np.where(df['Interest_Balance_Due'] == 0, df['Interest_Accrued'], df['Interest_Balance_Due'] ) #<--careful this does not overwite fully paid cases
        df['Interest_Balance_Due'] = np.where(
            df['Interest_Balance_Due'] == False, df['Interest_Accrued'], df['Interest_Balance_Due'])
        if 'Interest_Payments_Recd' not in df.columns: df['Interest_Payments_Recd'] = 0
        df['interest_owed'] = (
            df['Interest_Balance_Due'] - df["Interest_Payments_Recd"])
        df['interest_owed'] = np.where(
            df['interest_owed'] < 0, 0, df['interest_owed'])
        #total_int_bal = df['interest_owed'].sum()
    return df


def infer_wage_penalty(df):

    mean_backwage = df['bw_amt'].mean()
    #mean_backwage = df[df['bw_amt']!=0].mean()

    # lookup term / (1) monetary penalty
    A = ["ACCESS TO PAYROLL", 750]  # $750
    B = ["L.C. 1021", 200]  # $200 per day (plug one day)
    C = ["L.C. 11942", mean_backwage]  # less than minimum wage
    D = ["L.C. 1197", mean_backwage]
    E = ["L.C. 1299", 500]
    F = ["L.C. 1391", 500]
    # improper deduction 30 days of wage (plug $15 x 8 x 30)
    G = ["L.C. 203", 3600]
    H = ["L.C. 2054", mean_backwage]
    I = ["L.C. 2060", mean_backwage]
    J = ["L.C. 223", mean_backwage]  # less than contract (prevailing)
    K = ["L.C. 226(a)", 250]  # paycheck itemized plus $250
    K1 = ["LCS 226(a)", 250]  # paycheck itemized plus $250
    L = ["L.C. 2267", 150]  # Meal periods plug ($150)
    M = ["L.C. 2675(a)", 250]
    # workmans compensation $500 to State Director for work comp fund
    N = ["L.C. 3700", 500]
    O = ["L.C. 510", 200]  # 8 hour workday $50 per pay period plug $200
    P = ["LIQUIDATED DAMAGES", mean_backwage]  # equal to lost wage plug mean
    Q = ["MEAL PERIOD PREMIUM WAGES", 75]  # 1 hour of pay (plug $15 * 5 days)
    R = ["MINIMUM WAGES", 50]  # plug $50
    S = ["Misclassification", mean_backwage]  # plug mean wage
    T = ["Overtime", mean_backwage]  # plus mean wage
    U = ["PAID SICK LEAVE", 200]  # $50 per day plug $200
    # aka PAGA $100 per pay period for 1 year plug $1,200
    V = ["PIECE RATE WAGES", 1200]
    W = ["PRODUCTION BONUS", mean_backwage]  # plug mean wage
    X = ["REGULAR WAGES", mean_backwage]  # plug mean wage
    # daily wage for 30 days plug $1,000 of (15 * 8 * 30)
    Y = ["REPORTING TIME PAY", 1000]
    Z = ["REST PERIOD PREMIUM WAGES", 2000]  # plug $2,000
    AA = ["VACATION WAGES", 2000]  # plug $2,000
    AB = ["SPLIT SHIFT PREMIUM WAGES", 500]  # $500
    AC = ["UNLAWFUL DEDUCTIONS", 2000]  # plug $2000
    AD = ["UNLAWFUL TIP DEDUCTIONS", 1000]  # $1,000
    AE = ["UNREIMBURSED BUSINESS EXPENSES", 2500]  # plug $2,500
    AF = ["WAITING TIME PENALTIES", 2500]  # plug $2,500
    AG = ["LC 1771", 125]  # 5 x $25
    AH = ["L.C. 1771", 125]  # 5 x $25
    AI = ["L.C. 1774", 125]  # 5 x $25
    AJ = ["LC 1774", 125]  # 5 x $25
    AK = ["", mean_backwage]  # <blank> plug mean wage
    # generic monetary penalty is 25% of backwages

    penalties = [['MONETARY_PENALTY'], A, B, C, D, E, F, G, H, I, J, K, K1, L, M, N,
                 O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF, AG, AH, AI, AJ, AK]

    if 'assumed_backwage' not in df.columns: df['assumed_backwage'] = 0
    df['assumed_backwage'] = np.where(((df['bw_amt'] == 0) | (df['bw_amt'] == "") | (
        df['bw_amt'] == 0) | (df['bw_amt'] == False)), 1, df['assumed_backwage'])

    if 'violation' in df.columns:
        if 'bw_amt' not in df.columns: df['bw_amt'] = 0 #test to debug
        if 'violation' not in df.columns: df['violation'] = "" #test to debug

        df['bw_amt'] = df.apply(
            lambda x: lookuplist(x['violation'], penalties, 1)
            if (x['assumed_backwage'] == 1)
            else x['bw_amt'], axis=1)

    return df


def compute_and_add_violation_count_assumptions(df):
    if not df.empty:
        # employee violated
        # DLSE cases are for one employee -- introduces an error when the dataset is violation records--need to remove duplicates
        df['ee_violtd_cnt'] = df['ee_violtd_cnt'].fillna(1)
        df['ee_violtd_cnt'] = np.where(
            df['ee_violtd_cnt'] == "", 1, df['ee_violtd_cnt'])  # catch if na misses
        df['ee_violtd_cnt'] = np.where(
            df['ee_violtd_cnt'] == 0, 1, df['ee_violtd_cnt'])  # catch if na misses
        df['ee_violtd_cnt'] = np.where(
            df['ee_violtd_cnt'] == False, 1, df['ee_violtd_cnt'])  # catch if na misses
        total_ee_violtd = df['ee_violtd_cnt'].sum()  # overwrite

        # by issue count
        if 'violation' in df.columns:
            df['violtn_cnt'] = df['violtn_cnt'].fillna(
                df['violation'].str.count("Issue"))  # assume mean
            df['violtn_cnt'] = np.where(df['violtn_cnt'] == "", df['violation'].str.count(
                "Issue"), df['violtn_cnt'])  # catch if na misses
            df['violtn_cnt'] = np.where(
                df['violtn_cnt'] == 0, df['violation'].str.count("Issue"), df['violtn_cnt'])
            df['violtn_cnt'] = np.where(
                df['violtn_cnt'] == False, df['violation'].str.count("Issue"), df['violtn_cnt'])
            total_case_violtn = df['violtn_cnt'].sum()  # overwrite

        # violations
        # safe assumption: violation count is always more then the number of employees
        total_case_violtn = max(
            df['violtn_cnt'].sum(), df['ee_violtd_cnt'].sum())

        if total_ee_violtd != 0:  # lock for divide by zero error
            # violation estimate by mean
            estimated_violations_per_emp = max(
                total_case_violtn//total_ee_violtd, 1)
            df['violtn_cnt'] = df['violtn_cnt'].fillna(
                estimated_violations_per_emp)  # assume mean
            df['violtn_cnt'] = np.where(
                df['violtn_cnt'] == "", (estimated_violations_per_emp), df['violtn_cnt'])  # catch if na misses
            df['violtn_cnt'] = np.where(
                df['violtn_cnt'] == 0, (estimated_violations_per_emp), df['violtn_cnt'])
            df['violtn_cnt'] = np.where(
                df['violtn_cnt'] == False, (estimated_violations_per_emp), df['violtn_cnt'])

    return df


def MoveCompanyLiabilityTermsToLiabilityTypeColumn(df):

    df['Liabilitytype'] = ""  # create new column and fill with str

    liability_terms0 = ['(a California)', '(a Californi)', '(a Californ)']
    pattern_liability0 = '|'.join(liability_terms0)
    if 'legal_nm' and 'trade_nm' in df.columns:
        foundIt0 = (df['legal_nm'].str.contains(pattern_liability0, na=False, flags=re.IGNORECASE, regex=True) |
                    df['trade_nm'].str.contains(pattern_liability0, na=False, flags=re.IGNORECASE, regex=True))

        df.loc[foundIt0, 'Liabilitytype'] = 'California'

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a California', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Californi', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a California', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Californi', '', regex=True, case=False)

        liability_terms1 = ['(a Delaware)']
        pattern_liability1 = '|'.join(liability_terms1)
        foundIt1 = (
            df['legal_nm'].str.contains(pattern_liability1, na=False, flags=re.IGNORECASE, regex=True) |
            df['trade_nm'].str.contains(
                pattern_liability1, na=False, flags=re.IGNORECASE, regex=True)
        )
        df.loc[foundIt1, 'Liabilitytype'] = 'Delaware'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Delaware', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Delaware', '', regex=True, case=False)

        liability_terms2 = ['(a Nevada)']
        pattern_liability2 = '|'.join(liability_terms2)
        foundIt2 = (df['legal_nm'].str.contains(pattern_liability2, na=False, flags=re.IGNORECASE, regex=True) |
                    df['trade_nm'].str.contains(pattern_liability2, na=False, flags=re.IGNORECASE, regex=True))

        df.loc[foundIt2, 'Liabilitytype'] = 'Delaware'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Nevada', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Nevada', '', regex=True, case=False)

        liability_terms3 = ['(a Nebraska)']
        pattern_liability3 = '|'.join(liability_terms3)
        foundIt3 = (df['legal_nm'].str.contains(pattern_liability3, na=False, flags=re.IGNORECASE, regex=True) |
                    df['trade_nm'].str.contains(pattern_liability3, na=False, flags=re.IGNORECASE, regex=True))

        df.loc[foundIt3, 'Liabilitytype'] = 'Nebraska'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Nebraska', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Nebraska', '', regex=True, case=False)

        liability_terms4 = ['(a foreign)']
        pattern_liability4 = '|'.join(liability_terms4)
        foundIt4 = (df['legal_nm'].str.contains(pattern_liability4, na=False, flags=re.IGNORECASE, regex=True) |
                    df['trade_nm'].str.contains(pattern_liability4, na=False, flags=re.IGNORECASE, regex=True))

        df.loc[foundIt4, 'Liabilitytype'] = 'Foreign'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Foreign', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Foreign', '', regex=True, case=False)

        liability_terms5 = ['(Which Will Be Doing Business In California)',
                            '(Which Will Be Doing Business In California As)']
        pattern_liability5 = '|'.join(liability_terms5)
        foundIt5 = (df['legal_nm'].str.contains(pattern_liability5, na=False, flags=re.IGNORECASE, regex=True) |
                    df['trade_nm'].str.contains(pattern_liability5, na=False, flags=re.IGNORECASE, regex=True))

        df.loc[foundIt5, 'Liabilitytype'] = 'California'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Foreign', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Foreign', '', regex=True, case=False)

    return df


def MoveBusinessTypeToBusinessTypeColumn(df):

    individual_terms = ['an individual', 'individual ']
    pattern_individual = '|'.join(individual_terms)
    if 'legal_nm' and 'trade_nm' in df.columns:
        foundIt = (df['legal_nm'].str.contains(pattern_individual, na=False, flags=re.IGNORECASE, regex=True) |
                   df['trade_nm'].str.contains(pattern_individual, na=False, flags=re.IGNORECASE, regex=True))

        # df['Businesstype'] = foundIt.replace((True,False), ('Individual',df['Businesstype']), regex=True) #fill column 'industry'
        df.loc[foundIt, 'Businesstype'] = 'Individual'
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'an individual', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'an individual', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'individual ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'individual ', '', regex=True, case=False)
    return df


def MoveLimitedLiabilityBusinessTypeToBusinessTypeColumn(df):
    company_terms = ['LLC', 'L.L.C.', 'company', 'Comapany', 'a limited liability company', 'a limited liability', 'Co.',
                     'Limited Liability', 'Limited Liability Comapany', 'Limited Liability Company']
    pattern_company = '|'.join(company_terms)

    if 'legal_nm' and 'trade_nm' in df.columns:
        foundIt = (df['legal_nm'].str.contains(pattern_company, na=False, flags=re.IGNORECASE, regex=True) |
                   df['trade_nm'].str.contains(pattern_company, na=False, flags=re.IGNORECASE, regex=True))

        # df['Businesstype'] = foundIt.replace((True,False), ('Company',df['Businesstype']), regex=True) #fill column 'industry'
        df.loc[foundIt, 'Businesstype'] = 'Company'

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            r'\bLLC$', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            r'\bLLC$', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            r'\bL.L.C.$', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            r'\bL.L.C.$', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'L.L.C., ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'L.L.C., ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'LLC, ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'LLC, ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'L.L.C. ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'L.L.C. ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull(
        )]['legal_nm'].str.replace('LLC ', '', regex=False, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull(
        )]['trade_nm'].str.replace('LLC ', '', regex=False, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'company', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'company', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Company', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Company', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'comapany', '', regex=True, case=False)  # common typo
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'comapany', '', regex=True, case=False)  # common typo
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Comapany', '', regex=True, case=False)  # common typo
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Comapany', '', regex=True, case=False)  # common typo

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a limited liability', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a limited liability', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a Limited Liability', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a Limited Liability', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'limited liability', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'limited liability', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Limited Liability', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Limited Liability', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull(
        )]['legal_nm'].str.replace(r'\bCo$', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull(
        )]['trade_nm'].str.replace(r'\bCo$', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull(
        )]['legal_nm'].str.replace('Co. ', '', regex=False, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull(
        )]['trade_nm'].str.replace('Co. ', '', regex=False, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull(
        )]['legal_nm'].str.replace('Co ', '', regex=False, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull(
        )]['trade_nm'].str.replace('Co ', '', regex=False, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull(
        )]['legal_nm'].str.replace('CO ', '', regex=False, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull(
        )]['trade_nm'].str.replace('CO ', '', regex=False, case=False)
    return df


def MovePartnershipBusinessTypeToBusinessTypeColumn(df):
    partnership_terms = ['as partners', 'LLP', 'individually & jointly', 'both individually & as partners', 'individually and as partners',
                         'both individually and as partners', 'both individually and jointly liable']
    pattern_partner = '|'.join(partnership_terms)

    if 'legal_nm' and 'trade_nm' in df.columns:
        foundIt = (df['legal_nm'].str.contains(pattern_partner, na=False, flags=re.IGNORECASE, regex=True) |
                   df['trade_nm'].str.contains(pattern_partner, na=False, flags=re.IGNORECASE, regex=True))

        # df['Businesstype'] = foundIt.replace((True,False), ('Partnership',df['Businesstype']), regex=True) #fill column 'industry'
        df.loc[foundIt, 'Businesstype'] = 'Partnership'

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both jointly and severally as employers', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both jointly and severally as employers', '',  regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'jointly and severally as employers', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'jointly and severally as employers', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each individually and as partners', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each individually and as partners', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both individually and as partners', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both individually and as partners', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'individually and as partners', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'individually and as partners', '', regex=True, case=False)

        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each individually and jointly liable', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each individually and jointly liable', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both individually and jointly liable', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both individually and jointly liable', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'individually and jointly liable', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'individually and jointly liable', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each individually and jointly', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each individually and jointly', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both individually and jointly', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both individually and jointly', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'individually and jointly', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'individually and jointly', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each jointly and severally', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each jointly and severally', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both jointly and severally', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both jointly and severally', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'jointly and severally', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'jointly and severally', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each severally and as joint employers', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each severally and as joint employers', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each severally and as joint employ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each severally and as joint employ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'both severally and as joint employers', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'both severally and as joint employers', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'severally and as joint employers', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'severally and as joint employers', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each severally and as joint', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each severally and as joint', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'severally and as joint', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'severally and as joint', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a general partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a general partnership', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'general partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'general partnership', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a limited partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a limited partnership', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'limited partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'limited partnership', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a partnership', '',  regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'partnership', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'partnership', '',  regex=True, case=False)

        # last ditch cleanup
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'each severally and as', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'each severally and as', '',  regex=True, case=False)

    return df


def MoveCorportationBusinessTypeToBusinessTypeColumn(df):
    corporation_terms = ['inc.', 'corporation', 'corp.', 'corp', 'inc', 'a corporation', 'Incorporated', 'non-profit corporation',
                         'nonprofit', 'non-profit']
    pattern_corp = '|'.join(corporation_terms)

    if 'legal_nm' and 'trade_nm' in df.columns:
        foundIt = (df['legal_nm'].str.contains(pattern_corp, na=False, flags=re.IGNORECASE, regex=True) |
                   df['trade_nm'].str.contains(pattern_corp, na=False,  flags=re.IGNORECASE, regex=True))

        # df['Businesstype'] = foundIt.replace((True,False), ('Corporation', df['Businesstype']), regex=True) #fill column business type
        df.loc[foundIt, 'Businesstype'] = 'Corporation'

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'a corporation', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'a corporation', '', regex=True, case=False)
        #df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace('corporation', '', regex=True, case=False)
        #df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace('corporation', '', regex=True, case=False)

        #df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace('CORPORATION', '', regex=True, case=False)

        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Corporation', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Corporation', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Incorporated', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Incorporated', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Corp ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Corp ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Inc ', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Inc ', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Inc.', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Inc.', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'inc', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'inc', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'Corp.', '', regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'Corp.', '', regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'non-profit corporation', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'non-profit corporation', '',  regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'nonprofit', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'nonprofit', '',  regex=True, case=False)
        df['legal_nm'] = df[df['legal_nm'].notnull()]['legal_nm'].str.replace(
            'non-profit', '',  regex=True, case=False)
        df['trade_nm'] = df[df['trade_nm'].notnull()]['trade_nm'].str.replace(
            'non-profit', '',  regex=True, case=False)
    return df


def RemovePunctuationFromCity(df):  # text cleanup: remove double spaces

    if 'cty_nm' in df.columns:
        df['cty_nm'] = df['cty_nm'].str.replace(',', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('.', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace(';', '', regex=False)
        #df['cty_nm'] = df['cty_nm'].str.replace('-','')
        df['cty_nm'] = df['cty_nm'].str.replace("'", '', regex=False)

        df['cty_nm'] = df['cty_nm'].str.replace('  ', ' ', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('&', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.strip(';,. ')

        df['cty_nm'] = df['cty_nm'].str.replace('(', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace(')', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('|', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('/', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('*', '', regex=False)
        df['cty_nm'] = df['cty_nm'].str.replace('  ', ' ', regex=False)

    return df


def RemovePunctuationFromAddresses(df):  # text cleanup: remove double spaces

    if 'street_addr' in df.columns:
        df['street_addr'] = df['street_addr'].str.replace(',', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace('.', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace(';', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace('-', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace("'", '', regex=False)

        df['street_addr'] = df['street_addr'].str.replace(
            '  ', ' ', regex=False)
        df['street_addr'] = df['street_addr'].str.replace(
            '&', 'and', regex=False)
        df['street_addr'] = df['street_addr'].str.strip(';,. ')

        df['street_addr'] = df['street_addr'].str.replace('(', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace(')', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace('|', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace('/', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace('*', '', regex=False)
        df['street_addr'] = df['street_addr'].str.replace(
            '  ', ' ', regex=False)

    return df


def RemoveDoubleSpacesFromAddresses(df):  # text cleanup: remove double spaces

    if 'street_addr' in df.columns:
        df['street_addr'] = df['street_addr'].str.replace(',,', ',')
        df['street_addr'] = df['street_addr'].str.replace('  ', ' ')
        df['street_addr'] = df['street_addr'].str.strip()
        df['street_addr'] = df['street_addr'].str.strip(';,. ')
    if 'legal_nm' in df.columns:
        df['legal_nm'] = df['legal_nm'].str.replace('  ', ' ')
    return df


def ReplaceAddressAbreviations(df):
    if 'street_addr' in df.columns:
        df['street_addr'] = df['street_addr'].str.replace('  ', ' ')
        df['street_addr'] = df['street_addr'].str.strip()
        df['street_addr'] = df['street_addr'].str.strip(';,. ')
        # add a right space to differentiate 'Ave ' from 'Avenue'
        df['street_addr'] = df['street_addr'].astype(str) + ' '

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CT.', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('WY.', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CTR.', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'AVE.', 'Avenue', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' ST.', ' Street', regex=False)  # bugget with EAST
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'DR.', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('RD.', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('LN.', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ.', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CT,', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('WY,', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CTR,', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'AVE,', 'Avenue', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' ST,', ' Street', regex=False)  # bugget with EAST
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'DR,', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('RD,', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('LN,', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ,', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CT ', 'Court ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('WY ', 'Way ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'CTR ', 'Center ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'AVE ', 'Avenue ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' ST ', ' Street ', regex=False)  # bugget with EAST
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'DR ', 'Drive ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'RD ', 'Road ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'LN ', 'Lane ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ ', 'Plaza ', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bCT$', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bWY$', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bCTR$', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bAVE$', 'Avenue', regex=False)
        #df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(r'\bST$', 'Street', regex = False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bDR$', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bRD$', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bLN$', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bPLZ$', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ct.', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Wy.', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ctr.', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ave.', 'Avenue', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'St.', 'Street', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Dr.', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Rd.', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Ln.', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ.', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ct,', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Wy,', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ctr,', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ave,', 'Avenue', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'St,', 'Street', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Dr,', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Rd,', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Ln,', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ,', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ct ', 'Court ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('Wy ', 'Way ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ctr ', 'Center ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ave ', 'Avenue ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'St ', 'Street ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Dr ', 'Drive ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Rd ', 'Road ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ln ', 'Lane ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'PLZ ', 'Plaza ', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bCt$', 'Court', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bWy$', 'Way', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bCtr$', 'Center', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bAve$', 'Avenue', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bSt$', 'Street', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bDr$', 'Drive', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bRd$', 'Road', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bLn$', 'Lane', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            r'\bPLZ$', 'Plaza', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Boulevard', 'Blvd.', False, re.IGNORECASE)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Expressway', 'Expy.', False, re.IGNORECASE)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Building', 'Bldg.', False, re.IGNORECASE)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'STE.', 'Suite', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ste.', 'Suite', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Ste ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'STE ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'APT.', 'Suite', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Apt.', 'Suite', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Apt ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'APT ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Unit ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'Unit', 'Suite', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '# ', 'Suite ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull(
        )]['street_addr'].str.replace('#', 'Suite ', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'S. ', 'South ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'W. ', 'West ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'E. ', 'East ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            'N. ', 'North ', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' S ', ' South ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' W ', ' West ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' E ', ' East ', regex=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            ' N ', ' North ', regex=False)

        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '1ST ', 'First ', regex=True, case=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '2ND ', 'Second ', regex=True, case=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '3RD ', 'Third ', regex=True, case=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '4TH ', 'Fourth ', regex=True, case=False)
        df['street_addr'] = df[df['street_addr'].notnull()]['street_addr'].str.replace(
            '5TH ', 'Fifth ', regex=True, case=False)
    return df


def StripPunctuationFromNames(df):
    if 'legal_nm' in df.columns:
        df['legal_nm'] = df['legal_nm'].astype(
            str)  # convert to str to catch floats
        df['legal_nm'] = df['legal_nm'].str.replace('  ', ' ', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('&', 'and', regex=False)
        df['legal_nm'] = df['legal_nm'].str.strip()
        df['legal_nm'] = df['legal_nm'].str.strip(';,. ')

        df['legal_nm'] = df['legal_nm'].str.replace(';', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace(',', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('.', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('-', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace("'", '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('(', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace(')', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('|', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('/', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('*', '', regex=False)
        df['legal_nm'] = df['legal_nm'].str.replace('  ', ' ', regex=False)

    if 'trade_nm' in df.columns:
        df['trade_nm'] = df['trade_nm'].astype(
            str)  # convert to str to catch floats
        df['trade_nm'] = df['trade_nm'].str.replace('  ', ' ', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('&', 'and', regex=False)
        df['trade_nm'] = df['trade_nm'].str.strip()
        df['trade_nm'] = df['trade_nm'].str.strip(';,. ')

        df['trade_nm'] = df['trade_nm'].str.replace(';', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('.', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace(',', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('-', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace("'", '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('(', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace(')', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('|', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('/', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('*', '', regex=False)
        df['trade_nm'] = df['trade_nm'].str.replace('  ', ' ', regex=False)

    return df


def RemoveDoubleSpacesFromCompanyName(df):
    if 'legal_nm' in df.columns:
        df['legal_nm'] = df['legal_nm'].str.replace(
            '  ', ' ')  # remove double spaces
        df['legal_nm'] = df['legal_nm'].str.replace(', , ', ', ')
        df['legal_nm'] = df['legal_nm'].str.replace(', , , ', ', ')
        df['legal_nm'] = df['legal_nm'].str.strip()
        df['legal_nm'] = df['legal_nm'].str.strip(';,. ')

    if 'trade_nm' in df.columns:
        df['trade_nm'] = df['trade_nm'].str.replace('  ', ' ')
        df['trade_nm'] = df['trade_nm'].str.replace(', , ', ', ')
        df['trade_nm'] = df['trade_nm'].str.replace(', , , ', ', ')
        df['trade_nm'] = df['trade_nm'].str.strip()
        df['trade_nm'] = df['trade_nm'].str.strip(';,. ')

        # add a right space to differentiate 'Inc ' from 'Incenerator'
        df['legal_nm'] = df['legal_nm'].astype(str) + ' '
        # add a right space to differentiate 'Inc ' from 'Incenerator'
        df['trade_nm'] = df['trade_nm'].astype(str) + ' '
    return df


def CleanUpAgency(df, COLUMN):
    if not df.empty and COLUMN in df.columns:
        # DLSE_terms = ['01','04', '05', '06', '07', '08', '09', '10', '11', '12', '13',
        # '14', '15', '16', '17', '18', '23','32']

        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '01', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '02', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '03', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '04', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '05', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '06', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '07', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '08', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '09', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '10', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '11', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '12', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '13', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '14', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '15', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '16', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '17', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '18', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '19', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '20', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '21', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '22', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '23', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '24', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '25', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            '35', 'DLSE', False, re.IGNORECASE)
        df[COLUMN] = df[df[COLUMN].notnull()][COLUMN].str.replace(
            'WC', 'DLSE', False, re.IGNORECASE)

    return df


def CleanNumberColumns(column):

    column = column.replace(
        to_replace="\$([0-9,\.]+).*", value=r"\1", regex=True)
    # column = str(column) #.astype(str)
    # #column = column.str.strip()
    column = column.replace(' ', '')
    # column = column.replace('$','')
    # column = column.replace(',','')
    column = column.replace("−", "-")
    column = column.replace('[)]', '', regex=True)
    column = column.replace('[(]', '-', regex=True)
    #column.loc[column == '-', column] = 0
    column = pd.to_numeric(column, errors='coerce')
    column = column.astype(float)

    column = column.fillna(0)
    column = column.abs()

    return column


def Cleanup_Number_Columns(df):

    if 'bw_amt' not in df.columns:
        df['bw_amt'] = 0
    if 'ee_pmt_due' not in df.columns:
        df['ee_pmt_due'] = 0
    if 'ee_violtd_cnt' not in df.columns:
        df['ee_violtd_cnt'] = 0
    if 'ee_pmt_recv' not in df.columns:
        df['ee_pmt_recv'] = 0
    if 'Interest_Balance_Due' not in df.columns:
        df['Interest_Balance_Due'] = 0
    if 'Interest_Payments_Recd' not in df.columns:
        df['Interest_Payments_Recd'] = 0
    if 'cmp_assd_cnt' not in df.columns:
        df['cmp_assd_cnt'] = 0
    if 'violtn_cnt' not in df.columns:
        df['violtn_cnt'] = 0

    df['bw_amt'] = CleanNumberColumns(df['bw_amt'])
    df['ee_pmt_due'] = CleanNumberColumns(df['ee_pmt_due'])
    df['ee_violtd_cnt'] = CleanNumberColumns(df['ee_violtd_cnt'])
    df['ee_pmt_recv'] = CleanNumberColumns(df['ee_pmt_recv'])
    df['Interest_Balance_Due'] = CleanNumberColumns(df['Interest_Balance_Due'])
    df['Interest_Payments_Recd'] = CleanNumberColumns(
        df['Interest_Payments_Recd'])
    df['cmp_assd_cnt'] = CleanNumberColumns(df['cmp_assd_cnt'])

    df['violtn_cnt'] = df['violtn_cnt'].abs()

    return df


def Clean_Summary_Values(DF_OG_VLN):

    DF_OG_VLN['bw_amt'] = CleanNumberColumns(DF_OG_VLN['bw_amt'])
    DF_OG_VLN['ee_pmt_due'] = CleanNumberColumns(DF_OG_VLN['ee_pmt_due'])
    DF_OG_VLN['violtn_cnt'] = CleanNumberColumns(DF_OG_VLN['violtn_cnt'])
    DF_OG_VLN['ee_violtd_cnt'] = CleanNumberColumns(DF_OG_VLN['ee_violtd_cnt'])
    DF_OG_VLN['ee_pmt_recv'] = CleanNumberColumns(DF_OG_VLN['ee_pmt_recv'])

    return DF_OG_VLN


def FormatNumbersHTMLRow(df):
    if not df.empty:
        df['bw_amt'] = df.apply(
            lambda x: "{0:,.0f}".format(x['bw_amt']), axis=1)
        df['ee_pmt_due'] = df.apply(
            lambda x: "{0:,.0f}".format(x['ee_pmt_due']), axis=1)
        df['ee_violtd_cnt'] = df.apply(
            lambda x: "{0:,.0f}".format(x['ee_violtd_cnt']), axis=1)
        df['ee_pmt_recv'] = df.apply(
            lambda x: "{0:,.0f}".format(x['ee_pmt_recv']), axis=1)
        df['violtn_cnt'] = df.apply(
            lambda x: "{0:,.0f}".format(x['violtn_cnt']), axis=1)

    return df


# drop duplicated backwage values, keeping the first
def DropDuplicateBackwage(df, FLAG_DUPLICATE):
    if not df.empty and 'case_id' in df.columns:
        df['case_id'] = df['case_id'].str.strip()  # remove spaces
        df["ee_pmt_due_x"] = df["ee_pmt_due"]

        df["_DUP_BW"] = df.duplicated(
            subset=['case_id', 'legal_nm', 'violation', 'bw_amt'], keep=False)
        df["_DUP_PMT_REC"] = df.duplicated(
            subset=['case_id', 'legal_nm', 'violation', 'ee_pmt_recv'], keep=False)

        # violation is ignored due to a specific error in the dataset--however, for generality, this should check that violation are different and then rzero if value is the same
        df["_DUP_PMT_DUE"] = df.duplicated(
            subset=['case_id', 'legal_nm', 'ee_pmt_due'], keep=False)

        df["_DUP_PMT_DUE_X"] = df.duplicated(
            subset=['case_id', 'legal_nm', 'ee_pmt_due'], keep='first')
        df["ee_pmt_due_x"] = np.where(
            df['_DUP_PMT_DUE_X'] == True, 0, df["ee_pmt_due_x"])

        # drop for report
        if FLAG_DUPLICATE == 0:
            df["ee_pmt_due"] = np.where(
                df['_DUP_PMT_DUE_X'] == True, 0, df["ee_pmt_due"])
    return df


def DropDuplicateRecords(df, FLAG_DUPLICATE):

    if not df.empty and 'case_id' in df.columns:
        df['case_id'] = df['case_id'].str.strip()  # remove spaces

        # always remove full duplicates and nearly full duplicates
        df = df.drop_duplicates(keep='first')
        # assumes that ee_pmt_due will sort same as ee_pmt_recv and that both values are either present or not
        df = df.sort_values('ee_pmt_recv', ascending=False).drop_duplicates(
            ['case_id', 'violation', 'bw_amt'], keep='first').sort_index()

        # always label
        #df["_DUP_Person"] = df.duplicated(subset=['Submitter_Email', 'Responsible_Person_Phone'], keep=False)
        df["_Case_X"] = df.duplicated(
            subset=['case_id', 'violation', 'bw_amt'], keep=False)
        df["_T_NM_X"] = df.duplicated(
            subset=['case_id', 'trade_nm', 'street_addr', 'violation', 'bw_amt'], keep=False)
        df["_L-NM_X"] = df.duplicated(subset=['case_id', 'legal_nm',
                                              'street_addr', 'violation', 'bw_amt'], keep=False)

        # drop for report
        if FLAG_DUPLICATE == 0:
            df = df.drop_duplicates(
                subset=['case_id', 'violation', 'bw_amt'], keep='first')
            df = df.drop_duplicates(
                subset=['case_id', 'trade_nm', 'street_addr', 'violation', 'bw_amt'], keep='first')
            df = df.drop_duplicates(
                subset=['case_id', 'legal_nm', 'street_addr', 'violation', 'bw_amt'], keep='first')

    return df


# aggregated functions*********************************

def Cleanup_Text_Columns(df):

    df = ReplaceAddressAbreviations(df)
    # https://pypi.org/project/pyspellchecker/
    df = RemoveDoubleSpacesFromAddresses(df)
    df = RemovePunctuationFromAddresses(df)  # once more
    # https://pypi.org/project/pyspellchecker/
    df = RemoveDoubleSpacesFromAddresses(df)

    df = RemovePunctuationFromCity(df)  # once more

    df = StripPunctuationFromNames(df)
    df = RemoveDoubleSpacesFromCompanyName(df)
    df = MoveCorportationBusinessTypeToBusinessTypeColumn(df)
    df = MovePartnershipBusinessTypeToBusinessTypeColumn(df)
    df = MoveLimitedLiabilityBusinessTypeToBusinessTypeColumn(df)
    df = MoveBusinessTypeToBusinessTypeColumn(df)
    df = MoveCompanyLiabilityTermsToLiabilityTypeColumn(df)
    df = StripPunctuationFromNames(df)

    # run a second time
    df = RemoveDoubleSpacesFromCompanyName(df)
    df = StripPunctuationFromNames(df)
    df = MoveCorportationBusinessTypeToBusinessTypeColumn(df)
    df = MovePartnershipBusinessTypeToBusinessTypeColumn(df)
    df = MoveLimitedLiabilityBusinessTypeToBusinessTypeColumn(df)
    df = MoveBusinessTypeToBusinessTypeColumn(df)
    df = MoveCompanyLiabilityTermsToLiabilityTypeColumn(df)
    df = StripPunctuationFromNames(df)

    # run a third time
    df = RemoveDoubleSpacesFromCompanyName(df)
    df = StripPunctuationFromNames(df)
    df = MoveCorportationBusinessTypeToBusinessTypeColumn(df)
    df = MovePartnershipBusinessTypeToBusinessTypeColumn(df)
    df = MoveLimitedLiabilityBusinessTypeToBusinessTypeColumn(df)
    df = MoveBusinessTypeToBusinessTypeColumn(df)
    df = MoveCompanyLiabilityTermsToLiabilityTypeColumn(df)
    df = StripPunctuationFromNames(df)

    return df


def Signatory_List_Cleanup(df_signatory):

    df_signatory['legal_nm'] = df_signatory['legal_nm'].str.upper()
    df_signatory['street_addr'] = df_signatory['street_addr'].str.upper()
    df_signatory['cty_nm'] = df_signatory['cty_nm'].str.upper()
    df_signatory['st_cd'] = df_signatory['st_cd'].str.upper()

    # deleted all companiy names shorter than 9 letters

    # add missing columns to allow program to go through expected columns
    #df_signatory['legal_nm'] = ""
    #df_signatory['street_addr'] = ""
    #df_signatory['cty_nm'] = ""
    #df_signatory['st_cd'] = ""
    #df_signatory['zip_cd'] = ""

    df_signatory['trade_nm'] = ""
    df_signatory['industry'] = ""
    df_signatory['Prevailing'] = ""
    df_signatory['Signatory'] = ""
    df_signatory['Businesstype'] = ""
    df_signatory['naic_cd'] = ""
    df_signatory['naics_desc.'] = ""

    df_signatory['length'] = df_signatory.legal_nm.str.len()
    company_name_length = 6
    # df_signatory = df_signatory[df_signatory.length > company_name_length] #https://stackoverflow.com/questions/42895061/how-to-remove-a-row-from-pandas-dataframe-based-on-the-length-of-the-column-valu

    df_signatory = StripPunctuationFromNames(df_signatory)
    df_signatory = RemoveDoubleSpacesFromCompanyName(df_signatory)
    df_signatory = MoveCorportationBusinessTypeToBusinessTypeColumn(
        df_signatory)
    df_signatory = MovePartnershipBusinessTypeToBusinessTypeColumn(
        df_signatory)
    df_signatory = MoveLimitedLiabilityBusinessTypeToBusinessTypeColumn(
        df_signatory)
    df_signatory = MoveBusinessTypeToBusinessTypeColumn(df_signatory)
    df_signatory = MoveCompanyLiabilityTermsToLiabilityTypeColumn(df_signatory)
    df_signatory = StripPunctuationFromNames(df_signatory)

    df_signatory['zip_cd'] = df_signatory['zip_cd'].where(  # remove zipcode suffix #https://stackoverflow.com/questions/44776115/remove-four-last-digits-from-string-convert-zip4-to-zip-code/44776170
        df_signatory['zip_cd'].str.len() == 5,
        df_signatory['zip_cd'].str[:5]
    )

    df_signatory = ReplaceAddressAbreviations(df_signatory)
    df_signatory = RemoveDoubleSpacesFromAddresses(
        df_signatory)  # https://pypi.org/project/pyspellchecker/
    df_signatory = RemovePunctuationFromAddresses(df_signatory)  # once more
    df_signatory = RemoveDoubleSpacesFromAddresses(
        df_signatory)  # https://pypi.org/project/pyspellchecker/

    return df_signatory


def Setup_Regular_headers(df):  # DSLE, WHD, etc headers

    df = df.rename(columns={
        'naics_code_description': 'naics_desc.',
        'EE_Payments_Received': 'ee_pmt_recv',  # causing trouble 11/1/2020
        'Balance_Due_to_Employee(s)': 'ee_pmt_due',
        'street_addr_1_txt': 'street_addr',
        'legal_name': 'legal_nm',
        'Jurisdiction_or_Project_Name': 'juris_or_proj_nm',
        'case_violtn_cnt': 'violtn_cnt',
        'bw_atp_amt': 'bw_amt',
        'trade': 'industry',

        #DLSE specific to conform to WHD -- added 10/2/2022
        'Case Number': 'case_id',
        'Account - DBA':'trade_nm',
        'Employer':'legal_nm',

        'Primary Address Street':'street_addr',
        'Primary Address City': 'cty_nm',
        'Primary Address State': 'st_cd',
        
        'NAICS Code': 'naic_cd',
        'NAICS Code Title': 'naics_desc.', #'naics_desc.',

        #'':'case_violtn_cnt',
        #'':'cmp_assd_cnt',
        #'':'ee_violtd_cnt',
        'EE(s) Amt Assessed':'bw_amt',
        "EE Payments Rec'd":'ee_pmt_recv',

        'Date of Docket':'findings_start_date',
        'Case Closed Date':'findings_end_date',

        'Case Issue Type':'violation',
        'DIR Office':'Jurisdiction_region_or_General_Contractor'
    })

    if 'trade_nm' not in df.columns:
        df['trade_nm'] = ""
    if 'legal_nm' not in df.columns:
        df['legal_nm'] = ""
    if 'Businesstype' not in df.columns:
        df['Businesstype'] = ""

    if 'street_addr' not in df.columns:
        df['street_addr'] = ""
    if 'zip_cd' not in df.columns:
        df['zip_cd'] = '0' #10/27/2022 change from 0 to False -- then to '0'

    if 'Prevailing' not in df.columns:
        df['Prevailing'] = ""
    if 'Signatory' not in df.columns:
        df['Signatory'] = ""

    if 'industry' not in df.columns:
        df['industry'] = ""
    if 'naic_cd' not in df.columns:
        df['naic_cd'] = ""

    if 'violation' not in df.columns:
        df['violation'] = ""
    if 'violation_code' not in df.columns:
        df['violation_code'] = ""
    if 'ee_violtd_cnt' not in df.columns:
        df['ee_violtd_cnt'] = 0
    if 'violtn_cnt' not in df.columns:
        df['violtn_cnt'] = 0
    if 'bw_amt' not in df.columns:
        df['bw_amt'] = 0

    if 'ee_pmt_recv' not in df.columns:
        df['ee_pmt_recv'] = 0
    if 'ee_pmt_due' not in df.columns:
        df['ee_pmt_due'] = 0
    if 'Paid' not in df.columns:
        df['Paid'] = ""

    if 'records' not in df.columns:
        df['records'] = 0

    if 'Note' not in df.columns:
        df['Note'] = ""
    if 'juris_or_proj_nm' not in df.columns:
        df['juris_or_proj_nm'] = ""
    if 'Jurisdiction_region_or_General_Contractor' not in df.columns:
        df['Jurisdiction_region_or_General_Contractor'] = ""

    return df


def Define_Column_Types(df):

    # Define column types**********************
    if 'case_id' and 'legal_nm' and 'trade_nm' and 'naic_cd' in df.columns:
        df['naic_cd'] = df['naic_cd'].astype(str)
        df['case_id'] = df['case_id'].astype(str)
        df['legal_nm'] = df['legal_nm'].astype(str)
        df['trade_nm'] = df['trade_nm'].astype(str)
        df['street_addr'] = df['street_addr'].astype(str)
        df['cty_nm'] = df['cty_nm'].str.upper()
        df['st_cd'] = df['st_cd'].astype(str)
        df['zip_cd'] = df['zip_cd'].astype(str)

        df['zip_cd'] = df['zip_cd'].where(  # remove zip code suffix #https://stackoverflow.com/questions/44776115/remove-four-last-digits-from-string-convert-zip4-to-zip-code/44776170
            df['zip_cd'].str.len() == 5,
            df['zip_cd'].str[:5]
        )
        df['zip_cd'] = df['zip_cd'].replace('nan', '0', regex=True)

        df['Prevailing'] = pd.to_numeric(
            df['Prevailing'], errors='coerce')
        df["Signatory"] = pd.to_numeric(
            df["Signatory"], errors='coerce')
        df['bw_amt'] = pd.to_numeric(df['bw_amt'], errors='coerce')
        df['ee_pmt_recv'] = pd.to_numeric(
            df['ee_pmt_recv'], errors='coerce')
        df['ee_pmt_due'] = pd.to_numeric(
            df['ee_pmt_due'], errors='coerce')

        df['legal_nm'] = df['legal_nm'].str.upper()
        df['trade_nm'] = df['trade_nm'].str.upper()
        df['street_addr'] = df['street_addr'].str.upper()
        df['cty_nm'] = df['cty_nm'].str.upper()
        df['st_cd'] = df['st_cd'].str.upper()

    return df


def Signatory_Library():

    hospital_signatories = [['Health_care'], ['El Camino Hospital', 'El Camino Hospital Los Gatos', 'El Camino HospitalLos Gatos',
                                              'VA Palo Alto Health Care System', 'OConner Hospital', 'Santa Clara Valley Medical Center', 'Good Samaritan Hospital',
                                              'El Camino Hospital Mountain View', 'El Camino HospitalMountain View', 'El Camino Hospital Mountain View',
                                              'Lucile Packard Childrens Hospital', 'LPC Hospital', 'Kaiser Permanente San Jose Medical Center', 'Regional Medical Center of San Jose',
                                              'Kaiser Permanente Hospital', 'Kaiser Permanente Santa Clara Medical Center', 'Kaiser Permanente', 'Kaiser Permanente Medical Center',
                                              'Saint Louise Regional Hospital', 'Saint Louise Hospital', 'Stanford University Hospital', 'Stanford Hospital']]

    construction_signatories = [['Construction'], ["Granite Construction", "A Ruiz Construction", "Central Fence", r"\bQLM\b",
                                                   "Otis Elevator ", "United Technologies", "Kiewit Pacific", "West Valley Construction", r"\bFerma\b", "TEICHERT CONSTRUCTION",
                                                   "Alliance Roofing", "Northern Underground Construction", "Albanese", "Vance Brown", "William ONeill Lath and Plastering",
                                                   "El Camino Paving"]]

    signatories_UCON = [['Construction'], ["Yerba Buena Engineering", "WoodruffSawyer", "WMA Landscape Construction", "William A Guthridge", "Whiteside Concrete Construction", "Westside Underground Pipe", "Westland Contractors",
                                           "Western Traffic Supply", "Western States Tool", "Western Stabilization", "West Valley Construction", "West Coast Sand and Gravel", "Wayne E Swisher Cement Contractor", "Walter C Smith", "Walsh Construction",
                                           "Waller", "W R Forde Associates", "W C Maloney", "W Bradley Electric", "W Contracting", "Vulcan Materials", "Vulcan Construction and Maintenance", "Volvo Construction Equipment", "Vintage Paving",
                                           "Viking Drillers", "Viking Construction", "Veteran Pipeline Construction", "Varela", "Vanguard Construction", "Valverde Construction", r"\bValentine\b", "United Rentals", "Underwater Resources", "Underground Construction",
                                           "Trunxai Construction", "Troutman Sanders", "TriWest Tractor", "TriValley Excavating", "Trinet Construction", "Trench Shoring", "Trench Plate Rental", "Trench and Traffic Supply", "Traffic Management", "Tracy Grading and Paving",
                                           "TPR Traffic Solutions", "Total Traffic Control", "Tony Skulick", "Tom McCready", "Thomas Lum", "The Hartford", "The Guarantee Company of North America", "The Construction Zone", "TerraCon Constructors", "Tennyson Electric",
                                           "Teichert Waterworks", "Teichert Utilities", "Teichert Solar", "Teichert Pipelines", "Teichert", "Team Ghilotti", "TBC Safety", "Talus Construction", "Taber Construction", "TDW Construction", "T and S Construction", "Syar Industries",
                                           "Sweeney Mason", "Super Seal and Stripe", "Sunbelt Rentals", "Sukut Construction", "Suarez and Munoz Construction", "Sturgeon Electric California", "Striping Graphics", "Stormwater Specialists", "Storm Water Inspection and Maint Svcs", r"\bSWIMS\b",
                                           r"\bStomper\b", "Stoloski and Gonzalez", "Stevenson Supply", "Stevens Creek Quarry", "Steve P Rados", "Steelhead Constructors", "Stacy and Witbeck", "St Francis Electric", "SPSG Partners", "Sposeto Engineering", "SpenCon Construction",
                                           "Sonsray Machinery", "SMTD Law", "Smith Denison Construction", "Smith Currie and Hancock", "SITECH NorCal", "Sinclair General Engineering Construction", "Silverado Contractors", "Silvas Pipeline", "Sierra Traffic Markings",
                                           "Sierra Mountain Construction", "Shimmick Construction", "Sherry Montoya", "Shaw Pipeline", "Sharon Alberts", "Seyfarth Shaw", "Serafix Engineering Contractors", "Security Shoring and Steel Plate", "Security Paving",
                                           "Schembri Construction", "SANDIS Civil Engineers Surveyors Planners", "Sanco Pipelines", "S and S Trucking", "Ryan Engineering", "Rutan and Tucker", "Rupert Construction Supply", "Royal Electric", "Rosie Garcia", "Rosendin Electric",
                                           "Rogers Joseph ODonnell", "Robust Network Solutions", "Robert Burns Construction", "Robert A Bothman Construction", "Roadway Construction", "Road Machinery", "RNR Construction", "Rinker MaterialsConcrete Pipe Division", "RGW Equipment Sales",
                                           "RGW Construction", "Revel Environmental Manufacturing", r"\bREM\b", "Reliable Trucking", "Reed and Graham", "Redgwick Construction", "Rebel Equipment Enterprises", "RDOVermeer", "RDO Integrated Controls", "RCI General Engineering",
                                           "RC Underground", "Rays Electric", r"\bRansome\b", "Ranger Pipelines", "Ramos Oil", "RAM Rick Albert Machinery", "Rain for Rent", "Rafael De La Cruz", r"\bRM Harris\b", "RJ Gordon Construction", "RC Fischer",
                                           "RA Nemetz Construction", "R E Maher", "RandS Construction Management", r"\bRandB\b", "R and W Concrete Contractors", "R and R Maher Construction", "R and B Equipment", r"\bQLM\b", "Proven Management", "Preston Pipelines",
                                           "Prestige Printing and Graphics", "Precision Engineering", "Precision Drilling", "Power One", "Power Engineering Construction", "Poms Landscaping", "PMK Contractors", "Platinum Pipeline", "PJs Rebar", "PIRTEK San Leandro",
                                           "Petrinovich Pugh", "Peterson Trucks", "Peterson Cat", "Peter Almlie", "Performance Equipment", "Penhall", "Pedro Martinez", "Pavement Recycling Systems", "Paul V Simpson", "Pape Machinery",
                                           "Pacific International Construction", "Pacific Infrastructure Const", "Pacific Highway Rentals", "Pacific Excavation", "Pacific Coast General Engineering", "Pacific Coast Drilling", "Pacific Boring", "PACE Supply",
                                           "P C and N Construction", "P and F Distributors", "Outcast Engineering", "Org Metrics", "OnSite Health and Safety", "Oldcastle Precast", "Oldcastle Enclosure Solutions", "OGrady Paving", "Odyssey Environmental Services",
                                           "Oak Grove Construction", "OC Jones and Sons", "Northwest Pipe", "NorCal Concrete", "Nor Cal Pipeline Services", "NixonEgli Equipment", "Nevada Cement", "Neary Landscape", "Navajo Pipelines",
                                           "National Trench Safety", "National Casting", "Nada Pacific", "Mozingo Construction", "Mountain F Enterprises", "Mountain Cascade", "Moss Adams", "Moreno Trenching", "Mobile Barriers MBT1", "MK Pipelines",
                                           "MJG Constructors", "Mitchell Engineering", "Mission Constructors", "Mission Clay Products", "MinervaGraniterock", "Minerva Construction", "Mike Brown Electric", "Midstate Barrier", r"\bMichels\b", "McSherry and Hudson",
                                           "MCK Services", "McInerney and Dillon PC", "McGuire and Hester", "Martin General Engineering", "Martin Brothers Construction", "Marques Pipeline", "Marinship Development Interest", "Marina Landscape", "Malcolm International",
                                           "Main Street Underground", "Maggiora and Ghilotti", "MF Maher", "Hernandez Engineering", "M Squared Construction", "M and M Foundation and Drilling", "Luminart Concrete", "Lorang Brothers Construction", "Long Electric",
                                           "Lone Star Landscape", "Liffey Electric", "Liberty Contractors", "Leonidou and Rosin Professional", "Lehigh Hanson", "LeClairRyan", "Last and Faoro", "Las Vegas Paving", "Landavazo Bros", "Labor Services", "Knife River Construction",
                                           "Kerex Engineering", "Kelly Lynch", "KDW Construction", "Karen Wonnenberg", "KJ Woods Construction", r"\bJS Cole\b", "Joseph J Albanese", "Jon Moreno", "Johnston, Gremaux and Rossi", "John S Shelton", "Joe Sostaric",
                                           "Joe Gannon", "JMB Construction", "JLM Management Consultants", "Jimni Rentals", "Jifco", "Jensen Precast", "Jensen Landscape Contractor", "Jeff Peel", "JDB and Sons Construction", "JCC", "James J Viso Engineering", "JAM Services",
                                           "JM Turner Engineering", "JJR Construction", "J Mack Enterprises", "J Flores Construction", "J D Partners Concrete", "J and M", "IronPlanet", "Interstate Grading and Paving", "Interstate Concrete Pumping",
                                           "Integro Insurance Brokers", "Innovate Concrete", "Inner City Demolition", "Industrial Plant Reclamation", "Independent Structures", "ICONIX Waterworks", r"\bHoseley\b", "Horizon Construction", "Hess Construction",
                                           "Harty Pipelines", "Harris Blade Rental", "Half Moon Bay Grading and Paving", "HandE Equipment Services", "Guy F Atkinson Construction", "GSL Construction", "Griffin Soil Group", "Graniterock", "Granite Construction",
                                           "Gordon N Ball", "Goodfellow Bros", "Gonsalves and Santucci", "The Conco Companies", "Golden Gate Constructors", "Golden Bay Construction", "Goebel Construction", "Gilbertson Draglines", "Ghilotti Construction", "Ghilotti Bros",
                                           "GECMS/McGuire and Hester JV", "Garney Pacific", "Gallagher and Burk", "G Peterson Consulting Group", "Fox Loomis", "Forterra", "Ford Construction", "Fontenoy Engineering", "Florez Paving", "Flatiron West", "Fisher Phillips",
                                           "Fine Line Sawing and Drilling", "Fermin Sierra Construction", r"\bFerma\b", "Ferguson Welding Service", "Ferguson Waterworks", "Farwest Safety", "Evans Brothers", "Esquivel Grading and Paving", "Enterprise Fleet Management",
                                           "Eighteen Trucking", "Economy Trucking", "Eagle Rock Industries", "EE Gilbert Construction", "Dynamic Office and Accounting Solutions", "Dutch Contracting", "Duran Construction Group", "Duran and Venables", "Druml Group",
                                           "Drill Tech Drilling and Shoring", "Doyles Work", "Downey Brand", "Dorfman Construction", "DMZ Transit", "DMZ Builders", "DLine Constructors", "Dixon Marine Services", "Ditch Witch West", "Disney Construction",
                                           "DirtMarket", "DHE Concrete Equipment", "DeSilva Gates Construction", "Demo Masters", "Dees Burke Engineering Constructors", "Debbie Ferrari", "De Haro Ramirez Group", "DDM Underground", "D'Arcy and Harty Construction",
                                           "DW Young Construction", "DP Nicoli", "DA Wood Construction", "D and D Pipelines", "Cushman and Wakefield", "Cratus Inc", "County Asphalt", "Corrpro Companies", "Corix Water Products", "Core and Main LP", "Cooper Engineering",
                                           "Contractor Compliance", "Construction Testing Services", "ConQuest Contractors", "CondonJohnson and Associates", "Concrete Demo Works", "ConcoWest", "Compass Engineering Contractors", "Command Alkon", "Columbia Electric",
                                           "CMD Construction Market Data", "CMC Construction", "Clipper International Equipment", "Champion Contractors", "Central Striping Service", "Central Concrete Supply", "Centerline Striping", "Carpenter Rigging", r"\bCarone\b",
                                           r"\bCampanella\b", "CalSierra Pipe", "California Trenchless", "California Portland Cement", "California Engineering Contractors", "Cal State Constructors", "Cal Safety", "CF Archibald Paving", "CandN Reinforcing", "Burnham Brown",
                                           "Bugler Construction", "Bruce Yoder", "Bruce Carone Grading and Paving", "Brosamer and Wall", "BrightView Landscape Development", "Bridgeway Civil Constructors", "Brianne Conroy", "Brian Neary", "Brendan Coyne", r"\bBolton\b", r"\bBob Heal\b",
                                           "BlueLine Rental", "Blue Iron Foundations and Shoring", "Blaisdell Construction", "Bill Crotinger", "Bertco", "Berkeley Cement", "Bentancourt Bros Construction", "Beliveau Engineering Contractors", "Bear Electrical Solutions",
                                           "Bayside Stripe and Seal", "Bay Pacific Pipeline", "Bay Line Cutting and Coring", "Bay Cities Paving and Grading", "Bay Area Traffic Solutions", "Bay Area Concretes", "Bay Area Barricade Service", "Bay Area Backhoes",
                                           "Bauman Landscape and Construction", "Badger Daylighting", "B and C Asphalt Grinding", "Azul Works", "AWSI", "AVAR Construction", "Atlas Peak Construction", "Atkinson", "Argonaut Constructors", "Argent Materials",
                                           "Arcadia Graphix and Signs", "Appian Engineering", "Apex Rents", "APB General Engineering", "Aon Construction Services Group", "Anvil Builders", r"\bAnrak\b", "Andreini Brothers", r"\bAndreini\b", "Andes Construction",
                                           "AMPCO North", "American Pavement Systems", "Alex Moody", "AJW Construction", "Advanced Stormwater Protection", "Advanced Drainage Systems", "Adrian Martin", "A and B Construction"]]

    signatories_CEA = [['Construction'], ["Alcal Specialty Contracting", "Alten Construction", r"\bOveraa\b", "Cahill Contractors", "Clark Construction", "Clark Pacific", "Dolan Concrete Construction", "Dome Construction", "DPR Construction",
                                          "Gonsalves and Stronck Construction", "Hathaway Dinwiddie Construction", "Howard Verrinder", "Obayashi", "Lathrop Construction", "McCarthy Building", "Nibbi Bros Associates", "Peck and Hiller", "Roebbelen Contracting",
                                          "Roy Van Pelt", "Rudolph and Sletten", "SJ Amoroso Construction", "Skanska", "Suffolk Construction", "Swinerton Builders", "Thompson Builders", "Webcor Builders", "XL Construction", "Rosendin Electric", "Boss Electric",
                                          "Cupertino Electric", 'Beltramo Electric', 'The Best Electrical', 'CH Reynolds Electric', 'Cal Coast Telecom', 'Comtel Systems Technology', 'Cupertino Electric', 'CSI Electrical Contractors',
                                          'Delgado Electric', 'Elcor Electric', 'Friel Energy Solutions', 'ICS Integrated Comm Systems', 'Intrepid Electronic Systems', 'MDE Electric', 'MidState Electric', 'Pacific Ridge Electric',
                                          'Pfeiffer Electric', 'Radiant Electric', 'Ray Scheidts Electric', 'Redwood Electric Group', 'Rosendin Electric', 'Sanpri Electric', 'Sasco Electric', 'Selectric Services', 'San Jose Signal Electric',
                                          'Silver Creek Electric', 'Splicing Terminating and Testing', 'Sprig Electric', 'TDN Electric', 'TL Electric', r'\bTherma\b', 'Thermal Mechanical', 'Don Wade Electric', 'ABCO Mechanical Contractors',
                                          'ACCO Engineered Systems', 'Air Conditioning Solutions', 'Air Systems Service and Construction', 'Air Systems', 'Airco Mechanical', 'Allied Heating and AC', 'Alpine Mechanial Service', 'Amores Plumbing',
                                          'Anderson Rowe and Buckley', 'Applied Process Cooling', 'Arc Perfect Solutions', 'Axis Mechanicals', 'Ayoob and Peery', 'Ayoob Mechanical', 'Bacon Plumbing', 'Bay City Mechanical', 'Bayline Mechancial',
                                          'Bell Products', 'Bellanti Plumbing', 'Booth Frank', 'Brady Air Conditioning', 'Broadway Mechanical Contractors', 'Brothers Energy', 'Cal Air', 'Cal Pacific Plumbing Systems', r'\bCARRIER\b',
                                          'City Mechanical', 'CNS Mechanical', 'Cold Room Solutions', 'Comfort Dynamics', 'Commerical Refrigeration Specialist', 'Cool Breeze Refrigeration', 'Critchfield Mechanical', 'Daikin Applied', 'Daniel Larratt Plumbing',
                                          'Desert Mechanical', 'Done Rite Plumbing', 'Dowdle Andrew and Sons', r'\bDPW\b', 'Egan Plumbing', 'Emcor Services', 'Mesa Energy', 'Envise', 'Estes Refrigeration', 'Green Again Landscaping and Concrete', 'Hickey W L Sons',
                                          'Johnson Controls M54', 'KDS Plumbing', 'KEP Plumbing', 'Key Refrigeration', 'Kinectics Mechanical Services', 'KMC Plumbing', 'KOH Mechanical Contractors', r'\bKruse L J\b', 'Larratt Bros Plumbing',
                                          'Lawson Mechanical Contractors', r'\bLescure\b', 'LiquiDyn', 'Marelich Mechanical', 'Masterson Enterprises', 'Matrix HG', 'McPhails Propane Installation', r'\bMcPhails\b', r'\bMitchell E\b', 'Monterey Mechanical',
                                          'MSR Mechanical', 'Murray Plumbing and Heating', 'OC McDonald', 'OBrien Mechanical', 'OMNITemp Refrigeration', 'Pacific Coast Trane', 'PanPacific Mechanical', 'Peterson Mechanical',
                                          r'\bPMI\b', 'POMI Mechanical', 'Pribuss Engineering', 'Quest Mechanical', 'RG Plumbing', 'Redstone Plumbing', 'Refrigeration Solutions', 'Reichel', 'C R Engineering', 'Rigney Plumbing',
                                          'Rountree Plumbing and Heating', 'S and R Mechanical', 'Schram Construction', 'Southland Industries', 'Spencer F W and Sons', 'Temper Insulation', 'Therma', 'Thermal Mechanical', 'United Mechanical',
                                          'Valente A and Sons', 'Westates Mechanical', 'Western Allied Mechanical', 'White Water Plumbing', 'Blues roofing']]

    SIGNATORIES = [['All_SIGNATORIES'], hospital_signatories,
                   signatories_CEA, signatories_UCON, construction_signatories]

    return SIGNATORIES


def Read_Violation_Data(TEST_CASES, url, out_file_report):

    df_csv = pd.DataFrame()
    df_csv = read_from_url(url, TEST_CASES)

    df_csv['juris_or_proj_nm'] = out_file_report
    df_csv = Setup_Regular_headers(df_csv)

    save_backup_to_folder(df_csv, out_file_report + '_backup', "csv_read_backup/")

    return df_csv


def save_backup_to_folder(df_csv, out_file_report_name = 'backup_', out_file_report_path = ""):
    from os.path import exists
    import os

    if out_file_report_path == "": out_file_report_path = out_file_report_path + '_backup/' #defualt folder name
    script_dir = os.path.dirname(os.path.dirname(__file__))
    abs_path = os.path.join(script_dir, out_file_report_path)
    if not os.path.exists(abs_path):  # create folder if necessary
        os.makedirs(abs_path)
    file_type = '.csv'
    
    file_name_backup = os.path.join(abs_path, (out_file_report_name).replace('/', '') + file_type)  # <-- absolute dir and file name
    df_csv.to_csv(file_name_backup) #uncomment for testing


def read_from_local(path, TEST_CASES):
    df_csv = pd.read_csv(path, encoding = "ISO-8859-1", low_memory=False, thousands=',', nrows=TEST_CASES, dtype={'zip_cd': 'str'} )
    return df_csv 


def read_from_url(url, TEST_CASES):
    req = requests.get(url)
    buf = io.BytesIO(req.content)
    if url[-3:] == 'zip':
        df_csv = pd.read_csv(buf, compression='zip', low_memory=False,
                             thousands=',', encoding="ISO-8859-1", sep=',', nrows=TEST_CASES, on_bad_lines="skip")
    else:
        df_csv = pd.read_csv(buf, low_memory=False, thousands=',',
                             encoding="ISO-8859-1", sep=',', nrows=TEST_CASES, on_bad_lines="skip")
    return df_csv


def Title_Block(TEST, DF_OG_VLN, DF_OG_ALL, target_jurisdition, TARGET_INDUSTRY, prevailing_wage_report, federal_data, state_data, textFile):
    textFile.write(
        f"<h1>DRAFT REPORT: Wage Theft in the Jurisdiction of {target_jurisdition} for {TARGET_INDUSTRY[0][0]} Industry</h1> \n")
    if prevailing_wage_report == 1:
        textFile.write(
            f"<h2 align=center>***PREVAILING WAGE REPORT***</h2> \n")
    if federal_data == 1 and state_data == 0:
        textFile.write(
            f"<h2 align=center>***FEDERAL DOL WHD DATA ONLY***</h2> \n")  # 2/5/2022
    if federal_data == 0 and state_data == 1:
        textFile.write(
            f"<h2 align=center>***CA STATE DLSE DATA ONLY***</h2> \n")
    textFile.write("\n")

    # all data summary block
    if TEST != 3:
        textFile.write("<p>These data are a combination of the Department of Labor Wage and Hour Division cases (not all result in judgments), the Division of Labor Standards Enforcement judgments, "
                       "and the San Jose Office of Enforcement cases. The WHD data were obtained from the DOL, the DLSE data were obtained through a Section 6250 CA Public Records Act request (up to Aug 1, 2019 and does not include purged cases which are those settled and then purged typically after three years), "
                       "and the City provided the SJOE data.</p>")

    textFile.write("\n")

    textFile.write(
        "<p>The dataset in this report is pulled from a larger dataset that for all regions and sources contains ")
    textFile.write(str.format('{0:,.0f}', DF_OG_ALL['case_id'].size))
    textFile.write(" cases")

    if not DF_OG_VLN['violtn_cnt'].sum() == 0:
        textFile.write(", ")
        textFile.write(str.format('{0:,.0f}', DF_OG_VLN['violtn_cnt'].sum()))
        textFile.write(" violations")

    if not DF_OG_ALL['ee_violtd_cnt'].sum() == 0:
        textFile.write(", ")
        textFile.write(str.format(
            '{0:,.0f}', DF_OG_ALL['ee_violtd_cnt'].sum()))
        textFile.write(" employees")

    if not DF_OG_VLN['bw_amt'].sum() == 0:
        textFile.write(", and  $ ")
        textFile.write(str.format('{0:,.0f}', DF_OG_VLN['bw_amt'].sum()))
        textFile.write(" in backwages")

    # if not DF_OG_VLN['ee_pmt_due'].sum()==0:
    # 	textFile.write(", and  $ ")
    # 	textFile.write(str.format('{0:,.0f}',DF_OG_VLN['ee_pmt_due'].sum() ) )
    # 	textFile.write(" in unpaid backwages")

    # <--i have no idea, it works fin above but here I had to do this 11/3/2020
    test_sum = DF_OG_VLN['ee_pmt_recv'].sum()
    if not test_sum == 0:
        textFile.write(", and  $ ")
        textFile.write(str.format('{0:,.0f}', test_sum))
        textFile.write(" in restituted backwages")

    textFile.write(".")

    textFile.write(" This is approximately a ")
    textFile.write(str.format(
        '{0:,.0f}', (DF_OG_VLN['bw_amt'].sum()/22000000000)*100))
    textFile.write("-percent sample of an estimated actual $22B annually in wage theft that occurs nationally (see https://blog.tsheets.com/2018/news/cost-of-wage-theft).</p>")

    textFile.write("\n")

    if TEST != 3:
        textFile.write(
            "<p>The Federal WHD data goes back to 2000, the State DLSE data goes back to 2000, and the City SJOE data goes back to 2011.</p>")

    '''
	textFile.write( "<p>Dataset date range: ")
	DF_MIN_OG = "<undefined>"
	if not df.empty:
		DF_MIN_OG = min(pd.to_datetime(DF_OG_ALL['findings_start_date'].dropna() ) )
		textFile.write( DF_MIN_OG.strftime("%m/%d/%Y") )
	textFile.write(" to ")
	DF_MAX_OG = "<undefined>"
	if not df.empty:
		DF_MAX_OG = max(pd.to_datetime(DF_OG_ALL['findings_start_date'].dropna() ) )
		textFile.write( DF_MAX_OG.strftime("%m/%d/%Y") )
	textFile.write("</p>")
	'''

    textFile.write("<p> These data are internally incomplete, and do not include private lawsuits, stop notices, and complaints to the awarding agency, contractor, employment department, licensing board, and district attorney. ")
    textFile.write(
        "Therefore, the following is a sample given the above data constraints and the reluctance by populations to file wage and hour claims.</p>")

    textFile.write("\n")

    textFile.write(
        "<p>Note that categorizations are based on both documented data and intelligent inferences, therefore, there are errors. ")
    textFile.write("For the fields used to prepare this report, please see https://docs.google.com/spreadsheets/d/19EPT9QlUgemOZBiGMrtwutbR8XyKwnrEhB5rZpZqM98/edit?usp=sharing . ")
    textFile.write(
        "And for the industry categories, which are given shortened names here, please see https://www.naics.com/search/ . ")
    textFile.write("To see a visualization of the data by zip code and industry, please see (last updated Feb 2020) https://public.tableau.com/profile/forest.peterson#!/vizhome/Santa_Clara_County_Wage_Theft/SantaClaraCounty . </p>")

    textFile.write("\n")
    textFile.write("\n")


def City_Summary_Block_4_Zipcode_and_Industry(df, df_max_check, TARGET_INDUSTRY, SUMMARY_SIG, filename):

    result = '''
	<html>
	<head>
	<style>

		h2 {
			text-align: center;
			font-family: Helvetica, Arial, sans-serif;
		}
		
	</style>
	</head>
	<body>
	'''

    # zip code = loop through
    df = df.reset_index(level=0, drop=True)  # drop city category

    #df = df.groupby(level=0)
    # df = df.agg({ #https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
    # 	"bw_amt":'sum',
    # 	"violtn_cnt":'sum',
    # 	"ee_violtd_cnt":'sum',
    # 	"ee_pmt_due": 'sum',
    # 	"records": 'sum',
    # 	}).reset_index().sort_values(["zip_cd"], ascending=True)
    zipcode = ""
    for zipcode, df_zipcode in df.groupby(level=0):  # .groupby(level=0):

        # print theft level in $ and employees
        test_num1 = pd.to_numeric(df_zipcode['bw_amt'].sum(), errors='coerce')
        test_num2 = pd.to_numeric(
            df_zipcode['ee_violtd_cnt'].sum(), errors='coerce')

        if test_num1 < 3000:
            # result +="<p> has no backwage data.</p>""
            dummy = ""  # just does nothing
        else:
            result += "<p>"
            result += "In the "
            result += str(zipcode) #10/26/2022 found bug "can only concatenate str (not "bool") to str"
            result += " zip code, "
            result += (str.format('{0:,.0f}', test_num2))
            if math.isclose(test_num2, 1.0, rel_tol=0.05, abs_tol=0.0):
                result += " worker suffered wage theft totaling $ "
            else:
                result += " workers suffered wage theft totaling $ "

            result += (str.format('{0:,.0f}', test_num1))
            result += " "

            # print the industry with highest theft

            # check df_max_check for industry with highest theft in this zip code
            df_zipcode = df_zipcode.reset_index(
                level=0, drop=True)  # drop zip code category
            df_zipcode = df_zipcode.groupby(level=0)

            df_zipcode = df_zipcode.agg({  # https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
                "bw_amt": 'sum',
                "violtn_cnt": 'sum',
                "ee_violtd_cnt": 'sum',
                "ee_pmt_recv": 'sum',
                "records": 'sum',
            }).reset_index().sort_values(["bw_amt"], ascending=False)

            # check df_max_check that industry in the top three for the County
            industry_list = len(TARGET_INDUSTRY)
            if industry_list > 2:
                result += ". The "
                result += df_zipcode.iloc[0, 0]
                result += " industry is one of the largest sources of theft in this zip code"
                # if math.isclose(df_zipcode.iloc[0,1], df_max_check['bw_amt'].max(), rel_tol=0.05, abs_tol=0.0):
                #result += " (this zip code has one of the highest levels of theft in this specific industry across the County)"
                # result += str.format('{0:,.0f}', df_zipcode.iloc[0,1])
                # result += "|"
                # result += str.format('{0:,.0f}', df_max_check['bw_amt'].max() )

            # note if this is the top 3 zip code for the county --> df_max_check
            # if test_num1 == df_max_check['bw_amt'].max():
            if math.isclose(test_num1, df_max_check['bw_amt'].max(), rel_tol=0.05, abs_tol=0.0):
                result += " (this zip code has one of the highest overall levels of theft in the County)."
                # result += str.format('{0:,.0f}', test_num1)
                # result += "|"
                # result += str.format('{0:,.0f}',df_max_check['bw_amt'].max() )
            else:
                result += ". "
            result += "</p>"
            result += ("\n")

    result += ("\n")
    result += ("\n")

    result += '''
		</body>
		</html>
		'''
    # with open(filename, mode='a') as f:
    with open(filename, mode='a', encoding="utf-8") as f:
        f.write(result)


def City_Summary_Block(city_cases, df, total_ee_violtd, total_bw_atp, total_case_violtn, unique_legalname, agency_df, cty_nm, SUMMARY_SIG, filename):

    result = '''
		<html>
		<head>
		<style>

			h2 {
				text-align: center;
				font-family: Helvetica, Arial, sans-serif;
			}
			
		</style>
		</head>
		<body>
		'''
    result += '\n'
    result += '<h2>'
    result += cty_nm
    result += ' CITY SUMMARY</h2>\n'

    # if not df.empty: #commented out 10/26/2020 to remove crash on findings_start_date
    # 	DF_MIN = min(pd.to_datetime(df['findings_start_date'].dropna(), errors = 'coerce' ) )
    # 	DF_MAX = max(pd.to_datetime(df['findings_start_date'].dropna(), errors = 'coerce' ) )
    # 	result += ( DF_MIN.strftime("%m/%d/%Y") )
    # 	result += (" to ")
    # 	result += ( DF_MAX.strftime("%m/%d/%Y") )
    # 	result += ("</p> \n")
    # else:
    # 	result += ( "<p>Actual date range: <undefined></p> \n")

    result += "<p>"
    test_num1 = pd.to_numeric(df['bw_amt'].sum(), errors='coerce')
    # if test_num1 > 3000:
    # 	result +="Wage theft is a concern in the City of "
    # 	result += cty_nm.title()
    # 	result +=". "

    if city_cases < 1:
        do_nothing = ""
        # result +="No wage theft cases were found in the City of "
        # result += cty_nm.title()
        # result +=". "
    elif math.isclose(city_cases, 1.0, rel_tol=0.05, abs_tol=0.0):
        result += "There is at least one wage theft case"
        if test_num1 <= 3000:
            result += " in the City of "
            result += cty_nm.title()
        result += ", "
    else:
        result += "There are "
        result += (str.format('{0:,.0f}', city_cases))
        result += " wage theft cases"
        if test_num1 <= 3000:
            result += " in the City of "
            result += cty_nm.title()
        result += ", "

    # total theft $
    #test_num1 = pd.to_numeric(df['bw_amt'].sum(), errors='coerce')
    if test_num1 < 1 and city_cases < 1:
        do_nothing = ""
        #result +=" and, there is no backwage data. "
    elif test_num1 < 1 and city_cases >= 1:
        result += " however, the backwage data is missing. "
    elif test_num1 > 3000:
        result += " resulting in a total of $ "
        result += (str.format('{0:,.0f}', test_num1))
        result += " in stolen wages. "
    else:
        result += " resulting in stolen wages. "

    # total unpaid theft $
    test_num0 = pd.to_numeric(df['ee_pmt_recv'].sum(), errors='coerce')
    if test_num0 < 1:
        do_nothing = ""
        #result +="Of that, an unknown amount is still due to the workers of this city. "
    else:
        result += ("Of that, $ ")
        result += (str.format('{0:,.0f}', test_num0))
        result += " has been returned to the workers of this city. "

    # total number of violations
    test_num2 = pd.to_numeric(df['ee_violtd_cnt'].sum(), errors='coerce')
    if test_num2 < 1:
        do_nothing = ""
        #result +="Therefore, there is no case evidence of workers affected by stolen wages. "
    else:
        test_num3 = pd.to_numeric(df['violtn_cnt'].sum(), errors='coerce')
        if math.isclose(test_num2, 1.0, rel_tol=0.05, abs_tol=0.0):
            result += "The theft comprises at least one discrete wage-and-hour violation "
        else:
            result += "The theft comprises "
            result += (str.format('{0:,.0f}', test_num3))
            result += " discrete wage-and-hour violations "

    if test_num2 < 1:
        do_nothing = ""
    elif math.isclose(test_num2, 1.0, rel_tol=0.05, abs_tol=0.0):
        result += "affecting at least one worker: "
    else:
        result += "affecting "
        result += (str.format('{0:,.0f}', test_num2))
        result += " workers: "

    # xx companies have multiple violations
    if len(unique_legalname.index) < 1:
        do_nothing = ""
        #result +="No employer was found with more than one case. "
    if math.isclose(len(unique_legalname.index), 1.0, rel_tol=0.05, abs_tol=0.0):
        result += "At least one employer has multiple cases. "
    else:
        result += (str.format('{0:,.0f}', len(unique_legalname.index)))
        result += " employers have multiple cases recorded against them. "

    # xx companies cited by multiple agencies
    if len(agency_df.index) < 1:
        #result +="No employer was found with cases from multiple agencies. "
        do_nothing = ""
    elif math.isclose(len(agency_df.index), 1.0, rel_tol=0.05, abs_tol=0.0):
        result += "at least one employer has cases from multiple agencies. "
    else:
        result += (str.format('{0:,.0f}', len(agency_df.index)))
        result += " employers have cases from multiple agencies. "

    # employer with top theft
    if test_num1 > 3000:
        # df = df.droplevel('legal_nm').copy()
        # df = df.reset_index()
        # df = df.groupby(['legal_nm']).agg({ #https://towardsdatascience.com/pandas-groupby-aggregate-transform-filter-c95ba3444bbb
        # 	"bw_amt":'sum',
        # 	"violtn_cnt":'sum',
        # 	"ee_violtd_cnt":'sum',
        # 	"ee_pmt_recv": 'sum',
        # 	"records": 'sum',
        # 	}).reset_index().sort_values(["bw_amt"], ascending=True)

        temp_row = unique_legalname.nlargest(
            3, 'backwage_owed').reset_index(drop=True)
        temp_value_1 = temp_row['backwage_owed'].iloc[0]
        if temp_row.size > 0 and temp_value_1 > 0:
            # indexNamesArr = temp_row.index.values[0] #https://thispointer.com/python-pandas-how-to-get-column-and-row-names-in-dataframe/
            #result += indexNamesArr.astype(str)
            result += temp_row['legal_nm'].iloc[0]
            result += " is the employer with the highest recorded theft in this city, "
            result += "it has unpaid wage theft claims of $ "
            result += (str.format('{0:,.0f}', temp_value_1))
            result += ". "

        result += "</p>"

        result += ("\n")
        result += ("\n")

    # close
    result += '''
		</body>
		</html>
		'''
    # with open(filename, mode='a') as f:
    with open(filename, mode='a', encoding="utf-8") as f:
        f.write(result)


def Regional_All_Industry_Summary_Block(out_counts, df, total_ee_violtd, total_bw_atp, total_case_violtn, unique_legalname, agency_df, OPEN_CASES, textFile):
    textFile.write("<h2>Summary for All Industries</h2> \n")

    if not df.empty:
        textFile.write(f"<p>Actual date range: ")
        DF_MIN = min(pd.to_datetime(
            df['findings_start_date'].dropna(), errors='coerce'))
        DF_MAX = max(pd.to_datetime(
            df['findings_start_date'].dropna(), errors='coerce'))
        textFile.write(DF_MIN.strftime("%m/%Y"))
        textFile.write(" to ")
        textFile.write(DF_MAX.strftime("%m/%Y"))
        textFile.write("</p> \n")
    else:
        textFile.write("<p>Actual date range: <undefined></p> \n")

    if OPEN_CASES == 1:
        textFile.write(
            "<p>This report has cases removed that are documented as closed or the amount repaid matches the backwages owed.</p> \n")

    if not len(out_counts.index) == 0:
        textFile.write("<p>Wage theft cases: ")
        textFile.write(str.format('{0:,.0f}', len(out_counts.index)))
        textFile.write("</p> \n")

    if not out_counts['wages_owed'].sum() == 0:
        textFile.write("<p>Total wage theft:  $ ")
        textFile.write(str.format(
            '{0:,.0f}', out_counts['wages_owed'].sum()))  # bw_amt
        if not df.empty:
            if total_ee_violtd == 0:
                textFile.write(
                    " <i> Note: Backwages per employee violated is not calculated in this report</i></p> \n")
            else:
                textFile.write(" <i>(gaps estimated as $")
                textFile.write(str.format(
                    '{0:,.0f}', total_bw_atp//total_ee_violtd))
                textFile.write(
                    " in backwages per employee violated--plus interest and penalties)</i> \n")
        textFile.write("</p>")

    if not out_counts['backwage_owed'].sum() == 0:
        textFile.write(
            "<p>Including monetary penalties and accrued interest, the amount owed is:  $ ")
        textFile.write(str.format(
            '{0:,.0f}', out_counts['backwage_owed'].sum()))  # bw_amt
        textFile.write("</p>")

    # if not out_counts['ee_pmt_due'].sum()==0:
    # 	textFile.write("<p>Total unpaid wage theft:  $ ")
    # 	textFile.write(str.format('{0:,.0f}',out_counts['ee_pmt_due'].sum() ) )
    # 	textFile.write("</p>")

    # text_sum_bug_fix = out_counts['ee_pmt_recv'].sum()
    # if not text_sum_bug_fix==0:
    # 	textFile.write("<p>Total paid wage theft:  $ ")
    # 	textFile.write(str.format('{0:,.0f}',text_sum_bug_fix ) )
    # 	textFile.write("</p>")

    if not out_counts['ee_violtd_cnt'].sum() == 0:
        textFile.write("<p>Total employees: ")
        textFile.write(str.format(
            '{0:,.0f}', out_counts['ee_violtd_cnt'].sum()))
        textFile.write("</p> \n")

    if not out_counts['violtn_cnt'].sum() == 0:
        textFile.write("<p>Total violations: ")
        textFile.write(str.format('{0:,.0f}', out_counts['violtn_cnt'].sum()))
        if not df.empty:
            if total_ee_violtd == 0:
                textFile.write(
                    " <i> Note: Violations per employee is not calculated in this report</i></p> \n")
            else:
                textFile.write(" <i>(gaps estimated as ")
                textFile.write(str.format(
                    '{0:,.2g}', total_case_violtn//total_ee_violtd))
                textFile.write(" violation(s) per employee violated)</i>")
        textFile.write("</p>")

    textFile.write("\n")
    textFile.write("\n")

    textFile.write("<p>Companies that are involved in multiple cases: ")
    textFile.write(str.format('{0:,.0f}', len(unique_legalname.index)))  # here
    textFile.write("</p> \n")

    if not len(agency_df.index) == 0:
        textFile.write("<p>Companies that are cited by multiple agencies: ")
        textFile.write(str.format('{0:,.0f}', len(agency_df.index)))  # here
        textFile.write("</p> \n")

    textFile.write("\n")
    textFile.write("\n")


def Industry_Summary_Block(out_counts, df, total_ee_violtd, total_bw_atp, total_case_violtn, unique_legalname, agency_df, OPEN_CASES, textFile):
    textFile.write("<h2>Summary for Reported Industry</h2> \n")

    if not df.empty:
        #textFile.write(f"<p>Date range: {YEAR_START} to {YEAR_END}</p>")

        # commented out due to out of bounds date that need an error check to fix debug 10/26/2020 Fixed 2/5/2022
        DF_MIN = min(pd.to_datetime(
            df['findings_start_date'].dropna(), errors='coerce'))
        DF_MAX = max(pd.to_datetime(
            df['findings_start_date'].dropna(), errors='coerce'))

        textFile.write(f"<p>Actual date range: ")
        #textFile.write( DF_MIN.strftime("%m/%d/%Y") )
        textFile.write(DF_MIN.strftime("%m/%Y"))
        textFile.write(" to ")
        #textFile.write( DF_MAX.strftime("%m/%d/%Y") )
        textFile.write(DF_MAX.strftime("%m/%Y"))
        textFile.write("</p> \n")
    else:
        textFile.write("<p>Actual date range: <undefined></p> \n")

    if OPEN_CASES == 1:
        textFile.write(
            "<p>This report has cases removed that are documented as closed or the amount repaid matches the backwages owed.</p> \n")

    if not len(out_counts.index) == 0:
        textFile.write("<p>Wage theft cases: ")
        textFile.write(str.format('{0:,.0f}', len(out_counts.index)))
        textFile.write("</p> \n")

    if not out_counts['bw_amt'].sum() == 0:
        textFile.write("<p>Total wage theft:  $ ")
        textFile.write(str.format('{0:,.0f}', out_counts['bw_amt'].sum()))
        if not df.empty:
            if total_ee_violtd == 0:
                textFile.write(
                    " <i> Note: Backwages per employee violated is not calulated in this report</i></p> \n")
            else:
                textFile.write(" <i>(gaps estimated as $")
                textFile.write(str.format(
                    '{0:,.0f}', total_bw_atp//total_ee_violtd))
                textFile.write(" in backwages per employee violated)</i> \n")
        textFile.write("</p>")

    # if not out_counts['ee_pmt_due'].sum()==0:
    # 	textFile.write("<p>Total unpaid wage theft:  $ ")
    # 	textFile.write(str.format('{0:,.0f}',out_counts['ee_pmt_due'].sum() ) )
    # 	textFile.write("</p>")

    # text_sum_bug_fix = out_counts['ee_pmt_recv'].sum()
    # if not text_sum_bug_fix==0:
    # 	textFile.write("<p>Total paid wage theft:  $ ")
    # 	textFile.write(str.format('{0:,.0f}',text_sum_bug_fix ) )
    # 	textFile.write("</p>")

    if not out_counts['ee_violtd_cnt'].sum() == 0:
        textFile.write("<p>Total employees: ")
        textFile.write(str.format(
            '{0:,.0f}', out_counts['ee_violtd_cnt'].sum()))
        textFile.write("</p> \n")

    if not out_counts['violtn_cnt'].sum() == 0:
        textFile.write("<p>Total violations: ")
        textFile.write(str.format('{0:,.0f}', out_counts['violtn_cnt'].sum()))
        if not df.empty:
            if total_ee_violtd == 0:
                textFile.write(
                    " <i> Note: Violations per employee is not calculated in this report</i></p> \n")
            else:
                textFile.write(" <i>(gaps estimated as ")
                textFile.write(str.format(
                    '{0:,.2g}', total_case_violtn//total_ee_violtd))
                textFile.write(" violation(s) per employee violated)</i>")
        textFile.write("</p>")

    textFile.write("\n")
    textFile.write("\n")

    textFile.write("<p>Companies that are involved in multiple cases: ")
    textFile.write(str.format('{0:,.0f}', len(unique_legalname.index)))  # here
    textFile.write("</p> \n")

    if not len(agency_df.index) == 0:
        textFile.write("<p>Companies that are cited by multiple agencies: ")
        textFile.write(str.format('{0:,.0f}', len(agency_df.index)))  # here
        textFile.write("</p> \n")

    textFile.write("\n")
    textFile.write("\n")


def Notes_Block(textFile, default_zipcode="####X"):

    textFile.write("<p>Notes: ")
    textFile.write(
        f"(1) In the following tables and city summaries, the zip {default_zipcode} represents data that is missing the zip code field. ")
    textFile.write("(2) There are unlabeled industries, many of these are actually construction, care homes, restaurants, etc. just there is not an ability to label them as such--a label of 'other' could lead one to indicate that they are not these industries and therefore the category of 'uncategorized.' ")
    textFile.write("(3) Values may deviate by 10% within the report for camparable subcategories: this is due to labeling and relabeling of industry that may overwrite a previous industry label (for example Nail Hamburger could be labeled service or food). ")
    textFile.write("</p>")

    textFile.write("\n")
    textFile.write("\n")


def Methods_Block(textFile):
    textFile.write("<p>")
    textFile.write("Methods: ")
    textFile.write("</p>")

    textFile.write("<p>")
    textFile.write("backwage_owed:")
    textFile.write("</p>")
    textFile.write("<ul>")
    textFile.write(
        "<li>the sum of wages owed, monetary penalty, and interest</li>")
    textFile.write(
        "<li>df['backwage_owed'] = df['wages_owed'] + df['cmp_assd_cnt'] + df['interest_owed']</li>")
    textFile.write("</ul>")

    textFile.write("<p>")
    textFile.write("wages_owed: ")
    textFile.write("</p>")
    textFile.write("<ul>")
    textFile.write(
        "<li>unpaid backwages less payment recieved by employee</li>")
    textFile.write(
        "<li>df['wages_owed'] = df['bw_amt'] - df['ee_pmt_recv']</li>")
    textFile.write("</ul>")

    textFile.write("<p>")
    textFile.write("interest_owed: ")
    textFile.write("</p>")
    textFile.write("<ul>")
    textFile.write("<li>interestd due less interest payments recieved</li>")
    textFile.write(
        "<li>df['interest_owed'] = df['Interest_Balance_Due'] - df['Interest_Payments_Recd])</li>")
    textFile.write("</ul>")

    textFile.write("<p>")
    textFile.write("Interest_Balance_Due: ")
    textFile.write("</p>")
    textFile.write("<ul>")
    textFile.write(
        "<li>where interest balance due is missing, then infer an interest balance based on a calaculated compounded interest of the backwages owed</li>")
    textFile.write(
        "<li>df['Interest_Balance_Due'] = np.where(df['Interest_Balance_Due'] == "", df['Interest_Accrued'], df['Interest_Balance_Due']</li>")
    textFile.write(
        "<li>df['Interest_Accrued'] = (df['wages_owed'] * (((1 + ((r/100.0)/n)) ** (n*df['Years_Unpaid']))) ) - df['wages_owed']</li>")
    textFile.write("</ul>")

    # textFile.write("bw_amt: ")
    # textFile.write("<li> </li>")
    # textFile.write("violtn_cnt: ")
    # textFile.write("<li> </li>")
    # textFile.write("ee_violtd_cnt: ")
    # textFile.write("<li> </li>")
    # textFile.write("ee_pmt_recv: ")
    # textFile.write("<li> </li>")
    # textFile.write("records: ")
    # textFile.write("<li> </li>")
    textFile.write("</p>")

    textFile.write("\n")
    textFile.write("\n")


def Signatory_to_Nonsignatory_Block(df1, df2, filename):
    # construction
    # medical

    # ratio_construction = df1.query(
    # 	"signatory_industry == 'construction_signatories' and signatory_industry == 'signatories_UCON' and signatory_industry == 'signatories_CEA' "
    # 	)['bw_amt'].sum() / df1['bw_amt'].sum()

    ratio_construction_ = df1.loc[df1['signatory_industry']
                                  == 'Construction', 'backwage_owed'].sum()
    #ratio_construction_ucon = df1.loc[df1['signatory_industry'] == 'Construction','backwage_owed'].sum()
    #ratio_construction_cea = df1.loc[df1['signatory_industry'] == 'Construction','backwage_owed'].sum()
    construction_industry_backwage = df1.loc[df1['industry']
                                             == 'Construction', 'backwage_owed'].sum()
    ratio_construction = (ratio_construction_) / construction_industry_backwage

    ratio_hospital_ = df1.loc[df1['signatory_industry']
                              == 'Health_care', 'backwage_owed'].sum()
    carehome_industry_backwage = df1.loc[df1['industry']
                                         == 'Carehome', 'backwage_owed'].sum()
    healthcare_industry_backwage = df1.loc[df1['industry']
                                           == 'Health_care', 'backwage_owed'].sum()
    residential_carehome_industry_backwage = df1.loc[df1['industry']
                                                     == 'Residential_carehome', 'backwage_owed'].sum()
    ratio_hospital = ratio_hospital_ / \
        (carehome_industry_backwage + healthcare_industry_backwage +
         residential_carehome_industry_backwage)

    filename.write("<p>")
    filename.write("Of $ ")
    filename.write(str.format('{0:,.0f}', df1['backwage_owed'].sum()))
    filename.write(
        " in all industry back wages owed (inc. monetary penalty and interest), ")
    filename.write(" union signatory employers represent: </p>")
    filename.write("<p>")
    filename.write(str.format('{0:,.0f}', ratio_construction * 100))
    filename.write(
        " percent of total documented theft in the construction industry with $ ")
    filename.write(str.format('{0:,.0f}', (ratio_construction_)))
    filename.write(" of $ ")
    filename.write(str.format('{0:,.0f}', construction_industry_backwage))
    filename.write(" in construction specific backwages. ")
    filename.write("</p>")
    filename.write("<p>")
    filename.write(str.format('{0:,.0f}', ratio_hospital * 100))
    filename.write(
        " percent of total documented theft in the healthcare industry with $ ")
    filename.write(str.format('{0:,.0f}', ratio_hospital_))
    filename.write(" of $ ")
    filename.write(str.format('{0:,.0f}', (carehome_industry_backwage +
                                           healthcare_industry_backwage + residential_carehome_industry_backwage)))
    filename.write(" in healthcare specific backwages. ")
    filename.write("</p>")
    filename.write("<p> Due to the situation of the union worker as fairly paid, educated in labor rights, and represented both in bargaining and enforcement of that bargained for agreement--as well as that these are two heavily unionized industries and that much of the non-union data is lost as undefined industry--then these percentages are likely overly represented as union workers would know how and when to bring a wage and hour case. As such, it is fair to conclude that there effectively is no concernable degree of wage theft in the unionized workforce that requires outside enforcement. </p>")


def Footer_Block(TEST, textFile):
    textFile.write("<p>Prepared by the Stanford University Center for Integrated Facility Engineering (CIFE) in collaboration with the Santa Clara County Wage Theft Coalition. These data have not been audited and, therefore, are only intended as an indication of wage theft.</p> \n")

    textFile.write("<p> Report generated ")
    textFile.write(pd.to_datetime('today').strftime("%m/%d/%Y"))
    textFile.write("</p>")

#write_to_html_file(new_df_3, header_HTML_EMP3, "", file_path('py_output/A4W_Summary_by_Emp_for_all2.html') )


# https://stackoverflow.com/questions/47704441/applying-styling-to-pandas-dataframe-saved-to-html-file
def write_to_html_file(df, header_HTML, title, filename):
    # added this line to avoid error 8/10/2022 f. peterson
    import pandas.io.formats.style
    import os  # added this line to avoid error 8/10/2022 f. peterso

    result = '''
		<html>
		<head>
		<style>

			h2 {
				text-align: center;
				font-family: Helvetica, Arial, sans-serif;
			}
			table { 
				margin-left: auto;
				margin-right: auto;
			}
			table, th, td {
				border: 1px solid black;
				border-collapse: collapse;
			}
			th, td {
				padding: 5px;
				text-align: center;
				font-family: Helvetica, Arial, sans-serif;
				font-size: 90%;
			}
			table tbody tr:hover {
				background-color: #dddddd;
			}
			.wide {
				width: 90%; 
			}

		</style>
		</head>
		<body>
		'''
    result += '<h2> %s </h2>\n' % title
    if type(df) == pd.io.formats.style.Styler:
        result += df.render()
    else:
        result += df.to_html(classes='wide', columns=header_HTML, escape=False)
    result += '''
		</body>
		</html>
		'''
    # with open(filename, mode='a') as f:
    # added this line to avoid error 8/10/2022 f. peterson
    # create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # https://stackoverflow.com/questions/27092833/unicodeencodeerror-charmap-codec-cant-encode-characters
    with open(filename, mode='a', encoding="utf-8") as f:
        f.write(result)

def append_log(bug_log, LOGBUG, text):
    if LOGBUG:
        bugFile = open(bug_log, 'a')
        bugFile.write(text)
        bugFile.close()
        print(text)

def debug_fileSetup_def(bug_filename):

    bug_filename.write("<!DOCTYPE html>")
    bug_filename.write("\n")
    bug_filename.write("<html><body>")
    bug_filename.write("\n")

    bug_filename.write("<h1>START</h1>")
    bug_filename.write("\n")


def file_path(relative_path):
    if os.path.isabs(relative_path):
        return relative_path
    dir = os.path.dirname(os.path.abspath(__file__))
    split_path = relative_path.split("/")
    new_path = os.path.join(dir, *split_path)
    return new_path


if __name__ == '__main__':
    main()
