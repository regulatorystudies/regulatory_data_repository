#----------------------------------Analysis of a Unified Agenda----------------------------------------------#

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
# UPDATE WHEN NEW ADMIN
admin_year = {'Clinton': [1993, 2001],
              'Bush 43': [2001, 2009],
              'Obama': [2009, 2017],
              'Trump 45': [2017, 2021],
              'Biden': [2021, 2025],
              'Trump 47': [2025, 2029]}

#%% Set directory
directory=os.path.dirname(os.path.realpath(__file__))

#%% Create subdirectories if they do not exist
for sub in ("raw_data","output"):
    folder_path=f"{directory}/{sub}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

#%% Function to convert date
def convert_date(s):
    month=s.split('/')[0]
    if month.isdigit():
        year=s.split('/')[2]
        return datetime.datetime(int(year), int(month), 1)
    else:
        return None

#-----------------------------------------------------------------------------------------------------------------------
#%% Function to load XML reports
def import_xml(file,year,midnight=0):
    df_xml = pd.DataFrame()
    parser = etree.XMLParser(encoding="UTF-8", recover=True)
    parsed_xml = etree.parse(file, parser)
    root = parsed_xml.getroot()
    row=0
    for child in root:
        df_xml.at[row, 'publication_date']=child.find('PUBLICATION')[0].text
        df_xml.at[row, 'RIN']=child.find('RIN').text
        if child.find('AGENCY') is not None:
            df_xml.at[row, 'agency_code']=child.find('AGENCY')[0].text
            if child.find('AGENCY').find('NAME') is not None:
                df_xml.at[row, 'agency_name']=child.find('AGENCY').find('NAME').text
        if child.find('PARENT_AGENCY') is not None:
            df_xml.at[row, 'department_code']=child.find('PARENT_AGENCY')[0].text
            df_xml.at[row, 'department_name']=child.find('PARENT_AGENCY')[1].text
        df_xml.at[row, 'rule_title'] = child.find('RULE_TITLE').text
        df_xml.at[row, 'abstract']=child.find('ABSTRACT').text
        if child.find('PRIORITY_CATEGORY') is not None:
            df_xml.at[row, 'priority']=child.find('PRIORITY_CATEGORY').text
        if child.find('RIN_STATUS') is not None:
            df_xml.at[row, 'RIN_status']=child.find('RIN_STATUS').text
        if child.find('RULE_STAGE') is not None:
            df_xml.at[row, 'rule_stage']=child.find('RULE_STAGE').text
        df_xml.at[row, 'major']=child.find('MAJOR').text if child.find('MAJOR') is not None else None

        if child.find('CFR_LIST') is not None:
            index=0; text=''
            while (index<len(list(child.find('CFR_LIST')))):
                add=child.find('CFR_LIST')[index].text
                text = add if text=='' else text+"; "+str(add)
                index += 1
            df_xml.at[row, 'CFR'] = text

        if child.find('LEGAL_AUTHORITY_LIST') is not None:
            index=0; text=''
            while (index<len(list(child.find('LEGAL_AUTHORITY_LIST')))):
                add=child.find('LEGAL_AUTHORITY_LIST')[index].text
                text = add if text=='' else text+"; "+str(add)
                index += 1
            df_xml.at[row, 'legal_authority']=text

        # All actions in timetable
        if child.find('TIMETABLE_LIST') is not None:
            index=0
            while (index<len(list(child.find('TIMETABLE_LIST')))):
                colname='action_date_FR'+str(index+1)
                node = child.find('TIMETABLE_LIST')[index]
                if node.find('FR_CITATION') is not None:
                    df_xml.at[row, colname]=node[0].text+'; '+node[1].text+'; '+node[2].text
                else:
                    if node.find('TTBL_DATE') is not None:
                        df_xml.at[row, colname] = node[0].text + '; ' + node[1].text
                    else:
                        df_xml.at[row, colname] = node[0].text
                index += 1

        # Last action in timetable
        if child.find('TIMETABLE_LIST') is not None:
            node = child.find('TIMETABLE_LIST')[-1]
            if node.find('FR_CITATION') is not None:
                df_xml.at[row, 'action_type']=node[0].text
                df_xml.at[row, 'action_date'] = node[1].text
                df_xml.at[row, 'fr_citation'] = node[2].text
            else:
                if node.find('TTBL_DATE') is not None:
                    df_xml.at[row, 'action_type'] = node[0].text
                    df_xml.at[row, 'action_date'] = node[1].text
                else:
                    df_xml.at[row, 'action_type'] = node[0].text

        # Potential midnight actions
        if midnight==1 and child.find('TIMETABLE_LIST') is not None:
            for node in child.find('TIMETABLE_LIST'):
                if node.find('FR_CITATION') is not None:
                    action_type=node[0].text; action_date=node[1].text; fr_citation=node[2].text
                else:
                    if node.find('TTBL_DATE') is not None:
                        action_type=node[0].text; action_date=node[1].text; fr_citation=None
                    else:
                        action_type=node[0].text; action_date=None; fr_citation=None
                dt = convert_date(action_date) if action_date else None
                if dt is not None and dt > datetime.datetime(year,11,30):
                    break
            df_xml.at[row, 'action_type']=action_type
            df_xml.at[row, 'action_date'] = action_date
            df_xml.at[row, 'fr_citation'] = fr_citation

        row += 1
    return df_xml

