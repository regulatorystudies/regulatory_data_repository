import warnings
warnings.filterwarnings('ignore') # Ignore warnings
import pandas as pd
import os
from lxml import etree
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO
import base64

pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', 10)

import streamlit as st
from unified_agenda_data import *
from oira_review_data_collector import *
# from unified_agenda_data_analysis import *

# 3 things to work on -
# - add a txt file with all the data
# - plot slideshow based on how the user selects the file
# - table with the minimum information



st.markdown(
    """
    <style>
    .stApp{
        background-color: #033C5A;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.image("images/logo.png",use_container_width=True)



def safe_find_text(node, tag, index=None):

    element = node.find(tag)
    if element is not None:
        try:
            if index is not None:
                return element[index].text if len(element) > index else ""
            return element.text or ""
        except:
            return ""
    return ""

current_time = datetime.now()
current_year = current_time.year


tab1, tab2, tab3 = st.tabs(["Unified Agenda Data","OIRA Review Data","Unified Agenda Data Analysis"])

with tab1:
    st.markdown(
        "<h1 style='color:#AA9868';>Unified Agenda data</h1>",
        unsafe_allow_html=True
    )
    st.write(f'The Unified Agenda data are available from Fall 1995 through {current_season.title()} {current_year}.\n')
    st.write(
        f'To request data, please enter the year and season range between Fall 1995 and {current_season.title()} {current_year}.')
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.selectbox("Start Year", list(range(1995,2025)),index=0)
        start_season = st.selectbox("Start Season",("spring","fall"),index=0)
    with col2:
        end_year = st.selectbox("End Year", list(range(1995, 2025)), index=0)
        end_season = st.selectbox("End Season", ("spring", "fall"), index=0)

    if st.button("More Information"):
        st.write("More Information about the dataset")
        st.image("images/data.png")

    if st.button("Display Data"):
        st.info("Collecting data, please wait...")

        # Call your collection function
        df = collect_ua_data(start_year, start_season, end_year, end_season)
        df1 = xml_to_csv(download_file(start_year, start_season))
        df2 = xml_to_csv(download_file(end_year, end_season))
        df = pd.concat([df1, df2], ignore_index=True)
        df = reorder_columns(df)
        name =f'REGINFO_RIN_DATA_{start_year}{start_season}-{end_year}{end_season}.csv'
        df.to_csv(name, index=False)
        # Save as CSV

        selected_columns = st.multiselect("select columns to display", df.columns.tolist(), default=df.columns.tolist())
        st.subheader("Data Preview")
        st.dataframe(df[selected_columns].head(20))

        # Download button
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            mime="text/csv"
        )




with tab2:
    st.markdown(
        "<h1 style='color:#AA9868';>Office of Information and Regulatory Affairs (OIRA) Review Data.</h1>",
        unsafe_allow_html=True
    )

    current_year = datetime.now().year
    agy_url = 'https://raw.githubusercontent.com/zhoudanxie/regulatory_data_repository/main/other_data/AGY_AGENCY_LIST.xml'
    agy_path = 'AGY_AGENCY_LIST.xml'


    @st.cache_data
    def download_agency_list():
        r = requests.get(agy_url)
        with open(agy_path, 'wb') as f:
            f.write(r.content)
        df = pdx.read_xml(open(agy_path).read(), ['OIRA_DATA']).pipe(pdx.flatten).pipe(pdx.flatten)
        return pd.DataFrame({
            'agency_code': df['AGENCY|AGENCY_CODE'].astype(int),
            'agency_name': df['AGENCY|NAME']
        })


    def download_xml(year):
        filename = f'EO_RULE_COMPLETED_{year}.xml'
        url = f'https://www.reginfo.gov/public/do/XMLViewFileAction?f=EO_RULE_COMPLETED_{year}.xml' \
            if year != current_year else \
            'https://www.reginfo.gov/public/do/XMLViewFileAction?f=EO_RULE_COMPLETED_YTD.xml'

        if not os.path.exists(filename):
            r = requests.get(url)
            content = r.content.decode('utf-8')
            if 'DATE_RECEIVED' in content:
                with open(filename, 'wb') as f:
                    f.write(r.content)
                return filename
            else:
                return None
        return filename


    def oira_transformation(filepath, agy_info):
        parser = etree.XMLParser(encoding="UTF-8", recover=True)
        xml = etree.parse(filepath, parser).getroot()

        data = []
        for regact in xml.findall("REGACT"):
            row = {
                'agency_code': int(regact.findtext("AGENCY_CODE", default=-1)),
                'rin': regact.findtext("RIN", default="NA"),
                'title': regact.findtext("TITLE", default="NA"),
                'stage': regact.findtext("STAGE", default="NA"),
                'ES': regact.findtext("ECONOMICALLY_SIGNIFICANT", default="NA"),
                'date_received': regact.findtext("DATE_RECEIVED", default="NA"),
                'legal_deadline': regact.findtext("LEGAL_DEADLINE", default="NA"),
                'date_completed': regact.findtext("DATE_COMPLETED", default="NA"),
                'decision': regact.findtext("DECISION", default="NA"),
                'date_published': regact.findtext("DATE_PUBLISHED", default="NA"),
                'health_care_act': regact.findtext("HEALTH_CARE_ACT", default="NA"),
                'Dodd_Frank_Act': regact.findtext("DODD_FRANK_ACT", default="NA"),
                'international_impacts': regact.findtext("INTERNATIONAL_IMPACTS", default="NA"),
                'unfunded_mandates': regact.findtext("UNFUNDED_MANDATES", default="NA"),
                'major': regact.findtext("MAJOR", default="NA"),
                'homeland_security': regact.findtext("HOMELAND_SECURITY", default="NA"),
                'regulatory_flexibility_analysis': regact.findtext("REGULATORY_FLEXIBILITY_ANALYSIS", default="NA")
            }
            data.append(row)

        df = pd.DataFrame(data)
        df = df.merge(agy_info, on="agency_code", how='left')
        df.insert(1, 'agency_name', df.pop('agency_name'))
        return df


    def process_oira_data(years):
        agy_info = download_agency_list()
        results = []
        for year in years:
            xml_file = download_xml(year)
            if xml_file:
                df = oira_transformation(xml_file, agy_info)
                results.append(df)
        if results:
            return pd.concat(results, ignore_index=True)
        return pd.DataFrame()




    mode = st.radio("Select Mode:", ["Single Year", "Multiple Years"])
    if mode == "Single Year":
        year = st.number_input("Enter Year", min_value=1981, max_value=current_year, step=1, value=current_year)
        if st.button("Download and Transform"):
            df = process_oira_data([year])
            if not df.empty:
                st.success("Data downloaded and processed.")
                st.dataframe(df.head())
                st.download_button("Download CSV", df.to_csv(index=False), file_name=f"OIRA_{year}.csv")
            else:
                st.error("Failed to fetch data.")
    else:
        start_year, end_year = st.slider("Select Year Range", min_value=1981, max_value=current_year,
                                         value=(2015, current_year))
        if st.button("Display data"):
            df = process_oira_data(list(range(start_year, end_year + 1)))
            if not df.empty:
                st.success("Data downloaded and processed.")
                st.dataframe(df.head())
                st.download_button("Download CSV", df.to_csv(index=False),
                                   file_name=f"OIRA_{start_year}-{end_year}.csv")
            else:
                st.error("Failed to fetch data.")

with tab3:
    st.markdown(
        "<h1 style='color:#AA9868';>Unified Agenda Analysis Dashboard</h1>",
        unsafe_allow_html=True
    )
    year = st.number_input("Enter Year here", min_value=1995, max_value=current_year, step=1, value=current_year)
    season = st.selectbox(
        "Please enter the season",
        ('spring','fall')
    )

    # agenda_season = restrict_season(season)

    # df = import_excel(year, season, agenda_midnight)
    st.write("Year",year)
    st.write("Season",season)
    # st.write("agenda midnight",agenda_midnight)
    # st.write("agenda season", agenda_season)


