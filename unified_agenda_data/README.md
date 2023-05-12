## Unified Agenda data

The Python code in this folder downloads [XML reports of the Unified Agenda](https://www.reginfo.gov/public/do/eAgendaXmlReport) from Reginfo.gov and converts them into a CSV file. The Unified Agenda has been published semiannually since Fall 1995 (except 2012 in which the Unified Agenda was only published once). The user can specify which Unified Agenda reports to download by entering the start year and season and end year and season while running the code. Based on the user input, the corresponding XML reports will be automatically downloaded to the specified directory and converted into a single CSV file with the following columns:

| Column |  Description                                                           | 
| :-------- | :-----------------------------------------------------------------------------|
| agenda_date  | Publication date of the Unified Agenda in which the rulemaking action was published  |
| RIN | Regulation Identifier Number (RIN)  |
| agency_code |   Agency code                                                                       | 
| agency_name | Agency name                                                                            |
| department_code | Department code                                        |
| deparment_name | Department name | 
| rule_title   |  Title of the rulemaking action           |
| abstract  | Abstract of the rulemaking action |
| priority  | Significance designation of the rulemaking action as defined in Executive Order 12866 (e.g., economically significant, other significant) |
| RIN_status  | Whether the rulemaking action was first time or previously published in the Unified Agenda  |
| rule_stage | Stage of the rulemaking action (e.g., proposed rule stage, final rule stage) | 
| major |   Whether the rulemaking action is designated as a major rule as defined in the Congressional Review Act  |
| CFR | The CFR parts that the rulemaking action adds or amends (Yes/No/Undetermined) |
| legal_authority | The public law or U.S. code that authorizes the rulemaking action |
| legal_deadline |	Legal deadlines for the rulemaking action (if any); multiple columns if there are multiple deadlines    |
| action |	Actions since the rulemaking was initiated until the Unified Agenda was published (e.g., NPRM and its publication date and FR cite); multiple columns if there are multiple actions |