#%% Download XML
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

#%% Save agenda as Excel
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
    else:
        df=pd.read_excel(excel_path)
    return df

#%% Latest year/season from Reginfo.gov
page = requests.get("https://www.reginfo.gov/public/do/eAgendaXmlReport")
soup = BeautifulSoup(page.content, 'html.parser')
newest_file_info = soup.select('li')[0].text[1:-6]
current_year_season = re.split(r"\s", newest_file_info, 1)
current_year = int(current_year_season[1])
current_season = current_year_season[0].lower()

#%% Input helpers
def input_year(year_type='year'):
    year_range = range(1995, current_year + 1)
    while True:
        year=int(input(f'Please enter the {year_type} of the Unified Agenda you are analyzing (e.g. 2024): '))
        if year in year_range:
            return year
        else:
            print(f'ERROR: Your input year {year} is not in the valid time range.')

def input_season():
    sea_option = ['spring','fall']
    while True:
        season=input(f'Please enter the season of the Agenda ("spring" or "fall"): ').lower()
        if season in sea_option:
            return season
        else:
            print(f'ERROR: Your input season "{season}" is not valid.')

def restrict_season(year):
    if year == 1995:
        season = 'fall'; print(f'Only fall agenda is available for {year}.')
    elif year == 2012:
        season = 'fall'; print(f'Only one agenda was published in {year}.')
    elif year == current_year:
        if current_season == 'spring':
            season = 'spring'; print(f'The most recent Unified Agenda is {current_season.title()} {current_year}')
        else:
            season = input_season()
    else:
        season = input_season()
    return season

#%% User input
print(f'The Unified Agenda data are available from Fall 1995 through {current_season.title()} {current_year}.\n')
print(f'To analyze data, please enter the year and season range between Fall 1995 and {current_season.title()} {current_year}.')
agenda_year=input_year()
agenda_season = restrict_season(agenda_year)

#%% Midnight?
agenda_midnight = 1 if (agenda_year in [years[1]-1 for years in admin_year.values()]) and (agenda_season=='fall') else 0

#%% Import Current Agenda
df=import_excel(agenda_year,agenda_season,agenda_midnight)
print(df.info())

#-----------------------------------------------------------------------------------------------------------------------
# Basic counts
print('Total # of actions:',len(df))
print("Actions by",df['priority'].value_counts(),"\n")
print("Actions by",df['RIN_status'].value_counts(),"\n")

# Stage conversion
def convert_stage(df):
    df.loc[df['rule_stage'] == 'Completed Actions', 'stage'] = 'Completed Actions'
    df.loc[df['rule_stage'] == 'Long-Term Actions', 'stage'] = 'Long-Term Actions'
    df.loc[(df['rule_stage'] != 'Long-Term Actions') & (df['rule_stage'] != 'Completed Actions'),'stage'] = 'Active Actions'
    return df

