import streamlit as st
from espn_api.football import League
import pandas as pd
import nfl_data_py as nfl
LEAGUE_ID = 1918224288
YEAR = 2024

def load_nfl_data(year):
    df = nfl.import_pbp_data([year])
    df['week'] = df['week'].astype(int)
    return df[['passer_player_name', 'receiver_player_name', 'rusher_player_name', 'yards_gained', 'rush_touchdown', 'pass_touchdown', 'week']]

def get_player_team_in_week(league, player_id, week):
    for team in league.teams:
        roster = team.roster
        for player in roster:
            if player.playerId == player_id:
                # Check if the player was in the starting lineup for that week
                box_scores = league.box_scores(week)
                for matchup in box_scores:
                    if player in matchup.home_lineup or player in matchup.away_lineup:
                        return team.team_name
    return None

def get_league_data(league, selected_week):
    current_week = league.current_week
    matchups = league.box_scores(selected_week)
    teams = league.teams
    return current_week, matchups, teams

def get_league_median_score(teams, week):
    scores = [team.scores[week-1] for team in teams if week <= len(team.scores)]
    return pd.Series(scores).median()

def get_season_high_score(teams, current_week):
    all_scores = [team.scores[week-1] for team in teams for week in range(1, current_week+1) if week <= len(team.scores)]
    max_score = max(all_scores)
    max_team = next(team for team in teams for score in team.scores if score == max_score)
    return max_score, max_team.team_name

def get_weekly_high_scores(league, current_week):
    weekly_high_scores = []
    for week in range(1, 15):  # Weeks 1-14
        if week <= current_week:
            matchups = league.box_scores(week)
            high_score = max(max(m.home_score, m.away_score) for m in matchups)
            high_scorer = next(m.home_team if m.home_score == high_score else m.away_team for m in matchups if max(m.home_score, m.away_score) == high_score)
            weekly_high_scores.append(f"{high_scorer.team_name}: {high_score:.2f}")
        else:
            weekly_high_scores.append(f"Week {week}")
    return weekly_high_scores

def get_survivor_data(league, current_week):
    eliminated_teams = set()
    survivor_data = []
    for week in range(1, 15):  # Weeks 1-14
        if week <= current_week:
            matchups = league.box_scores(week)
            all_scores = [(m.home_team, m.home_score) for m in matchups] + [(m.away_team, m.away_score) for m in matchups]
            eligible_scores = [(team, score) for team, score in all_scores if team.team_name not in eliminated_teams]
            if eligible_scores:
                lowest_team, lowest_score = min(eligible_scores, key=lambda x: x[1])
                survivor_data.append(f"{lowest_team.team_name}: {lowest_score:.2f}")
                eliminated_teams.add(lowest_team.team_name)
            else:
                survivor_data.append("No eligible teams")
        else:
            survivor_data.append(f"Week {week}")
    return survivor_data


def get_team_avatar_url(team):
    """Extract the avatar URL from the team object."""
    if team.logo_url:
        return team.logo_url
    return "https://example.com/default-avatar.png"  # Replace with a default avatar URL

def get_unlucky_teams(teams):
    points_against = [(team.team_name, team.points_against) for team in teams]
    return sorted(points_against, key=lambda x: x[1], reverse=True)[:3]

def format_standings(teams):
    west_teams = [team for team in teams if team.division_name == 'West']
    east_teams = [team for team in teams if team.division_name == 'East']
    west_data = [(get_team_avatar_url(team), team.team_name, f"{team.wins}-{team.losses}") for team in west_teams]
    east_data = [(get_team_avatar_url(team), team.team_name, f"{team.wins}-{team.losses}") for team in east_teams]
    max_len = max(len(west_data), len(east_data))
    west_data += [('', '', '')] * (max_len - len(west_data))
    east_data += [('', '', '')] * (max_len - len(east_data))
    return pd.DataFrame({
        'West Avatar': [avatar for avatar, _, _ in west_data],
        'West': [team for _, team, _ in west_data],
        'West Record': [record for _, _, record in west_data],
        'East Avatar': [avatar for avatar, _, _ in east_data],
        'East': [team for _, team, _ in east_data],
        'East Record': [record for _, _, record in east_data]
    })


