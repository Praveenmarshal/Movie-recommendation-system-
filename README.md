# Movie-recommendation-system-
Highly rated IMDB movies of now
trending movies that are also Tamil
Here's the code:
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- Configuration ---
# Replace with your actual TMDb API key
TMDB_API_KEY = 'YOUR_TMDB_API_KEY' # MAKE SURE TO REPLACE THIS!
BASE_URL = 'https://api.themoviedb.org/3'
DATA_FILE = 'tamil_trending_movies_data.csv' # Changed filename for trending Tamil movies
TRENDING_TIME_WINDOW = 'week' # 'day' or 'week'

# --- 1. Function to Fetch Trending Tamil Movies from TMDb ---
def fetch_trending_tamil_movies(api_key, time_window, num_pages=5):
    """
    Fetches trending Tamil movies from TMDb API for a given time window.
    Fetches multiple pages to get a good number of movies.
    """
    trending_movies_list = []
    headers = {
        "Accept": "application/json"
    }

    # IMPORTANT CHANGE HERE: Using /trending/movie/{time_window} endpoint
    # We will still filter by original language 'ta'
    # The 'region' parameter usually doesn't apply directly to /trending endpoints
    # but we will try to refine the results by ensuring they are indeed Tamil.
    for page in range(1, num_pages + 1):
        # The /trending endpoint doesn't directly support 'with_original_language'.
        # So, we'll fetch general trending movies and then filter locally.
        # Alternatively, we can use the /discover endpoint, which allows combining filters.
        # Let's use /discover for better control over language and popularity.

        # Using /discover with sort_by popularity and original language
        url = (f"{BASE_URL}/discover/movie?"
               f"api_key={api_key}&"
               f"language=en-US&" # Response language
               f"page={page}&"
               f"sort_by=popularity.desc&" # Sort by popularity for 'trending' feel
               f"with_original_language=ta&" # Filter for Tamil movies
               f"primary_release_date.gte={(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')}&" # Released in last 90 days (approx. trending)
               f"vote_count.gte=10" # Basic vote count to avoid obscure movies with no real trend
              )
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            for movie in data.get('results', []):
                if movie.get('title') and movie.get('vote_count', 0) > 0 and movie.get('vote_average', 0) > 0:
                    trending_movies_list.append({
                        'title': movie['title'],
                        'imdb_rating': movie.get('vote_average', 0.0),
                        'num_votes': movie.get('vote_count', 0),
                        'release_date': movie.get('release_date', ''),
                        'original_language': movie.get('original_language', '')
                    })
            time.sleep(0.1)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from TMDb API (page {page}): {e}")
            break

    return pd.DataFrame(trending_movies_list)

# --- 2. Function to Update or Load Movie Data ---
# This function is adapted to use the new fetching function and DATA_FILE
def load_or_update_movie_data(api_key):
    """
    Loads existing movie data or fetches new trending data.
    Merges new data with existing data, handling duplicates.
    """
    try:
        existing_df = pd.read_csv(DATA_FILE)
        print(f"Loaded existing data with {len(existing_df)} movies from {DATA_FILE}")

        print("Fetching new trending Tamil movies to update the dataset...")
        # Use the specific trending fetch function
        new_movies_df = fetch_trending_tamil_movies(api_key, TRENDING_TIME_WINDOW)

        # Combine existing and new data, remove duplicates favoring the new data
        updated_df = pd.concat([existing_df, new_movies_df]).drop_duplicates(subset='title', keep='first')
        updated_df.to_csv(DATA_FILE, index=False)
        print(f"Updated data with {len(updated_df)} movies.")
        return updated_df

    except FileNotFoundError:
        print(f"'{DATA_FILE}' not found. Fetching initial trending Tamil movie data...")
        # Fetch more pages for initial load of trending data
        initial_df = fetch_trending_tamil_movies(api_key, TRENDING_TIME_WINDOW, num_pages=15)
        if not initial_df.empty:
            initial_df.to_csv(DATA_FILE, index=False)
            print(f"Initial data with {len(initial_df)} movies saved to '{DATA_FILE}'.")
            return initial_df
        else:
            print("Could not fetch initial trending Tamil movie data. Exiting.")
            exit()
    except Exception as e:
        print(f"An error occurred during data loading/updating: {e}")
        exit()


