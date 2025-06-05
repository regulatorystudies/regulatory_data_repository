#----------------------------------Analysis of Fall 2024 Unified Agenda----------------------------------------------#

import pandas as pd
import os
from lxml import etree
import numpy as np
import requests
import re
pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', 10)
import datetime
from bs4 import BeautifulSoup
import inflect

import warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['font.family'] = "Times New Roman"

#%% Define administrations and their start & end years
# If there is a new administration, add {president name: [start year, end year]} to the dictionary below.
admin_year = {'Clinton': [1993, 2001],
              'Bush 43': [2001, 2009],
              'Obama': [2009, 2017],
              'Trump 45': [2017, 2021],
              'Biden': [2021, 2025],
              'Trump 47': [2025, 2029]}

#%% Set directory
# directory="unified_agenda_data"
directory='/Users/sayam_palrecha/my_project/GW_Regulatory/Regulatory_data/Data Analysis'

#%% Create subdirectories if not exist
folder_path1=f"{directory}/raw_data"
if not os.path.exists(folder_path1):
    os.makedirs(folder_path1)

folder_path1=f"{directory}/output"
if not os.path.exists(folder_path1):
    os.makedirs(folder_path1)

#%% Function to convert date
def convert_date(str):
    month=str.split('/')[0]
    if month.isdigit():
        year=str.split('/')[2]
        return datetime.datetime(int(year), int(month), 1)
    else:
        return None