df=convert_stage(df)
print("Actions by rulemaking",df['stage'].value_counts(),"\n")

print('Active actions by', df[df['stage']=='Active Actions']['priority'].value_counts(),'\n')
print('Active actions by', df[df['stage']=='Active Actions']['RIN_status'].value_counts(),'\n')
print('Long-term actions by',df[df['stage']=='Long-Term Actions']['priority'].value_counts(),'\n')
print('Long-term actions by',df[df['stage']=='Long-Term Actions']['RIN_status'].value_counts(),'\n')
print('Completed actions by',df[df['stage']=='Completed Actions']['priority'].value_counts(),'\n')
print('Completed actions by',df[df['stage']=='Completed Actions']['RIN_status'].value_counts(),'\n')

print('Economically significant actions by',df[(df['priority']=='Economically Significant') |
      (df['priority']=='Section 3(f)(1) Significant')]['stage'].value_counts(),'\n')
print('Economically significant actions by',df[(df['priority']=='Economically Significant') |
      (df['priority']=='Section 3(f)(1) Significant')]['RIN_status'].value_counts(),'\n')

print('Active economically significant actions by',
      df[((df['priority']=='Economically Significant') | (df['priority']=='Section 3(f)(1) Significant')) &
         (df['stage']=='Active Actions')]['RIN_status'].value_counts(),'\n')

print('First time published actions by',df[df['RIN_status']=='First Time Published in The Unified Agenda']['stage'].value_counts(),'\n')

# First Time Published & Completed Actions
df_temp=df[(df['RIN_status']=='First Time Published in The Unified Agenda') & (df['stage']=='Completed Actions')].reset_index(drop=True)

# Midnight slicing
if agenda_midnight==1:
    df['action_date2']=df['action_date'].apply(convert_date)
    df_es = df[((df['priority'] == 'Economically Significant') | (df['priority'] == 'Section 3(f)(1) Significant')) & (df['stage'] == 'Active Actions')].reset_index(drop=True)
    df_es['midnight'] = 0
    df_es.loc[(df_es['action_date2'] < datetime.datetime(agenda_year+1, 2, 1)) &
              (df_es['action_date2'] > datetime.datetime(agenda_year, 11, 30)), 'midnight'] = 1
    type_excl = ['NPRM Comment Period End', 'Analyzing Comments', 'Next Action Undetermined',
                 'Notice', 'Analyze Stakeholder Comments', 'NPRM Comment Period Extended End',
                 'Final Rule Effective', 'Informal Public Hearing (11/12/2024)']
    df_es.loc[df_es['action_type'].isin(type_excl), 'midnight'] = 0
    print("Potential midnight actions:", len(df_es[df_es['midnight']==1]),"\n")
    print("Potential midnight actions by",df_es[df_es['midnight'] == 1]['action_type'].value_counts())
else:
    df_es = df[((df['priority'] == 'Economically Significant') | (df['priority'] == 'Section 3(f)(1) Significant')) & (df['stage'] == 'Active Actions')].reset_index(drop=True)

# Agency & Department
df.loc[df['department_name'].isnull(),'department_name']=df['agency_name']
df_es.loc[df_es['department_name'].isnull(),'department_name']=df_es['agency_name']

print("Active economically significant actions by",
      df[((df['priority']=='Economically Significant') | (df['priority']=='Section 3(f)(1) Significant')) &
         (df['stage']=='Active Actions')]['department_name'].value_counts(dropna=False))

# Active ES actions by agency
df_es_agency=df_es['department_name'].value_counts(dropna=False).reset_index()

if agenda_midnight==1:
    df_es_mid=df_es[df_es['midnight']==1]['department_name'].value_counts(dropna=False).reset_index()
    df_es_agency=df_es_agency.merge(df_es_mid,on='department_name',how='left',suffixes=('_total', '_midnight'))
    df_es_agency.rename(columns={'index':'department_name'},inplace=True)
    df_es_agency['count_midnight']=df_es_agency['count_midnight'].fillna(0)
    df_es_agency['count_non_midnight']=df_es_agency['count_total']-df_es_agency['count_midnight']
