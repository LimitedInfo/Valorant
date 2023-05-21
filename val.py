from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import sqlite3
import time
import random


def get_totals(cell):
    return cell.split()[0]


def get_totals_d(cell):
    return cell.split()[1]


def format_dataframe(dataframes, map_num):
    """
    unduplicates data

    :param dataframes: dataframes returned using the pandas read_html function on the page source
    :param map_num: indexed starting at 1 for which map is being played in a series
    :return: formatted df
    """

    if map_num == 1:
        formatting_df = pd.concat(dataframes[:2])
    elif map_num == 2:
        formatting_df = pd.concat([dataframes[4], dataframes[5]])


    elif map_num == 3:
        try:
            formatting_df = pd.concat([dataframes[6], dataframes[7]])
        except IndexError as x:
            print('map 3 link not working')
            return



    formatting_df = formatting_df.reset_index()
    formatting_df = formatting_df.drop(columns=['index', 'Unnamed: 1'])

    def get_opp_team(row, team_column):
        teams = team_column.drop_duplicates()
        for team in teams:
            if team != row['TEAM']:
                return team


    formatting_df.iloc[:, 1:4] = formatting_df.iloc[:, 1:4].applymap(get_totals)
    formatting_df.iloc[:, 5:] = formatting_df.iloc[:, 5:].applymap(get_totals)
    formatting_df['PLAYER'] = formatting_df['Unnamed: 0'].apply(lambda x: ' '.join(x.split()[:-1]))
    formatting_df['TEAM'] = formatting_df['Unnamed: 0'].apply(lambda x: x.split()[-1])
    formatting_df['OPP'] = formatting_df.apply(lambda x: get_opp_team(x, formatting_df['TEAM']), axis=1)

    team_full_name_elements = driver.find_elements(By.CLASS_NAME, value='wf-title-med ')
    formatting_df['TEAM_FULL'] = 0
    formatting_df['TEAM_FULL'].iloc[:5] = team_full_name_elements[0].text
    formatting_df['TEAM_FULL'].iloc[5:] = team_full_name_elements[1].text
    formatting_df['OPP_FULL'] = 0
    formatting_df['OPP_FULL'].iloc[:5] = team_full_name_elements[1].text
    formatting_df['OPP_FULL'].iloc[5:] = team_full_name_elements[0].text

    formatting_df = formatting_df.drop(columns=['Unnamed: 0'])

    formatting_df.iloc[:, 3] = formatting_df.iloc[:, 3].apply(get_totals_d)

    return formatting_df


def get_match_results_data(source):
    """
    :param source: pagesource
    :param link: link for particular match results page
    :return: multiple dataframes of match results, names for images/agent names
    """
    dfs = pd.read_html(source)

    img_elements = driver.find_elements(By.TAG_NAME, value='img')

    # Loop through each image element and extract the "alt" text
    alt_texts = []
    for img_element in img_elements:
        alt_text = img_element.get_attribute('alt')
        if alt_text:
            alt_texts.append(alt_text)


    return dfs, alt_texts


def get_data(driver, map_num, map_name):
    dfs = pd.read_html(driver.page_source)
    df1 = format_dataframe(dfs, map_num)

    #skip if no table is provided
    if df1 is None:
        return

    #define element needed to be searched for team information depending on map number
    # add agents
    dfs, alt_texts = get_match_results_data(driver.page_source)
    relevent_elements = (len(alt_texts) - 2) / 2
    df1['AGENT'] = 0

    if map_num == 1:
        team_nums = [0,1]
        df1['AGENT'] = alt_texts[2:12]
    elif map_num == 2:
        team_nums = [4,5]
        df1['AGENT'] = alt_texts[-20:-10]
    elif map_num == 3:
        team_nums = [8,9]
        df1['AGENT'] = alt_texts[-10:]


    # Get Time/Teams/Map for creating a primary key
    time_of_map = driver.find_element(By.CLASS_NAME, value='moment-tz-convert')
    time_of_map = time_of_map.get_attribute('data-utc-ts')

    # map_name = driver.find_element(By.CLASS_NAME, value='map')
    # print(map_name.text)
    # map_name = map_name.text.split('\n')[0]
    df1['map'] = map_name


    match_score_loser = int(driver.find_element(By.CLASS_NAME, value='match-header-vs-score-loser').text)
    match_score_winner = int(driver.find_element(By.CLASS_NAME, value='match-header-vs-score-winner').text)
    df1['SERIES_SCORE_WINNER'] = match_score_winner
    df1['SERIES_SCORE_LOSER'] = match_score_loser

    patch = driver.find_element(By.XPATH, value='//*[@id="wrapper"]/div[1]/div[3]/div[1]/div[1]/div[2]/div/div[3]/div')
    df1['PATCH'] = patch.text
    unformatted_elos = driver.find_elements(By.CLASS_NAME, value='match-header-link-name-elo')
    elos = [int(x.text.strip('[').strip(']')) for x in unformatted_elos]
    df1['ELO_TEAM'] = 0
    df1['ELO_TEAM'].iloc[:5] = elos[0]
    df1['ELO_TEAM'].iloc[5:] = elos[1]
    df1['ELO_OPP'] = 0
    df1['ELO_OPP'].iloc[:5] = elos[1]
    df1['ELO_OPP'].iloc[5:] = elos[0]

    series_length = driver.find_elements(By.CLASS_NAME, value='match-header-vs-note')[-1].text
    bet_return_winner = driver.find_elements(By.CLASS_NAME, value='match-bet-item-team')[-1].text
    bet_return_amount = int(driver.find_elements(By.CLASS_NAME, value='match-bet-item-odds')[-1].text[1:])

    df1['SERIES_LENGTH'] = series_length
    df1['SERIES_WINNER'] = bet_return_winner
    df1['BET_RETURN'] = bet_return_amount

    #get rounds won and team names
    team_information = driver.find_elements(By.CLASS_NAME, value='vm-stats-game-header')[map_num-1]
    right_team = team_information.find_element(By.CLASS_NAME, value='team.mod-right')
    left_team = team_information.find_element(By.CLASS_NAME, value='team')

    formatted_team_information = right_team.text.split('\n')

    away_team_information = formatted_team_information[0]
    away_rounds_won = formatted_team_information[-1]
    df1['rounds_won'] = 0
    df1['rounds_won'].iloc[5:] = away_rounds_won

    formatted_team_information_home = left_team.text.split('\n')

    home_team_information = formatted_team_information_home[-2]
    home_rounds_won = formatted_team_information_home[0]
    df1['rounds_won'].iloc[:5] = home_rounds_won

    #create primary key
    teams_sorted = [df1['TEAM'].iloc[0], df1['OPP'].iloc[0]]
    teams_sorted.sort()
    df1['match_id'] = teams_sorted[0] + ' ' + teams_sorted[1] + ' ' + map_name + ' ' + time_of_map

    return df1


