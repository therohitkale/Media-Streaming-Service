from flask import Flask, request, jsonify, render_template, abort
from db_handler import DatabaseManager
from flask_cors import CORS
from datetime import datetime
import json
from sentence_transformers import SentenceTransformer

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Load the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

CORS(app)  # Enable CORS for all routes

# Initialize database manager
db_manager = DatabaseManager()

# Routes for UI rendering
@app.route('/')
def home():
    """Render the home page"""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Render the search page"""
    query = request.args.get('q', '')
    return render_template('search.html', query=query)

@app.route('/movie/<movie_id>')
def movie_page(movie_id):
    """Render the movie details page"""
    movie = db_manager.get_movie_details(movie_id)
    if movie:
        return render_template('movie_details.html', movie=movie)
    abort(404)

# API Routes
@app.route('/api/movies/search', methods=['GET'])
def search_movies():
    """API endpoint for searching movies"""
    try:
        query = request.args.get('query', '')
        semantic = request.args.get('semantic', 'false')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        from_ = (page - 1) * size
        sort = request.args.get('sort', '')
        yearFrom = request.args.get('yearFrom', 0)
        yearTo = request.args.get('yearTo', 0)

        # Build search query
        search_query = {
            "bool": {
                "must": [],
                "filter": []
            }
        }

        # Add text search if query provided
        if query:
            if semantic == 'true':
                query_embedding = model.encode(query).tolist()
                search_query['bool']['must'].append({
                    'knn': {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": 10,
                        "num_candidates": 100,
                    }
                })
            else:
                search_query["bool"]["must"].append({
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "plot_summary", "cast", "director"],
                        "fuzziness": "AUTO"
                    }
                })
        else:
            search_query["bool"]["must"].append({"match_all": {}})

        if yearFrom and yearTo:
            search_query["bool"]["filter"].append({
                "range": {
                    "release_date": {
                        "gte": yearFrom,
                        "lte": yearTo,
                        "format": "yyyy"
                    }
                }
            })

        # Add filters
        for field, value in {
            "genres": request.args.get('genres', '').split(','),
            "language": request.args.get('languages', '').split(','),
            "content_rating": request.args.get('contentRating'),
            "director": request.args.get('director'),
            "average_rating": request.args.get('rating')
        }.items():
            if type(value) == list:
                value = [val for val in value if val]
                if len(value):
                    search_query["bool"]["filter"].append({
                        "terms": {field: value}
                    })
            elif value:
                search_query["bool"]["filter"].append({
                    "term": {field: value}
                })

        # Execute search
        body = {
                "query": search_query,
                "from": from_,
                "size": size,
                "sort": [],
                "aggs": {
                    "genres": {
                        "terms": {
                            "field": "genres",
                            "size": 20
                        }
                    },
                    "languages": {
                        "terms": {
                            "field": "language",
                            "size": 10
                        }
                    },
                    "content_ratings": {
                        "terms": {
                            "field": "content_rating",
                            "size": 10
                        }
                    },
                    "directors": {
                        "terms": {
                            "field": "director",
                            "size": 20
                        }
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {},
                        "plot_summary": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            }
    
        if not sort or sort == 'popularity':
            body['sort'] = [
                "_score",
                {"popularity_score": {"order": "desc"}}
            ]
        else:
            body["sort"] = [{sort: {"order": "asc"}}]
        response = db_manager.es.search(
            index="movies",
            body=body
        )

        # Convert Elasticsearch response to dictionary
        results = {
            "hits": {
                "total": {
                    "value": response["hits"]["total"]["value"],
                    "relation": response["hits"]["total"]["relation"]
                },
                "hits": []
            },
            "aggregations": {}
        }

        # Process hits
        for hit in response["hits"]["hits"]:
            processed_hit = {
                "_id": hit["_id"],
                "_score": hit["_score"],
                "_source": hit["_source"]
            }
            if "highlight" in hit:
                processed_hit["highlight"] = hit["highlight"]
            results["hits"]["hits"].append(processed_hit)

        # Process aggregations
        if "aggregations" in response:
            results["aggregations"] = {
                key: {
                    "buckets": agg["buckets"]
                }
                for key, agg in response["aggregations"].items()
            }

        return jsonify(results)

    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/movies/<movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    """API endpoint for getting movie details"""
    try:
        movie = db_manager.get_movie_details(movie_id)
        if movie:
            return jsonify(movie)
        return jsonify({"error": "Movie not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/movies/load-sample-data', methods=['POST'])
def load_sample_data():
    """API endpoint for loading sample data"""
    try:
        result = db_manager.load_sample_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/genres', methods=['GET'])
def get_genres():
    """API endpoint for getting all genres"""
    try:
        genres = db_manager.get_all_genres()
        return jsonify(genres)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trending', methods=['GET'])
def get_trending():
    """API endpoint for getting trending movies"""
    try:
        size = int(request.args.get('size', 10))
        trending = db_manager.get_trending_movies(size)
        return jsonify(trending)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommendations/<movie_id>', methods=['GET'])
def get_recommendations(movie_id):
    """API endpoint for getting movie recommendations"""
    try:
        size = int(request.args.get('size', 5))
        recommendations = db_manager.get_recommendations(movie_id, size)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/movies/by-genre/<genre>', methods=['GET'])
def get_movies_by_genre(genre):
    """API endpoint for getting movies by genre"""
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        movies = db_manager.get_movies_by_genre(genre, page, size)
        return jsonify(movies)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/cassandra/movie', methods=['POST'])
def insert_movie_cassandra():
    """
    Insert a movie playback event into the Cassandra table.
    """
    try:
        data = request.get_json()
        bucket = data.get('bucket')  # e.g., "2024-W47"
        movie_id = data.get('movie_id')  # UUID format
        print(bucket, movie_id)
        
        if not bucket or not movie_id:
            return jsonify({"error": "Missing bucket or movie_id"}), 400
        
        # Check if the movie already exists in this bucket
        check_query = "SELECT play_count FROM trending_movies WHERE bucket = %s AND movie_id = %s"
        rows = db_manager.cassandra_session.execute(check_query, (bucket, movie_id))
        
        row = rows.one()
        if row:  # Movie exists
            # Increment play_count manually
            current_play_count = row.play_count
            new_play_count = current_play_count + 1
            
            update_query = """
            UPDATE trending_movies SET play_count = %s WHERE bucket = %s AND movie_id = %s
            """
            db_manager.cassandra_session.execute(update_query, (new_play_count, bucket, movie_id))
        else:  # Movie does not exist
            # Insert a new row with play_count = 1
            insert_query = """
            INSERT INTO trending_movies (bucket, movie_id, play_count) VALUES (%s, %s, %s)
            """
            db_manager.cassandra_session.execute(insert_query, (bucket, movie_id, 1))
        
        return jsonify({"message": "Movie playback event processed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/cassandra/top10_this_week', methods=['GET'])
def top10_this_week():
    """
    Retrieve the top 10 trending movies for the current week.
    """
    try:
        # Get the current week in ISO format (e.g., "2024-W47")
        current_week = datetime.now().strftime("%Y-W%U")
        
        # Query Cassandra for the current week's movies
        query = "SELECT movie_id, play_count FROM trending_movies WHERE bucket = %s"
        rows = db_manager.cassandra_session.execute(query, (current_week,))

        # Sort movies by play_count in descending order and take the top 10
        top_movies = sorted(
            [{"movie_id": str(row.movie_id), "play_count": row.play_count} for row in rows],
            key=lambda x: x['play_count'],
            reverse=True
        )[:10]

        # Fetch detailed movie information for each movie_id
        detailed_movies = []
        for movie in top_movies:
            movie_details = db_manager.get_movie_details(movie["movie_id"])
            if movie_details:
                movie_details["play_count"] = movie["play_count"]  # Add play_count to details
                detailed_movies.append(movie_details)

        return jsonify(detailed_movies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cassandra/top10_all_time', methods=['GET'])
def top10_all_time():
    """
    Retrieve the top 10 all-time trending movies.
    """
    try:
        # Query all rows from the table
        query = "SELECT bucket, movie_id, play_count FROM trending_movies"
        rows = db_manager.cassandra_session.execute(query)

        # Aggregate play_count across all buckets
        movie_aggregates = {}
        for row in rows:
            if row.movie_id not in movie_aggregates:
                movie_aggregates[row.movie_id] = 0
            movie_aggregates[row.movie_id] += row.play_count

        # Get the top 10 movies sorted by play_count
        top_movies = sorted(
            movie_aggregates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Format the result
        result = [{"movie_id": str(movie_id), "play_count": play_count} for movie_id, play_count in top_movies]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
# @app.errorhandler(404)
# def not_found_error(error):
#     return render_template('404.html'), 404

# @app.errorhandler(500)
# def internal_error(error):
#     return render_template('500.html'), 500

def init_application():
    """Initialize the application by setting up databases and loading initial data if needed"""
    try:
        # Create PostgreSQL tables
        print("Checking PostgreSQL connection...")
        db_manager.init_postgres()
        print("PostgreSQL tables created successfully")
        
        # Initialize Elasticsearch
        print("Checking Elasticsearch connection...")
        if not db_manager.es.indices.exists(index="movies"):
            db_manager.init_elasticsearch()
            print("Elasticsearch index created successfully")
        
        # Check if data exists
        movie_count = db_manager.get_movie_count()
        
        if movie_count == 0:
            print("No data found. Loading sample data...")
            result = db_manager.load_sample_data()
            print(result)
        else:
            print(f"Found {movie_count} existing movies in database")

        print("Checking Cassandra connection...")
        db_manager.init_cassandra()
        print("Cassandra tables created successfully")
            
        return True
    except Exception as e:
        print(f"Error initializing application: {str(e)}")
        return False

# Custom template filters
@app.template_filter('format_date')
def format_date(date_str):
    """Format date string to readable format"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%B %d, %Y')
    except:
        return date_str

@app.template_filter('format_runtime')
def format_runtime(minutes):
    """Format runtime minutes to hours and minutes"""
    try:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{remaining_minutes}m"
    except:
        return f"{minutes} minutes"

@app.template_filter('format_money')
def format_money(amount):
    """Format money amount with commas and dollar sign"""
    try:
        return f"${amount:,.2f}"
    except:
        return amount

if __name__ == '__main__':
    print("Initializing Media Streaming Service...")
    if init_application():
        print("Initialization successful - Starting server...")
        # For development
        app.run(debug=True, port=5002, host='0.0.0.0')
        # For production, use this instead:
        # app.run(port=5000, host='0.0.0.0')
    else:
        print("Failed to initialize application")