#-----------------------------------------------------------------------------------------------------------------------
#%% Function to load XML reports
def import_xml(file,year,midnight=0):
    df_xml = pd.DataFrame()
    parser = etree.XMLParser(encoding="UTF-8", recover=True)
    parsed_xml = etree.parse(file, parser)  # prevent form issue
    root = parsed_xml.getroot()
    row=0
    for child in root:
        df_xml.at[row, 'publication_date']=child.find('PUBLICATION')[0].text
        df_xml.at[row, 'RIN']=child.find('RIN').text
        if child.find('AGENCY') != None:
            df_xml.at[row, 'agency_code']=child.find('AGENCY')[0].text
            if child.find('AGENCY').find('NAME') != None:
                df_xml.at[row, 'agency_name']=child.find('AGENCY').find('NAME').text
        if child.find('PARENT_AGENCY')!=None:
            df_xml.at[row, 'department_code']=child.find('PARENT_AGENCY')[0].text
            df_xml.at[row, 'department_name']=child.find('PARENT_AGENCY')[1].text
        df_xml.at[row, 'rule_title'] = child.find('RULE_TITLE').text
        df_xml.at[row, 'abstract']=child.find('ABSTRACT').text
        if child.find('PRIORITY_CATEGORY')!=None:
            df_xml.at[row, 'priority']=child.find('PRIORITY_CATEGORY').text
        if child.find('RIN_STATUS')!=None:
            df_xml.at[row, 'RIN_status']=child.find('RIN_STATUS').text
        if child.find('RULE_STAGE')!=None:
            df_xml.at[row, 'rule_stage']=child.find('RULE_STAGE').text
        if child.find('MAJOR')!=None:
            df_xml.at[row, 'major']=child.find('MAJOR').text
        else:
            df_xml.at[row, 'major']=None

        if child.find('CFR_LIST')!=None:
            index=0
            text=''
            while (index<len(list(child.find('CFR_LIST')))):
                add=child.find('CFR_LIST')[index].text
                if text=='':
                    text=add
                else:
                    text=text+"; "+str(add)
                index=index+1
            df_xml.at[row, 'CFR'] = text

        if child.find('LEGAL_AUTHORITY_LIST')!=None:
            index=0
            text=''
            while (index<len(list(child.find('LEGAL_AUTHORITY_LIST')))):
                add=child.find('LEGAL_AUTHORITY_LIST')[index].text
                if text=='':
                    text=add
                else:
                    text=text+"; "+str(add)
                index=index+1
            df_xml.at[row, 'legal_authority']=text

        # # Extract all actions in the timetable
        # if child.find('TIMETABLE_LIST')!=None:
        #     index=0
        #     while (index<len(list(child.find('TIMETABLE_LIST')))):
        #         colname='action_date_FR'+str(index+1)
        #         if child.find('TIMETABLE_LIST')[index].find('FR_CITATION')!=None:
        #             df_xml.at[row, colname]=child.find('TIMETABLE_LIST')[index][0].text+'; '+child.find('TIMETABLE_LIST')[index][1].text+'; '+child.find('TIMETABLE_LIST')[index][2].text
        #         else:
        #             if child.find('TIMETABLE_LIST')[index].find('TTBL_DATE')!=None:
        #                 df_xml.at[row, colname] = child.find('TIMETABLE_LIST')[index][0].text + '; ' + \
        #                                        child.find('TIMETABLE_LIST')[index][1].text
        #             else:
        #                 df_xml.at[row, colname] = child.find('TIMETABLE_LIST')[index][0].text
        #         index=index+1

        # # Extract the last action in the timetable
        # if child.find('TIMETABLE_LIST')!=None:
        #     index=-1
        #     if child.find('TIMETABLE_LIST')[index].find('FR_CITATION')!=None:
        #         df_xml.at[row, 'action_type']=child.find('TIMETABLE_LIST')[index][0].text
        #         df_xml.at[row, 'action_date'] = child.find('TIMETABLE_LIST')[index][1].text
        #         df_xml.at[row, 'fr_citation'] = child.find('TIMETABLE_LIST')[index][2].text
        #     else:
        #         if child.find('TIMETABLE_LIST')[index].find('TTBL_DATE')!=None:
        #             df_xml.at[row, 'action_type'] = child.find('TIMETABLE_LIST')[index][0].text
        #             df_xml.at[row, 'action_date'] = child.find('TIMETABLE_LIST')[index][1].text
        #         else:
        #             df_xml.at[row, 'action_type'] = child.find('TIMETABLE_LIST')[index][0].text

        # Extract potential might actions
        if midnight==1:
            if child.find('TIMETABLE_LIST')!=None:
                for index in range(len(list(child.find('TIMETABLE_LIST')))):
                    if child.find('TIMETABLE_LIST')[index].find('FR_CITATION')!=None:
                        action_type=child.find('TIMETABLE_LIST')[index][0].text
                        action_date = child.find('TIMETABLE_LIST')[index][1].text
                        fr_citation = child.find('TIMETABLE_LIST')[index][2].text
                    else:
                        if child.find('TIMETABLE_LIST')[index].find('TTBL_DATE')!=None:
                            action_type = child.find('TIMETABLE_LIST')[index][0].text
                            action_date = child.find('TIMETABLE_LIST')[index][1].text
                            fr_citation = None
                        else:
                            action_type = child.find('TIMETABLE_LIST')[index][0].text
                            action_date = fr_citation = None

                    if convert_date(action_date)!=None:
                        if convert_date(action_date)>datetime.datetime(year,11,30):
                            break
                        else:
                            pass
                    else:
                        pass

                df_xml.at[row, 'action_type']=action_type
                df_xml.at[row, 'action_date'] = action_date
                df_xml.at[row, 'fr_citation'] = fr_citation

        row=row+1
    return df_xml

#%% Function to download an XML file
def download_file(year, season_no='10'):
    if year == 2012:
        file_name = f'REGINFO_RIN_DATA_{year}.xml'
        file_url = f'https://www.reginfo.gov/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_{year}.xml'
    else:
        file_name = f'REGINFO_RIN_DATA_{year}{season_no}.xml'
        file_url = f'https://www.reginfo.gov/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_{year}{season_no}.xml'

    file_path = f'{directory}/raw_data/{file_name}'

    try:
        if not os.path.exists(file_path):
            r = requests.get(file_url, allow_redirects=True)
            open(file_path, 'wb').write(r.content)
            print(f'{file_name} has been downloaded.')
        else:
            print(f'{file_name} already exists in the directory.')

        return file_path

    except:
        print(f'ERROR: {file_name} cannot be downloaded.')