else:
    df_es_agency.rename(columns={'count':'count_total'},inplace=True)

# Plot labels (generated for top 10 agencies)
agency_dict = {
    'Commodity Futures Trading Commission':'CFTC',
    'Consumer Financial Protection Bureau':'CFPB',
    'Consumer Product Safety Commission':'CPSC',
    'Department of Agriculture':'USDA',
    'Department of Commerce':'DOC',
    'Department of Defense':'DOD',
    'Department of Education':'ED',
    'Department of Energy':'DOE',
    'Department of Health and Human Services':'HHS',
    'Department of Homeland Security':'DHS',
    'Department of Housing and Urban Development':'HUD',
    'Department of the Interior':'DOI',
    'Department of Justice':'DOJ',
    'Department of Labor':'DOL',
    'Department of State':'DOS',
    'Department of Transportation':'DOT',
    'Department of the Treasury':'TREAS',
    'Department of Veterans Affairs':'VA',
    'Environmental Protection Agency':'EPA',
    'Federal Communications Commission':'FCC',
    'Federal Deposit Insurance Corporation':'FDIC',
    'Federal Housing Finance Agency':'FHFA',
    'Federal Maritime Commission':'FMC',
    'Federal Trade Commission':'FTC',
    'Nuclear Regulatory Commission':'NRC',
    'Postal Regulatory Commission':'PRC',
    'Securities and Exchange Commission':'SEC',
    'Small Business Administration':'SBA'
}

df_es_agency=df_es_agency[0:10]
df_es_agency['department_acronym']=[agency_dict[i] for i in df_es_agency['department_name']]
print('Active economically significant actions published by top 10 agencies:',sum(df_es_agency['count_total']))
if agenda_midnight==1:
    print('Potential midnight economically significant actions published by top 10 agencies:',sum(df_es_agency['count_midnight']))

# Bar by agency (single-color)
fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.bar(df_es_agency['department_acronym'], df_es_agency['count_total'], color='#033C5A', width=0.5)
ax.bar_label(bars)
ax.set_ylabel("Number of Actions",fontsize=12)
ax.set_title(f"Active Economically Significant Actions in the {agenda_season.capitalize()} {agenda_year}\nUnified Agenda for Select Agencies",
             fontsize=16)
ax.tick_params(axis='both',which='major',labelsize=12,color='#d3d3d3')
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
plt.savefig(f'{directory}/output/Active Economically Significant Actions by Agency.jpg', bbox_inches='tight')
plt.close()

# Stacked bar for midnight by agency
if agenda_midnight==1:
    df_es_agency=df_es_agency[['department_acronym','count_midnight','count_non_midnight']].set_index('department_acronym')
    df_es_agency.loc[df_es_agency['count_non_midnight']==0,'count_non_midnight']=np.nan
    df_es_agency.rename(columns={'count_midnight':f'Proposed or Final Rule Expected in Dec {agenda_year} or Jan {agenda_year+1}',
                          'count_non_midnight':f'Next Rulemaking Action Expected After Jan {agenda_year+1}'},inplace=True)
    ax = df_es_agency.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=['#0190DB','#033C5A'])
    for c in ax.containers:
        labels=[int(x) if x>0 else '' for x in c.datavalues]
        ax.bar_label(c, labels=labels, label_type='center', color='white', fontsize=10)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=1, fontsize=14)
    ax.set_ylabel('Number of Actions', fontsize=12); ax.set_xlabel('')
    ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
    ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
    ax.set_title(f"Active Economically Significant Actions in the {agenda_season.capitalize()} {agenda_year}\nUnified Agenda for Select Agencies",
                 fontsize=18)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
    plt.savefig(f'{directory}/output/Active Economically Significant Actions with Midnight Status by Agency.jpg', bbox_inches='tight')
    plt.close()

