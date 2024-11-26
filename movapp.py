from flask import Flask, request, jsonify, render_template, abort
from db_handler import DatabaseManager
from flask_cors import CORS
from datetime import datetime
import json

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
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
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        from_ = (page - 1) * size

        # Build search query
        search_query = {
            "bool": {
                "must": [],
                "filter": []
            }
        }

        # Add text search if query provided
        if query:
            search_query["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "plot_summary", "cast", "director"],
                    "fuzziness": "AUTO"
                }
            })
        else:
            search_query["bool"]["must"].append({"match_all": {}})

        # Add filters
        for field, value in {
            "genres": request.args.get('genre'),
            "language": request.args.get('language'),
            "content_rating": request.args.get('content_rating'),
            "director": request.args.get('director')
        }.items():
            if value:
                search_query["bool"]["filter"].append({
                    "term": {field: value}
                })

        # Execute search
        response = db_manager.es.search(
            index="movies",
            body={
                "query": search_query,
                "from": from_,
                "size": size,
                "sort": [
                    "_score",
                    {"popularity_score": {"order": "desc"}}
                ],
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

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
        app.run(debug=True, port=5000, host='0.0.0.0')
        # For production, use this instead:
        # app.run(port=5000, host='0.0.0.0')
    else:
        print("Failed to initialize application")