#%% Function to save an agenda as excel
def import_excel(year,season='fall',midnight=0):
    season_no='04' if season=='spring' else '10'
    excel_path=f'{directory}/raw_data/Unified Agenda {year}{season_no}.xlsx'
    if not os.path.exists(excel_path):
        file_path=download_file(year,season_no)
        print('Converting XML to Dataframe...')
        df = import_xml(file_path,year,midnight)
        fr_cols = [col for col in df if col.startswith('action')]
        la_cols=[col for col in df if col.startswith('legal_deadline')]
        df = df[['publication_date', 'RIN', 'rule_title', 'agency_code', 'agency_name', 'department_code',
                           'department_name', 'abstract', 'priority', 'major', 'RIN_status', 'rule_stage', 'CFR']
                            + la_cols + fr_cols]
        df.to_excel(excel_path, index=False)
        # print(f'Unified Agenda {year}{season_no}.xlsx has been saved.')
    else:
        df=pd.read_excel(excel_path)

    return df

#%% Request user input on which agenda to analyze
# Fetch the latest year & season from Reginfo.gov
# Make a request
page = requests.get("https://www.reginfo.gov/public/do/eAgendaXmlReport")
soup = BeautifulSoup(page.content, 'html.parser')

# Extract the newest file information
newest_file_info = soup.select('li')[0].text[1:-6]

# Fetch the newest year and season
current_year_season = re.split("\s", newest_file_info, 1) #list
current_year = int(current_year_season[1]) # int
current_season = current_year_season[0] # str
current_season = current_season.lower()

#%% Check year & season input
# Function to input year
def input_year(year_type='year'):
    year_range = range(1995, current_year + 1)
    while True:
        year=int(input(f'Please enter the {year_type} of the Unified Agenda you are analyzing (e.g. 2024): '))
        if year in year_range:
            return year
            break
        else:
            print(f'ERROR: Your input year {year} is not in the valid time range.')

# Function to input season
def input_season():
    sea_option = ['spring','fall']
    while True:
        season=input(f'Please enter the season of the Agenda ("spring" or "fall"): ').lower()
        if season in sea_option:
            return season
            break
        else:
            print(f'ERROR: Your input season "{season}" is not valid.')

# Function to restrict season input depending on the year
def restrict_season(year):
    if year == 1995:
        season = 'fall'
        print(f'Only fall agenda is available for {year}.')
    elif year == 2012:
        season = 'fall'
        print(f'Only one agenda was published in {year}.')
    elif year == current_year:
        if current_season == 'spring':
            season = 'spring'
            print(f'The most recent Unified Agenda is {current_season.title()} {current_year}')
        else:
            season = input_season()
    else:
        season = input_season()
    return season

#%% Get user input and run the main function
# User input
print(f'The Unified Agenda data are available from Fall 1995 through {current_season.title()} {current_year}.\n')
print(f'To analyze data, please enter the year and season range between Fall 1995 and {current_season.title()} {current_year}.')

# Input start year
agenda_year=input_year()
agenda_season = restrict_season(agenda_year)

#%% Determine if the agenda is a midnight agenda
if (agenda_year in [years[1]-1 for years in admin_year.values()]) and (agenda_season=='fall'):
    agenda_midnight=1
else:
    agenda_midnight=0

#%% Import Current Agenda
df=import_excel(agenda_year,agenda_season,agenda_midnight)
print(df.info())

#-----------------------------------------------------------------------------------------------------------------------
#%% Contents of the agenda
# print(df['publication_date'].value_counts())

