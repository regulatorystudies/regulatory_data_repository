#--------------------------------------------Append Unified Agenda XML-------------------------------------------------#

import pandas as pd
import os
import xml.etree.cElementTree as et
pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', 10)

# Load XML reports
def import_xml(file):
    df_xml = pd.DataFrame()
    xmlp = et.XMLParser(encoding="UTF-8")
    parsed_xml = et.parse(file,parser=xmlp)
    root = parsed_xml.getroot()
    row=0
    for child in root:
        df_xml.at[row, 'publication_date']=child.find('PUBLICATION')[0].text
        df_xml.at[row, 'RIN']=child.find('RIN').text
        df_xml.at[row, 'agency_code']=child.find('AGENCY')[0].text
        df_xml.at[row, 'agency_name']=child.find('AGENCY')[1].text
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

        # Legal deadline codes need to be revised.
        # if child.find('LEGAL_DLINE_LIST')!=None:
        #     index=0
        #     while (index<len(list(child.find('LEGAL_DLINE_LIST')))):
        #         if child.find('LEGAL_DLINE_LIST').find('LEGAL_DLINE_INFO') != None:
        #             colname='legal_deadline'+str(index+1)
        #             text=''
        #             for i in range(0,len(list(child.find('LEGAL_DLINE_LIST')[index]))):
        #                 add=child.find('LEGAL_DLINE_LIST')[index][i].text
        #                 if text=='':
        #                     text=add
        #                 else:
        #                     text=text+'; '+add if add is not None else text
        #             df_xml.at[row,colname]=text
        #         index=index+1

        if child.find('TIMETABLE_LIST')!=None:
            index=0
            while (index<len(list(child.find('TIMETABLE_LIST')))):
                colname='action_date_FR'+str(index+1)
                if child.find('TIMETABLE_LIST')[index].find('FR_CITATION')!=None:
                    df_xml.at[row, colname]=child.find('TIMETABLE_LIST')[index][0].text+'; '+child.find('TIMETABLE_LIST')[index][1].text+'; '+child.find('TIMETABLE_LIST')[index][2].text
                else:
                    if child.find('TIMETABLE_LIST')[index].find('TTBL_DATE')!=None:
                        df_xml.at[row, colname] = child.find('TIMETABLE_LIST')[index][0].text + '; ' + \
                                               child.find('TIMETABLE_LIST')[index][1].text
                    else:
                        df_xml.at[row, colname] = child.find('TIMETABLE_LIST')[index][0].text
                index=index+1
        row=row+1
    return df_xml

df_all=pd.DataFrame()
for file in os.listdir('Unified Agenda Data/Raw Data'):
    if file.endswith('.xml'):
        filepath='Unified Agenda Data/Raw Data/'+str(file)
        df=import_xml(filepath)
        df_all=df_all.append(df,ignore_index=True)
print(df_all.info())

print(list(df_all.columns.values))
col_list=[]
for n in range(1,143):
    col="action_date_FR"+str(n)
    col_list.append(col)
df_all_copy=df_all[['publication_date','RIN', 'rule_title','agency_code', 'agency_name', 'department_code',
 'department_name', 'abstract', 'priority','major','RIN_status', 'rule_stage', 'CFR', 'legal_authority']+col_list]
print(df_all_copy.info())
df_all_copy=df_all_copy.sort_values(['publication_date','RIN']).reset_index(drop=True)
#df_all_copy.to_csv('Unified Agenda Data/Unified Agenda 199510-202010.csv',index=False)
df_all_copy.to_csv('Unified Agenda Data/Unified Agenda 199510-202104.csv',index=False)