# --- 3. Weighted Recommendation Function (Same as before) ---
def recommend_by_weighted_rating(df, top_n=10, min_votes_threshold=50):
    """
    Recommends movies based on a weighted IMDb-like rating, considering both rating
    and the number of votes.
    """
    if df.empty:
        print("No movie data available for recommendations.")
        return pd.Series([])

    # Ensure necessary columns are numeric and handle potential missing values
    df['imdb_rating'] = pd.to_numeric(df['imdb_rating'], errors='coerce').fillna(0)
    df['num_votes'] = pd.to_numeric(df['num_votes'], errors='coerce').fillna(0)

    # Filter out movies that don't meet the minimum votes threshold
    qualified_movies = df[df['num_votes'] >= min_votes_threshold].copy()

    if qualified_movies.empty:
        print(f"No movies qualify with a minimum of {min_votes_threshold} votes. Adjusting threshold or data might be too small.")
        # Fallback to simple rating if no movies meet weighted criteria
        return df.sort_values(by='imdb_rating', ascending=False)['title'].head(top_n)


    # Calculate the mean rating of all *qualified* movies in the dataset
    C = qualified_movies['imdb_rating'].mean()

    # Calculate the weighted rating for qualified movies
    v = qualified_movies['num_votes']
    R = qualified_movies['imdb_rating']
    m = min_votes_threshold

    qualified_movies['weighted_rating'] = (v / (v + m)) * R + (m / (v + m)) * C

    # Sort movies by their weighted rating in descending order
    recommended_movies = qualified_movies.sort_values(by='weighted_rating', ascending=False)

    # Return the 'title' column of the top_n movies
    return recommended_movies['title'].head(top_n)

# --- Main Execution ---
if __name__ == "__main__":
    if TMDB_API_KEY == 'YOUR_TMDB_API_KEY':
        print("WARNING: Please replace 'YOUR_TMDB_API_KEY' with your actual TMDb API key.")
        print("Get one from: https://www.themoviedb.org/settings/api")
        exit()

    print(f"--- Starting Trending Tamil Movie Recommender Update ({TRENDING_TIME_WINDOW} trends) ---")
    movies_data_df = load_or_update_movie_data(TMDB_API_KEY)
    print("\n--- Generating Recommendations ---")

    # You can adjust top_n and min_votes_threshold here
    top_recommendations = recommend_by_weighted_rating(movies_data_df, top_n=15, min_votes_threshold=50) # Lowered threshold for trending

    if not top_recommendations.empty:
        print(f"Top Recommended Trending Tamil Movies (Weighted Rating, {TRENDING_TIME_WINDOW} trends):")
        for i, title in enumerate(top_recommendations):
            print(f"{i+1}. {title}")
    else:
        print("No trending Tamil recommendations could be generated. This might happen if TMDb doesn't return many highly-rated Tamil movies based on the current filters/thresholds.")


Key Changes and How it Targets "Trending" and "Tamil":
 * DATA_FILE = 'tamil_trending_movies_data.csv': Changed the CSV filename again to reflect the new focus.
 * TRENDING_TIME_WINDOW = 'week': A new configuration variable to easily switch between daily or weekly trends.
 * Modified fetch_trending_tamil_movies function (previously fetch_new_movies):
   * Endpoint Strategy:
     * The direct /trending/movie/{time_window} endpoint on TMDb doesn't have a with_original_language filter.
     * Therefore, I've switched to the more versatile /discover/movie endpoint.
   * /discover/movie with combined filters:
     * sort_by=popularity.desc: This is the primary way to get "trending" results using the discover endpoint. It sorts movies by their popularity score.
     * with_original_language=ta: This ensures we only get movies where the original language is Tamil.
     * primary_release_date.gte={(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')}: This is a crucial addition to capture current trends. It filters movies released within the last 90 days (approximately 3 months). You can adjust 90 to a smaller or larger number to define what "current" means to you.
     * vote_count.gte=10: A small vote count threshold to filter out extremely new or obscure movies with almost no engagement, helping focus on actual "trends."
   * The region=IN parameter is not directly used in the discover endpoint for filtering by release region, but language=en-US still sets the response language.
How to Use:
 * Update your TMDB_API_KEY: Replace 'YOUR_TMDB_API_KEY' with your actual TMDb API key.
 * Save the modified code as a new Python file (e.g., tamil_trending_recommender.py).
 * Delete the old CSV files (movies_data.csv and tamil_movies_data.csv) if they exist, to ensure you start fresh with only trending Tamil movie data.
 * Run the script: python tamil_trending_recommender.py
This version should provide a list of Tamil movies that are currently popular and have been released relatively recently, giving you a good sense of "trending" within the Tamil film industry on TMDb. You can experiment with the primary_release_date.gte days (e.g., 30 for very recent, 180 for a broader recent period) and min_votes_threshold to fine-tune the results.