# Total
print('Total # of actions:',len(df))
print("Actions by",df['priority'].value_counts(),"\n")
print("Actions by",df['RIN_status'].value_counts(),"\n")
# print("Actions by",df['rule_stage'].value_counts(),"\n")

#%% By Stage
def convert_stage(df):
    df.loc[df['rule_stage'] == 'Completed Actions', 'stage'] = 'Completed Actions'
    df.loc[df['rule_stage'] == 'Long-Term Actions', 'stage'] = 'Long-Term Actions'
    df.loc[(df['rule_stage'] != 'Long-Term Actions') & (df['rule_stage'] != 'Completed Actions'),
                'stage'] = 'Active Actions'
    return df

df=convert_stage(df)
print("Actions by rulemaking",df['stage'].value_counts(),"\n")

#%% By stage & priority/rin_status
print('Active actions by', df[df['stage']=='Active Actions']['priority'].value_counts(),'\n')
print('Active actions by', df[df['stage']=='Active Actions']['RIN_status'].value_counts(),'\n')

print('Long-term actions by',df[df['stage']=='Long-Term Actions']['priority'].value_counts(),'\n')
print('Long-term actions by',df[df['stage']=='Long-Term Actions']['RIN_status'].value_counts(),'\n')

print('Completed actions by',df[df['stage']=='Completed Actions']['priority'].value_counts(),'\n')
print('Completed actions by',df[df['stage']=='Completed Actions']['RIN_status'].value_counts(),'\n')

#%% Economically significant actions
print('Economically significant actions by',df[(df['priority']=='Economically Significant') |
                                          (df['priority']=='Section 3(f)(1) Significant')]['stage'].value_counts(),'\n')
print('Economically significant actions by',df[(df['priority']=='Economically Significant') |
                                          (df['priority']=='Section 3(f)(1) Significant')]['RIN_status'].value_counts(),'\n')

print('Active economically significant actions by',
      df[((df['priority']=='Economically Significant') | (df['priority']=='Section 3(f)(1) Significant')) &
         (df['stage']=='Active Actions')]['RIN_status'].value_counts(),'\n')

print('First time published actions by',df[df['RIN_status']=='First Time Published in The Unified Agenda']['stage'].value_counts(),'\n')

#%% First Time Published & Completed Actions
df_temp=df[(df['RIN_status']=='First Time Published in The Unified Agenda') & (df['stage']=='Completed Actions')].reset_index(drop=True)

#%% Next action date in datetime format
if agenda_midnight==1:
    df['action_date2']=df['action_date'].apply(convert_date)

    # Active ES actions
    df_es = df[((df['priority'] == 'Economically Significant') | (df['priority'] == 'Section 3(f)(1) Significant')) & \
               (df['stage'] == 'Active Actions')].reset_index(drop=True)

    # Potential midnight regulations
    df_es['midnight'] = 0
    df_es.loc[(df_es['action_date2'] < datetime.datetime(agenda_year+1, 2, 1)) &
              (df_es['action_date2'] > datetime.datetime(agenda_year, 11, 30)), 'midnight'] = 1
    # print(df_es['midnight'].value_counts())
    # print(df_es[df_es['midnight'] == 1]['action_type'].value_counts(dropna=False))

    # Adjust midnight designation
    type_excl = ['NPRM Comment Period End', 'Analyzing Comments', 'Next Action Undetermined',
                 'Notice', 'Analyze Stakeholder Comments', 'NPRM Comment Period Extended End',
                 'Final Rule Effective', 'Informal Public Hearing (11/12/2024)']
    df_es.loc[df_es['action_type'].isin(type_excl), 'midnight'] = 0
    print("Potential midnight actions:", len(df_es[df_es['midnight']==1]),"\n")
    print("Potential midnight actions by",df_es[df_es['midnight'] == 1]['action_type'].value_counts())

else:
    # Active ES actions
    df_es = df[((df['priority'] == 'Economically Significant') | (df['priority'] == 'Section 3(f)(1) Significant')) & \
               (df['stage'] == 'Active Actions')].reset_index(drop=True)