# Export potential midnight regulations
if agenda_midnight==1:
    CLEANR = re.compile('<.*?>')
    def remove_html(s): return re.sub(CLEANR, '', s).strip()
    df_midnight=df_es[df_es['midnight']==1].reset_index(drop=True)
    print('Potential economically significant midnight actions by',df_midnight['rule_stage'].value_counts())
    df_midnight.rename(columns={'publication_date':'unified_agenda','action_type':'next_action_type','action_date':'next_action_date'},inplace=True)
    df_midnight['unified_agenda']=f'{agenda_season.capitalize()} {agenda_year}'
    df_midnight['abstract']=df_midnight['abstract'].apply(remove_html)
    df_midnight.drop(['stage','action_date2','midnight'],axis=1).to_excel(f'{directory}/output/Potential Midnight Regulations in {agenda_season.capitalize()} {agenda_year} Unified Agenda.xlsx',index=False)

# Helper function for stable presidential order & locked colors
def order_stacks_and_colors(df_rows, row_order, color_map):
    df_ordered = df_rows.reindex(row_order)
    colors = [color_map[r] for r in df_ordered.index]
    return df_ordered, colors

# Admin extraction and strict ordering on the Transposed DF
import re as _re
# UPDATE WHEN NEW ADMIN
admin_pattern = _re.compile(r'^(Clinton|Bush 43|Obama|Trump 45|Biden|Trump 47)\b', _re.IGNORECASE)

def extract_admin(label: str):
    if label is None:
        return None
    m = admin_pattern.search(str(label).strip())
    if not m:
        return None
    # UPDATE WHEN NEW ADMIN
    canon = {
        'clinton': 'Clinton',
        'bush 43': 'Bush 43',
        'obama': 'Obama',
        'trump 45': 'Trump 45',
        'biden': 'Biden',
        'trump 47': 'Trump 47',
    }
    return canon[m.group(1).lower()]

def filter_and_order_admins_on_T(dfT, admin_order):

    # dfT = df Transposed (x-axis = dfT.index). Keep only rows whose admin matches admin_pattern, then order strictly by admin_order using categorical sort.
    idx = dfT.index.to_series()
    admins = idx.map(extract_admin)
    mask = admins.isin(admin_order)
    dfT2 = dfT[mask].copy()
    admins2 = admins[mask]
    cat = pd.Categorical(admins2, categories=admin_order, ordered=True)
    dfT2 = dfT2.iloc[cat.argsort(kind="stable")]
    return dfT2

# strict left-to-right x-axis admin order (became necessary to add due to previous bug where order was right-to-left)
# UPDATE WHEN NEW ADMIN
admin_order = ["Bush 43", "Obama", "Trump 45", "Biden", "Trump 47"]