def import_df_to_sqlite(df, table_name, conn):
    df.to_sql(name=table_name, con=conn, if_exists='append', index=False)


def dataframes_to_sql(dataframes, conn):
    # import the dataframes into the database using the function
    for dataframe in dataframes:
        if dataframe is not None:
            import_df_to_sqlite(dataframe, 'val', conn)


def get_links(matches_path):
    driver = webdriver.Chrome(executable_path=chromedriver_path)


    # navigate to a website
    driver.get(matches_path)

    anchors = driver.find_elements(by=By.CSS_SELECTOR, value='a')

    links = []
    # Iterate over each anchor element and extract the href attribute
    for anchor in anchors:
        href = anchor.get_attribute('href')
        links.append(href)

    return links[14:-10]


def get_data_and_upload(link):
    driver.get(link)


    try:
        more_than_one_map = driver.find_element(By.CLASS_NAME, value='vm-stats-gamesnav.noselect  ')
    except NoSuchElementException:
        print('only one map')
        more_than_one_map = None
    dataframes = []

    if more_than_one_map:
        map_buttons_1 = driver.find_element(By.XPATH,
                                            '//*[@id="wrapper"]/div[1]/div[3]/div[6]/div/div[1]/div[2]/div/div[2]')
        map_buttons_2 = driver.find_element(By.XPATH,
                                            '//*[@id="wrapper"]/div[1]/div[3]/div[6]/div/div[1]/div[2]/div/div[3]')
        map_buttons_3 = driver.find_element(By.XPATH,
                                            '//*[@id="wrapper"]/div[1]/div[3]/div[6]/div/div[1]/div[2]/div/div[4]')
        print(map_buttons_1.text, map_buttons_2.text, map_buttons_3.text)
        map_buttons = [map_buttons_1, map_buttons_2, map_buttons_3]

        for map, button in enumerate(map_buttons):
            if 'N/A' not in button.text:
                button.click()
                df = get_data(driver, map + 1, map_buttons[map].text.split()[1])
                dataframes.append(df)


    else:
        df = get_data(driver, 1, driver.find_element(By.CLASS_NAME, value='map').text.split('\n')[0])
        dataframes.append(df)


    ### Add dataframes into SQLite database
    dataframes_to_sql(dataframes, conn)


# SET PATHS/URLS
conn = sqlite3.connect('valorant.db')
matches_path = 'https://www.vlr.gg/matches/results'
chromedriver_path = r'C:\Users\work\Sportsbetting\Valorant\chromedriver.exe'

driver = webdriver.Chrome(executable_path=chromedriver_path)
driver.get(matches_path)
first_results_page = '/?page=2'

# GET LINKS
# links = []
# for x in range(2, 3):
#     links = links + get_links(matches_path + first_results_page[:-1] + str(x))
# cleaned_links = []
# for link in links:
#     if len(link) < (len(matches_path) + 10):
#         pass
#     else:
#         cleaned_links.append(link)
cleaned_links = ['https://www.vlr.gg/209026/maru-gaming-vs-nongshim-redforce-world-cyber-games-challengers-league-korea-split-2-ubsf/?game=130883&tab=overview']

# GET DATA INTO SQLITE
conn = sqlite3.connect('valorant.db')
for link in cleaned_links:
    try:
        get_data_and_upload(link)
        time.sleep(2.3 + random.random())
    except Exception as n:
        print('match forfeited')
        print(n)