#%% Agency & Department
# print(df['agency_name'].value_counts())
# print(df['department_name'].value_counts())

# replace with agency name if department name is None
# df['department_name'].fillna(df['agency_name'], inplace=True)
df.loc[df['department_name'].isnull(),'department_name']=df['agency_name']
df_es.loc[df_es['department_name'].isnull(),'department_name']=df_es['agency_name']

print("Active economically significant actions by",
         df[((df['priority']=='Economically Significant') | (df['priority']=='Section 3(f)(1) Significant')) & \
         (df['stage']=='Active Actions')]['department_name'].value_counts(dropna=False))

#%% Active ES actions by agency
df_es_agency=df_es['department_name'].value_counts(dropna=False).reset_index()
# print(sum(df_es_agency['count']))

# Active ES midnight actions by agency
if agenda_midnight==1:
    df_es_mid=df_es[df_es['midnight']==1]['department_name'].value_counts(dropna=False).reset_index()
    # print(sum(df_es_mid['count']))

    # Merge
    df_es_agency=df_es_agency.merge(df_es_mid,on='department_name',how='left',suffixes=('_total', '_midnight'))
    df_es_agency.rename(columns={'index':'department_name'},inplace=True)
    df_es_agency['count_midnight']=df_es_agency['count_midnight'].fillna(0)
    df_es_agency['count_non_midnight']=df_es_agency['count_total']-df_es_agency['count_midnight']

else:
    df_es_agency.rename(columns={'count':'count_total'},inplace=True)

#%% Top 10 agencies
# Agency dictionary (update this if a top agency is not included)
agency_dict={'Department of Health and Human Services':'HHS',
             'Department of the Treasury':'TREAS',
             'Small Business Administration':'SBA',
             'Department of Labor':'DOL',
             'Environmental Protection Agency':'EPA',
             'Department of Transportation':'DOT',
             'Department of Education':'ED',
             'Department of Energy':'DOE',
             'Department of Homeland Security':'DHS',
             'Department of Veterans Affairs':'VA',
             'Department of Agriculture':'USDA',
             'Department of the Interior':'DOI',
             'Nuclear Regulatory Commission':'NRC',
             'Departmetn of Justice':'DOJ'}

df_es_agency=df_es_agency[0:10]
df_es_agency['department_acronym']=[agency_dict[i] for i in df_es_agency['department_name']]
print('Active economically significant actions published by top 10 agencies:',sum(df_es_agency['count_total']))

if agenda_midnight==1:
    print('Potential midnight economically significant actions published by top 10 agencies:',sum(df_es_agency['count_midnight']))

#%% Create a bar plot by agency
fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.bar(df_es_agency['department_acronym'], df_es_agency['count_total'], color='#033C5A',
        width=0.5)
ax.bar_label(bars)

ax.set_ylabel("Number of Actions",fontsize=12)
ax.set_title(f"Active Economically Significant Actions in the {agenda_season.capitalize()} {agenda_year}\nUnified Agenda for Select Agencies",
             fontsize=16)

ax.tick_params(axis='both',which='major',labelsize=12,color='#d3d3d3')

# Borders
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3')
ax.spines['bottom'].set_color('#d3d3d3')

plt.savefig(f'{directory}/output/Active Economically Significant Actions by Agency.jpg', bbox_inches='tight')
plt.close()