#-----------------------------------------------------------------------------------------------------------------------
# Compare with previous agendas under the same admin (chronological; Biden-only chart)
if not ((agenda_year in [years[0] for years in admin_year.values()]) and (agenda_season=='spring')):
    def get_start_year_for_admin(year):
        for admin, years in admin_year.items():
            start, end = years
            if start <= year <= end:
                return start
        return None

    year_start=get_start_year_for_admin(agenda_year)
    season_start='spring'
    year_end=agenda_year if agenda_season=='fall' else agenda_year-1
    season_end='spring' if year_end==agenda_year else 'fall'

    agenda_list=[]
    for y in range(year_start,year_end+1):
        for s in ['spring','fall']:
            if (y==year_start) and (season_start=='fall'):
                agenda_list.append((y,season_start)); break
            elif (y==year_end) and (season_end=='spring'):
                agenda_list.append((y,season_end)); break
            else:
                agenda_list.append((y, s))
    print("Comparing Agendas:",agenda_list)

    df_all=df
    for year,season in agenda_list:
        df_add=import_excel(year,season)
        df_all=pd.concat([df_all,df_add],ignore_index=True)
    df_all['publication_date']=df_all['publication_date'].astype(int)
    df_all=convert_stage(df_all)

    print('Economically Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         ((df_all['priority']=='Economically Significant') |
                                          (df_all['priority']=='Section 3(f)(1) Significant'))]))
    print("\n")

    print('Active Economically Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         ((df_all['priority']=='Economically Significant') |
                                          (df_all['priority']=='Section 3(f)(1) Significant')) &
                                         (df_all['stage']=='Active Actions')]))
    print("\n")

    print('Other Significant Actions:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season}:',len(df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                         (df_all['priority']=='Other Significant')]))
    print("\n")

    print('Long-term actions by priority:')
    for year,season in agenda_list:
        season_no = '04' if season == 'spring' else '10'
        print(f'{year} {season} by',df_all[(df_all['publication_date']==int(f'{year}{season_no}')) &
                                    (df_all['stage']=='Long-Term Actions')]['priority'].value_counts(),'\n')

    # Stage-by-agenda table for Biden-only chart
    df_compare=pd.DataFrame(columns=['stage'])
    for year,season in agenda_list+[(agenda_year,agenda_season)]:
        season_no = '04' if season == 'spring' else '10'
        df_stage=df_all[df_all['publication_date']==int(f'{year}{season_no}')]['stage']\
            .value_counts(dropna=False).reset_index(name=f'{season.capitalize()} {year}')
        df_compare=df_compare.merge(df_stage,on='stage',how='outer')
    df_compare=df_compare.set_index('stage')

    # locked stage order & colors for this chart
    stage_order_biden = ["Active Actions", "Completed Actions", "Long-Term Actions"]
    stage_colors_map = {
        "Active Actions": "#033C5A",
        "Completed Actions": "#0190DB",
        "Long-Term Actions": "#AA9868"
    }
    df_plot_prev, colors_prev = order_stacks_and_colors(df_compare, stage_order_biden, stage_colors_map)

    desired_cols = [f"{s.capitalize()} {y}" for (y, s) in agenda_list + [(agenda_year, agenda_season)]]
    desired_cols += [c for c in df_plot_prev.columns if c not in desired_cols]
    df_plot_prev = df_plot_prev[desired_cols]

    ax = df_plot_prev.T.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=colors_prev)
    for c in ax.containers:
        ax.bar_label(c, label_type='center',color='white', fontsize=12)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
    ax.set_ylabel('Number of Actions', fontsize=12)
    ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
    ax.tick_params(axis='x',which='major',labelsize=12,color='#d3d3d3', rotation=30)
    ax.set_title(f"{agenda_season.capitalize()} {agenda_year} and Previous Agendas under the Biden Administration", fontsize=18)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
    plt.savefig(f'{directory}/output/{agenda_season.capitalize()} {agenda_year} and Previous Agendas.jpg', bbox_inches='tight')
    plt.close()

#-----------------------------------------------------------------------------------------------------------------------
# nth Agenda vs previous administrations
def get_nth_publication(year, season):
    for admin, (start, end) in admin_year.items():
        if start <= year < end:
            years_elapsed = year - start
            n = years_elapsed * 2
            n += 1 if season == 'spring' else 2
            return n
    return None

if (agenda_year in [years[1] for years in admin_year.values()]) and (agenda_season=='fall'):
    n='last'
else:
    n=get_nth_publication(agenda_year,agenda_season)

for admin, (start, end) in admin_year.items():
    if start <= agenda_year < end:
        agenda_admin=admin
        break

# Current agenda aggregations
df_es_stage=df[(df['priority']=='Economically Significant') | (df['priority']=='Section 3(f)(1) Significant')]\
    ['stage'].value_counts(dropna=False).reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

def sig_filter(df_):
    df_.loc[(df_['priority']=='Economically Significant') | (df_['priority']=='Section 3(f)(1) Significant'),'priority']='Economically Significant'
    return df_[(df_['priority']=='Economically Significant') | (df_['priority']=='Other Significant')].reset_index(drop=True)

df_sig_stage=sig_filter(df)
df_sig_stage=df_sig_stage['priority'].value_counts(dropna=False).reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

df_active_sig_stage=sig_filter(df)
df_active_sig_stage=df_active_sig_stage[df_active_sig_stage['stage']=='Active Actions']['priority'].value_counts(dropna=False)\
    .reset_index(name=f'{agenda_admin}\n({agenda_season.capitalize()} {agenda_year})')

# Import previous UAs
df_compare_es=df_es_stage.copy()
df_compare_sig=df_sig_stage.copy()
df_compare_active_sig=df_active_sig_stage.copy()

