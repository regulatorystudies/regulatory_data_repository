import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import zipfile
import time
from tqdm import tqdm
from pathlib import Path

#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------
#%%Download XML files from GovInfo Bulk Data Repository
files_failed=[]
for year in range(2000, 2022):
    folder_path = 'federal_register_data/raw_xml_data/FR-' + str(year)
    file_path = 'federal_register_data/raw_xml_data/FR-' + str(year)+'.zip'
    try:
        if not os.path.exists(file_path):
            file_url = 'https://www.govinfo.gov/bulkdata/FR/'+str(year)+'/FR-'+str(year)+'.zip'
            r = requests.get(file_url, allow_redirects=True)
            open(file_path, 'wb').write(r.content)
            print(str(year) +' has been downloaded')
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(folder_path)
            print(str(year) +' has been extracted')
    except:
        print('Failed: ' +str(year))
        files_failed.append(year)
        pass

#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------
#%%Parse final rules
def parse_rule(xml_data):
    results=[]
    soup = BeautifulSoup(xml_data,'xml')
    date=soup.find('DATE').text
    for rule in soup.find_all('RULE'):
        try:
            agency=rule.find('PREAMB').find('AGENCY').text
        except:
            agency=""
            pass
        try:
            rin=rule.find('PREAMB').find('RIN').text
        except:
            rin=""
            pass
        try:
            subject=rule.find('PREAMB').find('SUBJECT').text
        except:
            subject=""
            pass
        try:
            action=rule.find('PREAMB').find('ACT').find('P').text
        except:
            action=""
            pass
        try:
            summary=rule.find('PREAMB').find('SUM').find('P').text
        except:
            summary=""
            pass
        results.append((date,agency,rin,action,subject,summary))
    return results

results=[]
for year in range(2000,2022):
    print(year)
    # assign directory
    directory = 'federal_register_data/raw_xml_data/FR-'+str(year)
    # iterate over files in that directory
    files = Path(directory).glob('**/*')
    for file in tqdm(files):
        if file.suffix=='.xml':
            data = open(file,"r",encoding="UTF-8",errors='ignore')
            results=results+parse_rule(data)
df_results=pd.DataFrame(results,columns=['date','agency','rin','action','subject','summary'])
print(df_results.info())

# Export
df_results.to_pickle('federal_register_data/all_fr.pkl')