#%% Prepare for a stacked bar for midnight actions by agency
if agenda_midnight==1:
    df_es_agency=df_es_agency[['department_acronym','count_midnight','count_non_midnight']].set_index('department_acronym')
    df_es_agency.loc[df_es_agency['count_non_midnight']==0,'count_non_midnight']=np.nan
    df_es_agency.rename(columns={'count_midnight':f'Proposed or Final Rule Expected in Dec {agenda_year} or Jan {agenda_year+1}',
                          'count_non_midnight':f'Next Rulemaking Action Expected After Jan {agenda_year+1}'},inplace=True)

    # Create a stacked bar
    ax = df_es_agency.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#0190DB','#033C5A'])

    for c in ax.containers:
        # ax.bar_label(c, fmt=lambda x: int(x) if x>0 else '', label_type='center',color='white', fontsize=10)
        # ax.bar_label(c, label_type='center', color='white', fontsize=10)
        labels=[int(x) if x>0 else '' for x in c.datavalues]
        ax.bar_label(c, labels=labels, label_type='center', color='white', fontsize=10)

    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=1, fontsize=14)
    ax.set_ylabel('Number of Actions', fontsize=12)
    ax.set_xlabel('')
    ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
    ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
    ax.set_title(f"Active Economically Significant Actions in the {agenda_season.capitalize()} {agenda_year}\nUnified Agenda for Select Agencies",
                 fontsize=18)

    # Borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d3d3d3')
    ax.spines['bottom'].set_color('#d3d3d3')

    plt.savefig(f'{directory}/output/Active Economically Significant Actions with Midnight Status by Agency.jpg', bbox_inches='tight')
    plt.close()

#%% Export a list of potential midnight regulations
if agenda_midnight==1:
    # Function to remove html tags
    CLEANR = re.compile('<.*?>')
    def remove_html(str):
        cleantext = re.sub(CLEANR, '', str)
        return cleantext.strip()

    df_midnight=df_es[df_es['midnight']==1].reset_index(drop=True)
    print('Potential economically significant midnight actions by',df_midnight['rule_stage'].value_counts())

    # df_midnight=df_midnight[df_midnight['rule_stage']=='Final Rule Stage'].reset_index(drop=True)

    df_midnight.rename(columns={'publication_date':'unified_agenda',
                                'action_type':'next_action_type',
                                'action_date':'next_action_date'},inplace=True)
    df_midnight['unified_agenda']=f'{agenda_season.capitalize()} {agenda_year}'
    df_midnight['abstract']=df_midnight['abstract'].apply(remove_html)

    df_midnight.drop(['stage','action_date2','midnight'],axis=1).\
        to_excel(f'{directory}/output/Potential Midnight Regulations in {agenda_season.capitalize()} {agenda_year} Unified Agenda.xlsx',index=False)

#-----------------------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------------
#%% Compare with previous agendas under the same administration (if not the first agenda)
if (agenda_year in [years[0] for years in admin_year.values()]) and (agenda_season=='spring'):
    pass