for admin in [a for a in reversed(list(admin_year.keys())) if a != agenda_admin]:
    if n=='last':
        year_add_admin=admin_year[admin][1]
    else:
        year_add_admin=admin_year[admin][0]+((n - 1)//2)

    if (1995<year_add_admin<current_year) or (year_add_admin==1995 and agenda_season=='fall'):
        df_admin=import_excel(year_add_admin,agenda_season)
        df_admin = convert_stage(df_admin)

        df_admin_es = df_admin[(df_admin['priority']=='Economically Significant') | (df_admin['priority']=='Section 3(f)(1) Significant')]\
            ['stage'].value_counts(dropna=False).reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        df_compare_es = df_compare_es.merge(df_admin_es, on='stage', how='outer')

        df_admin_sig=sig_filter(df_admin)
        df_admin_sig = df_admin_sig['priority'].value_counts(dropna=False).reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        df_compare_sig = df_compare_sig.merge(df_admin_sig, on='priority', how='outer')

        df_admin_active_sig=sig_filter(df_admin)
        df_admin_active_sig = df_admin_active_sig[df_admin_active_sig['stage'] == 'Active Actions']['priority']\
            .value_counts(dropna=False).reset_index(name=f'{admin}\n({agenda_season.capitalize()} {year_add_admin})')
        df_compare_active_sig = df_compare_active_sig.merge(df_admin_active_sig, on='priority', how='outer')

# Set index
df_compare_es.set_index('stage',inplace=True)
df_compare_sig.set_index('priority',inplace=True)
df_compare_active_sig.set_index('priority',inplace=True)

# n to words
p = inflect.engine()
n_word=p.ordinal(n) if isinstance(n, int) else n

# ---------- Plot 1: ES actions by stage ----------
stage_order_main = ["Active Actions", "Completed Actions", "Long-Term Actions"]
stage_colors_map = {
    "Active Actions": "#033C5A",
    "Completed Actions": "#0190DB",
    "Long-Term Actions": "#AA9868"
}
df_plot_es, colors_es = order_stacks_and_colors(df_compare_es, stage_order_main, stage_colors_map)
dfT = filter_and_order_admins_on_T(df_plot_es.T, admin_order)

ax = dfT.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=colors_es)
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Economically Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations", fontsize=18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
plt.savefig(f'{directory}/output/{n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

# ---------- Plot 2: Significant actions ----------
priority_order = ["Other Significant", "Economically Significant"]
priority_colors_map = {
    "Other Significant": "#033C5A",
    "Economically Significant": "#0190DB",
}
df_plot_sig = df_compare_sig.reindex(priority_order)
colors_sig = [priority_colors_map[p] for p in df_plot_sig.index]
dfT = filter_and_order_admins_on_T(df_plot_sig.T, admin_order)

ax = dfT.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=colors_sig)
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations", fontsize=18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
plt.savefig(f'{directory}/output/Significant Actions in the {n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

# ---------- Plot 3: Active significant actions ----------
df_plot_active = df_compare_active_sig.reindex(priority_order)
colors_active = [priority_colors_map[p] for p in df_plot_active.index]
dfT = filter_and_order_admins_on_T(df_plot_active.T, admin_order)

ax = dfT.plot.bar(stacked=True, figsize=(12, 7), rot=0, color=colors_active)
for c in ax.containers:
    ax.bar_label(c, label_type='center',color='white', fontsize=12)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=14)
ax.set_ylabel('Number of Actions', fontsize=12)
ax.tick_params(axis='y',which='major',labelsize=12,color='#d3d3d3')
ax.tick_params(axis='x',which='major',labelsize=14,color='#d3d3d3')
ax.set_title(f"Active Significant Actions Published in the {n_word.capitalize()} Unified Agenda\nunder Different Administrations", fontsize=18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#d3d3d3'); ax.spines['bottom'].set_color('#d3d3d3')
plt.savefig(f'{directory}/output/Active Significant Actions in the {n_word.capitalize()} Agendas under Administrations.jpg', bbox_inches='tight')
plt.close()

#%% Clean raw data files
raw_path = f'{directory}/raw_data'
for filename in os.listdir(raw_path):
    file_path = os.path.join(raw_path, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)

print("End of execution! See the Output folder for charts and datasets.")