def format_matchups(matchups):
    formatted_matchups = []
    for m in matchups:
        formatted_matchups.append({
            'Team1Avatar': get_team_avatar_url(m.home_team),
            'Team1Name': m.home_team.team_name,
            'Team1Score': f"{m.home_score:.2f}",
            'Team2Score': f"{m.away_score:.2f}",
            'Team2Name': m.away_team.team_name,
            'Team2Avatar': get_team_avatar_url(m.away_team)
        })
    return pd.DataFrame(formatted_matchups)

def main():
    st.set_page_config(layout="wide")
    
    # Initialize the League
    league = League(league_id=LEAGUE_ID, year=YEAR)
    current_week = league.current_week
    

    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.title("Shreve Fantasy League")
        
            # Load NFL data
        nfl_data = load_nfl_data(YEAR)
        # longest_tds = get_longest_tds(nfl_data)
        # Week selection
        selected_week = st.selectbox("Select Week", range(1, current_week + 1), index=current_week - 1)
        
        st.subheader(f"Week {selected_week}")
        
        _, matchups, teams = get_league_data(league, selected_week)
        
        # League Median Score
        median_score = get_league_median_score(teams, selected_week)
        st.metric("League Median Score", f"{median_score:.2f}")
        
        # Matchups Table
        if selected_week == current_week:
            st.subheader("This Week's Matchups")
        else:
            st.subheader(f"Week {selected_week} Matchups")
        
        matchups_df = format_matchups(matchups)
        st.dataframe(matchups_df, hide_index=True, column_config={
            "Team1Avatar": st.column_config.ImageColumn("", width="small"),
            "Team1Name": st.column_config.TextColumn("", width="medium"),
            "Team1Score": st.column_config.TextColumn("", width="small"),
            "Team2Score": st.column_config.TextColumn("", width="small"),
            "Team2Name": st.column_config.TextColumn("", width="medium"),
            "Team2Avatar": st.column_config.ImageColumn("", width="small")
        })
        
        # Standings Table
        st.subheader("Standings")
        standings_df = format_standings(league.standings())
        st.dataframe(standings_df, hide_index=True, column_config={
            "West Avatar": st.column_config.ImageColumn("", width="small"),
            "West": st.column_config.TextColumn("West", width="medium"),
            "West Record": st.column_config.TextColumn("Record", width="small"),
            "East Avatar": st.column_config.ImageColumn("", width="small"),
            "East": st.column_config.TextColumn("East", width="medium"),
            "East Record": st.column_config.TextColumn("Record", width="small")
        })
        
    # Right Column
    with right_col:
        st.header("Prize Tracker")
        
        # Season High Score
        st.subheader("Current Season High Score ($25)")
        season_high_score, high_score_team = get_season_high_score(league.teams, current_week)
        st.metric(f"{high_score_team}", f"{season_high_score:.2f}")

        # Weekly High Scores Table
        st.subheader("Weekly High Scores ($10/week)")
        with st.expander("View Weekly High Scorers"):
            weekly_high_scores = get_weekly_high_scores(league, current_week)
            weeks_1_7 = weekly_high_scores[:7]
            weeks_8_14 = weekly_high_scores[7:]
            weekly_scores_df = pd.DataFrame({
                "Weeks 1-7": weeks_1_7,
                "Weeks 8-14": weeks_8_14
            })
            st.dataframe(weekly_scores_df, hide_index=True)

        # Survivor Table
        st.subheader("Survivor ($10)")
        with st.expander("View Survivor Eliminations"):
            survivor_data = get_survivor_data(league, current_week)
            survivor_1_7 = survivor_data[:7]
            survivor_8_14 = survivor_data[7:]
            survivor_df = pd.DataFrame({
                "Weeks 1-7": survivor_1_7,
                "Weeks 8-14": survivor_8_14
            })
            st.dataframe(survivor_df, hide_index=True)

        # Unlucky Teams
        st.subheader("Unlucky ($10)")
        with st.expander("View Unlucky Contenders"):
            unlucky_teams = get_unlucky_teams(league.teams)
            for i, (team_name, points_against) in enumerate(unlucky_teams, 1):
                st.markdown(f"{i}. {team_name}: {points_against:.2f}")



if __name__ == "__main__":
    main()