else:
    # Function to determine if an agenda is the first under an administration
    def get_start_year_for_admin(year):
        for admin, years in admin_year.items():
            start, end = years
            if start <= year <= end:
                return start
        return None  # Return None if the year doesn't fall in any range

    # Compile a list of previous agendas
    year_start=get_start_year_for_admin(agenda_year)
    season_start='spring'
    year_end=agenda_year if agenda_season=='fall' else agenda_year-1
    season_end='spring' if year_end==agenda_year else 'fall'

    agenda_list=[]
    for y in range(year_start,year_end+1):
        for s in ['spring','fall']:
            if (y==year_start) and (season_start=='fall'):
                agenda_list.append((y,season_start))
                break
            elif (y==year_end) and (season_end=='spring'):
                agenda_list.append((y,season_end))
                break
            else:
                agenda_list.append((y, s))
    print("Comparing Agendas:",agenda_list)

    # Append all previous agendas
    df_all=df
    for year,season in agenda_list:
        df_add=import_excel(year,season)
        df_all=pd.concat([df_all,df_add],ignore_index=True)
    df_all['publication_date']=df_all['publication_date'].astype(int)

    # Convert stage
    df_all=convert_stage(df_all)

    # # Compare with previous agendas
    # def print_counts(year,season):
    #     season_no='04' if season=='spring' else '10'
    #     df_temp=df[df['publication_date']==int(f'{year}{season_no}')]
    #     print(df_temp['publication_date'].iloc[0])
    #     print(df_temp['priority'].value_counts())
    #     print(df_temp['RIN_status'].value_counts())
    #     print(df_temp['rule_stage'].value_counts())
    #     print(df_temp['stage'].value_counts(),'\n')
    #     return
    #
    # print_counts(2021,'spring')

    # Compare current and previous agendas
    # ES rules
    print('Economically Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         ((df_all['priority']=='Economically Significant') |
                                          (df_all['priority']=='Section 3(f)(1) Significant'))]))
    print("\n")

    # Active ES rules
    print('Active Economically Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         ((df_all['priority']=='Economically Significant') |
                                          (df_all['priority']=='Section 3(f)(1) Significant')) &
                                         (df_all['stage']=='Active Actions')]))
    print("\n")

    # Other significant rules
    print('Other Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         (df_all['priority']=='Other Significant')]))
    print("\n")

    # Long term rules by priority
    print('Long-term actions by priority:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season} by',df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                    (df_all['stage']=='Long-Term Actions')]['priority'].value_counts(),'\n')

    # By stage
    df_compare=pd.DataFrame(columns=['stage'])
    for year,season in agenda_list+[(agenda_year,agenda_season)]:
        season_no = '04' if season == 'spring' else '10'
        df_stage=df_all[df_all['publication_date']==int(f'{year}{season_no}')]['stage'].\
            value_counts(dropna=False).reset_index(name=f'{season.capitalize()} {year}')
        df_compare=df_compare.merge(df_stage,on='stage',how='outer')
    df_compare=df_compare.set_index('stage')

    # Plot stacked bar
    ax = df_compare.T.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#033C5A','#0190DB','#AA9868'])
    for c in ax.containers:
        ax.bar_label(c, label_type='center',color='white', fontsize=12)

    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
    ax.set_ylabel('Number of Actions', fontsize=12)
    ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
    ax.tick_params(axis='x',which='major',labelsize=12,color='#d3d3d3', rotation=30)
    ax.set_title(f"{agenda_season.capitalize()} {agenda_year} and Previous Agendas under the Biden Administration",
                 fontsize=18)

    # Borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d3d3d3')
    ax.spines['bottom'].set_color('#d3d3d3')

    plt.savefig(f'{directory}/output/{agenda_season.capitalize()} {agenda_year} and Previous Agendas.jpg', bbox_inches='tight')
    plt.close()

#-----------------------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------------
#%% Compare with nth Agenda of previous administrations
def get_nth_publication(year, season):
    for admin, (start, end) in admin_year.items():
        if start <= year < end:
            # Calculate how many full years have passed since the admin started
            years_elapsed = year - start
            # Each year has 2 publications; multiply by 2
            n = years_elapsed * 2
            # Add 1 for spring or 2 for fall of the current year
            n += 1 if season == 'spring' else 2
            return n
    return None  # If year is not within any administration

# Determine if the agenda is the last one of an administration
if (agenda_year in [years[1] for years in admin_year.values()]) and (agenda_season=='fall'):
    n='last'     #(number or 'last')
else:
    n=get_nth_publication(agenda_year,agenda_season)

#%% Find the admin of the current agenda
for admin, (start, end) in admin_year.items():
    if start <= agenda_year < end:
        agenda_admin=admin
        break

# Aggregate ES actions by stage in current agenda
df_es_stage=df[(df['priority']=='Economically Significant') |
               (df['priority']=='Section 3(f)(1) Significant')]['stage'].\
               value_counts(dropna=False).reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

# Aggregate significant actions by priority in current agenda
def sig_filter(df):
    df.loc[(df['priority']=='Economically Significant') |
           (df['priority']=='Section 3(f)(1) Significant'),'priority']=\
           'Economically Significant'
    df_sig=df[(df['priority']=='Economically Significant') |
              (df['priority']=='Other Significant')].reset_index(drop=True)
    return df_sig

