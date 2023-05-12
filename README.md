# Regulatory Data Repository (Preliminary)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/zhoudanxie/regulatory_data_repository/HEAD)

This repository provides Python code and tools to obtain and use publicly available data on federal rulemakings. The purpose of this repository is to facilitate research on regulation using government big data.

This repository will be complemented and updated routinely.

The current version of the repository contains the following foders:


## 1. Unified Agenda Data

This folder contains Python code to obtain and organize data from the semiannual [Unified Agenda of Regulatory and Deregulatory Actions](https://www.reginfo.gov/public/do/eAgendaMain) since Fall 1995. The code will generate a clean CSV file covering all the rulemaking actions published in user-specified Unified Agendas. For each action, the CSV file contains most of the information you can find on a Unified Agenda page (for example, [RIN 2060-AN53](https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=200604&RIN=2060-AN53)), including RIN, rule title, abstract, agency, priority (i.e., economically significant, significant, etc.), RIN status, rule stage, CFR citation, legal authority, legal deadlines, and timetable (i.e., action, data, and FR citation). 

|            |  Unified Agenda Data                                                           | 
| :-------- | :------------------------------------------------------------------------------ |
| Source:    | [Reginfo.gov Unified Agenda XML Reports](https://www.reginfo.gov/public/do/eAgendaXmlReport)   |
| Timeframe: | Fall 1995 - The latest available date                                                          |


## 2. OIRA Review Data

This folder contains Python code to obtain and organize data on rulemaking actions reviewed by the Office of Information and Regulatory Affairs (OIRA) since 1981. The code will generate a clean CSV file covering all the actions reviewed by OIRA during user-specified years. The CSV file contains information on each action including RIN, rule title, agency code, agency name, date and year received, date and year completed, rule stage, economic significance (Y/N), major rule status (Y/N), legal deadline, and decision.

|            |  OIRA Review Data        | 
| :--------  | :----------------------- |
| Source:    | [Reginfo.gov Regulatory Review XML Reports](https://www.reginfo.gov/public/do/XMLReportList) |
| Timeframe: | 1981 - The latest available year            |                                                     


## 3. Federal Register Data

## 4. Regulatory Forms Data

## 5. Other Data




 

