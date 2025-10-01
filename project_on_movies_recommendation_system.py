import pandas as pd
import requests
import time
from datetime import datetime, timedelta

TMDB_API_KEY = 'e80b945a8e2d319f84ad5347f1d4257f'
BASE_URL = 'https://api.themoviedb.org/3'
DATA_FILE = 'movies_data.csv'

def fetch_new_movies(api_key, num_pages=5):
    """
    Fetches the latest popular movies from TMDb API.
    Fetches multiple pages to get a good number of recent movies.
    """
    new_movies_list = []
    headers = {
        "Accept": "application/json"
    }

    for page in range(1, num_pages + 1):
        url = f"{BASE_URL}/movie/now_playing?api_key={api_key}&language=en-US&page={page}&region=IN"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            for movie in data.get('results', []):
                if movie.get('title') and movie.get('vote_count', 0) > 0 and movie.get('vote_average', 0) > 0:
                    new_movies_list.append({
                        'title': movie['title'],
                        'imdb_rating': movie.get('vote_average', 0.0),
                        'num_votes': movie.get('vote_count', 0),
                        'release_date': movie.get('release_date', '')
                    })
            time.sleep(0.1)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from TMDb API (page {page}): {e}")
            break

    return pd.DataFrame(new_movies_list)

def load_or_update_movie_data(api_key):
    """
    Loads existing movie data or fetches new data if the file doesn't exist
    or is too old. Merges new data with existing data, handling duplicates.
    """
    try:
        existing_df = pd.read_csv(DATA_FILE)
        print(f"Loaded existing data with {len(existing_df)} movies from {DATA_FILE}")

        print("Fetching new movies to update the dataset...")
        new_movies_df = fetch_new_movies(api_key)
        
        updated_df = pd.concat([existing_df, new_movies_df]).drop_duplicates(subset='title', keep='first')
        updated_df.to_csv(DATA_FILE, index=False)
        print(f"Updated data with {len(updated_df)} movies.")
        return updated_df

    except FileNotFoundError:
        print(f"'{DATA_FILE}' not found. Fetching initial movie data...")
        initial_df = fetch_new_movies(api_key, num_pages=10) 
        if not initial_df.empty:
            initial_df.to_csv(DATA_FILE, index=False)
            print(f"Initial data with {len(initial_df)} movies saved to '{DATA_FILE}'.")
            return initial_df
        else:
            print("Could not fetch initial movie data. Exiting.")
            exit()
    except Exception as e:
        print(f"An error occurred during data loading/updating: {e}")
        exit()


def recommend_by_weighted_rating(df, top_n=10, min_votes_threshold=50):
    """
    Recommends movies based on a weighted IMDb-like rating, considering both rating
    and the number of votes.
    """
    if df.empty:
        print("No movie data available for recommendations.")
        return pd.Series([])

    df['imdb_rating'] = pd.to_numeric(df['imdb_rating'], errors='coerce').fillna(0)
    df['num_votes'] = pd.to_numeric(df['num_votes'], errors='coerce').fillna(0)

    qualified_movies = df[df['num_votes'] >= min_votes_threshold].copy()

    if qualified_movies.empty:
        print(f"No movies qualify with a minimum of {min_votes_threshold} votes. Adjusting threshold or data might be too small.")
        return df.sort_values(by='imdb_rating', ascending=False)['title'].head(top_n)


    C = qualified_movies['imdb_rating'].mean()

    v = qualified_movies['num_votes']
    R = qualified_movies['imdb_rating']
    m = min_votes_threshold

    qualified_movies['weighted_rating'] = (v / (v + m)) * R + (m / (v + m)) * C

    recommended_movies = qualified_movies.sort_values(by='weighted_rating', ascending=False)

    return recommended_movies['title'].head(top_n)

if __name__ == "__main__":
    if TMDB_API_KEY == 'YOUR_TMDB_API_KEY':
        print("WARNING: Please replace 'YOUR_TMDB_API_KEY' with your actual TMDb API key.")
        print("Get one from: https://www.themoviedb.org/settings/api")
        exit()

    print("--- Starting Movie Recommender Update ---")
    movies_data_df = load_or_update_movie_data(TMDB_API_KEY)
    print("\n--- Generating Recommendations ---")
    
    top_recommendations = recommend_by_weighted_rating(movies_data_df, top_n=15, min_votes_threshold=100)
    
    if not top_recommendations.empty:
        print("Top Recommended Movies (Weighted Rating):")
        for i, title in enumerate(top_recommendations):
            print(f"{i+1}. {title}")
    else:
        print("No recommendations could be generated.")