df_sig_stage=sig_filter(df)
df_sig_stage=df_sig_stage['priority'].value_counts(dropna=False).\
            reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

# Aggregate active significant actions by priority in current agenda
df_active_sig_stage=sig_filter(df)
df_active_sig_stage=df_active_sig_stage[df_active_sig_stage['stage']=='Active Actions']['priority'].value_counts(dropna=False).\
            reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

#%% Import previous UAs
df_compare_es=df_es_stage
df_compare_sig=df_sig_stage
df_compare_active_sig=df_active_sig_stage
for admin in [a for a in reversed(list(admin_year.keys())) if a != agenda_admin]:
    if n=='last':
        year_add_admin=admin_year[admin][1]
    else:
        year_add_admin=admin_year[admin][0]+((n - 1)//2)

    if (1995<year_add_admin<current_year) or (year_add_admin==1995 and agenda_season=='fall'):
        # Import
        df_admin=import_excel(year_add_admin,agenda_season)

        # Aggregate ES actions by stage in previous agenda
        df_admin = convert_stage(df_admin)
        df_admin_es = df_admin[(df_admin['priority']=='Economically Significant') |
                               (df_admin['priority']=='Section 3(f)(1) Significant')]['stage'].\
                               value_counts(dropna=False).reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        # Merge
        df_compare_es = df_compare_es.merge(df_admin_es, on='stage', how='outer')

        # Aggregate significant actions by priority in previous agenda
        df_admin_sig=sig_filter(df_admin)
        df_admin_sig = df_admin_sig['priority'].value_counts(dropna=False). \
                        reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        # Merge
        df_compare_sig = df_compare_sig.merge(df_admin_sig, on='priority', how='outer')

        # Aggregate active significant actions by priority in previous agenda
        df_admin_active_sig=sig_filter(df_admin)
        df_admin_active_sig = df_admin_active_sig[df_admin_active_sig['stage'] == 'Active Actions']['priority'].value_counts(dropna=False). \
            reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        # Merge
        df_compare_active_sig = df_compare_active_sig.merge(df_admin_active_sig, on='priority', how='outer')

# Set index
df_compare_es.set_index('stage',inplace=True)
df_compare_sig.set_index('priority',inplace=True)
df_compare_active_sig.set_index('priority',inplace=True)

# n to words
p = inflect.engine()
n_word=p.ordinal(n) if isinstance(n, int) else n

#%% Plot stacked bar for ES actions by stage
ax = df_compare_es.T.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#033C5A','#0190DB','#AA9868'])
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)

ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Economically Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations",
             fontsize=18)

# Borders
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3')
ax.spines['bottom'].set_color('#d3d3d3')

plt.savefig(f'{directory}/output/{n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

#%% Plot stacked bar for significant actions
ax = df_compare_sig.T.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#033C5A','#0190DB'])
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)

ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations",
             fontsize=18)

# Borders
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3')
ax.spines['bottom'].set_color('#d3d3d3')

plt.savefig(f'{directory}/output/Significant Actions in the {n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

#%% Plot stacked bar for active significant actions
ax = df_compare_active_sig.T.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#033C5A','#0190DB'])
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)

ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Active Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations",
             fontsize=18)

# Borders
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3')
ax.spines['bottom'].set_color('#d3d3d3')

# # Add note
# txt="Note: Light blue bars indicate section 3(f)(1) significant actions published in the Fall 2024 Unified Agenda " \
#     "and economically significant\nactions in the previous Agendas."
# plt.figtext(0.11, -0.12, txt, horizontalalignment='left', fontsize=12)
# fig.subplots_adjust(bottom=0.25)

plt.savefig(f'{directory}/output/Active Significant Actions in the {n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

#%% Clean raw data files
raw_path = f'{directory}/raw_data'
for filename in os.listdir(raw_path):
    file_path = os.path.join(raw_path, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)

#%% End
print("End of execution! See the Output folder for charts and datasets.")