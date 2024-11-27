from sqlalchemy import create_engine, Column, Integer, String, Float, ARRAY, JSON, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import random
import json
from sentence_transformers import SentenceTransformer

# Database configurations
POSTGRES_URL = "postgresql://postgres:password@localhost/moviedb"
ES_HOST = "https://192.168.0.47:9200"
ES_USER = "elastic"
ES_PASSWORD = "39bTYqJEnp4bShv8cuiq"

# Load the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

Base = declarative_base()

class MovieMetadata(Base):
    __tablename__ = "movie_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(String, unique=True, index=True)
    title = Column(String)
    plot_summary = Column(Text)
    release_date = Column(Date)
    runtime = Column(Integer)
    budget = Column(Float)
    revenue = Column(Float)
    genres = Column(ARRAY(String))
    production_companies = Column(ARRAY(String))
    cast = Column(ARRAY(String))
    director = Column(String)
    keywords = Column(ARRAY(String))
    streaming_url = Column(String)
    trailer_url = Column(String)
    poster_url = Column(String)
    imdb_rating = Column(Float)
    content_rating = Column(String)
    language = Column(String)
    popularity_score = Column(Float)
    views = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)

class DatabaseManager:
    def __init__(self):
        # Initialize PostgreSQL
        self.engine = create_engine(POSTGRES_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize Elasticsearch
        self.es = Elasticsearch(
            ES_HOST,
            basic_auth=(ES_USER, ES_PASSWORD),
            verify_certs=False,
            ssl_show_warn=False
        )
        
        print("Database connections initialized")

    def init_postgres(self):
        """Initialize PostgreSQL database"""
        Base.metadata.create_all(bind=self.engine)

    def init_elasticsearch(self):
        """Initialize Elasticsearch index with mapping"""
        movies_mapping = {
            "mappings": {
                "properties": {
                    "movie_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "plot_summary": {"type": "text"},
                    "release_date": {"type": "date"},
                    "genres": {"type": "keyword"},
                    "cast": {"type": "keyword"},
                    "director": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "content_rating": {"type": "keyword"},
                    "imdb_rating": {"type": "float"},
                    "popularity_score": {"type": "float"},
                    "views": {"type": "integer"},
                    "average_rating": {"type": "float"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": "true",
                        "similarity": "cosine",
                    }
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard"
                        }
                    }
                },
                "index": {
                    "number_of_shards": 5,
                    "number_of_replicas": 3
                }
            }
        }
        
        if not self.es.indices.exists(index="movies"):
            self.es.indices.create(index="movies", body=movies_mapping)

    def generate_sample_data(self, num_records=200):
        """Generate sample movie records"""
        # Sample data pools
        titles = ["The Adventure", "Mystery of the", "Journey to", "Tales of", "The Last", "Rise of the", 
                 "Beyond the", "Legend of", "Return to", "Escape from"]
        adjectives = ["Lost", "Hidden", "Ancient", "Dark", "Eternal", "Golden", "Sacred", "Secret", 
                     "Mysterious", "Forgotten"]
        nouns = ["Kingdom", "World", "Paradise", "Empire", "Planet", "Galaxy", "Realm", "Mountain", 
                 "Ocean", "Forest"]
        
        genres = ["Action", "Drama", "Comedy", "Sci-Fi", "Horror", "Romance", "Thriller", 
                 "Adventure", "Fantasy", "Animation"]
        languages = ["English", "Spanish", "French", "Japanese", "Korean", "Chinese", "German"]
        content_ratings = ["G", "PG", "PG-13", "R"]
        companies = ["Universal", "Warner Bros", "Paramount", "Sony Pictures", "Disney", 
                    "Lionsgate", "Netflix", "Amazon Studios"]
        
        actor_pool = ["Tom Hanks", "Brad Pitt", "Leonardo DiCaprio", "Meryl Streep", 
                     "Jennifer Lawrence", "Robert Downey Jr", "Emma Stone", "Morgan Freeman",
                     "Scarlett Johansson", "Chris Evans", "Samuel L. Jackson", "Anne Hathaway"]
        
        director_pool = ["Christopher Nolan", "Martin Scorsese", "Steven Spielberg", 
                        "Quentin Tarantino", "James Cameron", "Peter Jackson", "Ridley Scott",
                        "Denis Villeneuve", "David Fincher", "Greta Gerwig"]

        sample_movies = []
        
        for i in range(1, num_records + 1):
            # Generate random title
            title = f"{random.choice(titles)} {random.choice(adjectives)} {random.choice(nouns)}"
            movie_id = f"mov_{i}"
            
            # Generate random date within last 20 years
            days_back = random.randint(0, 365 * 20)
            release_date = datetime.now() - timedelta(days=days_back)
            random_summaries = [
                'In a world on the brink of chaos, a scientist discovers a hidden formula that could save humanity. As time runs out, she must confront her past and battle ruthless enemies to protect the future.',
                'A young archaeologist stumbles upon ancient ruins that hold the secret to a forgotten civilization. As she deciphers the mysteries, she awakens forces that threaten to destroy the world.',
                'A musician struggling with loss finds solace in an unexpected friendship with a mysterious stranger. Together, they discover the healing power of music and the strength to move forward.',
                'An astronaut embarks on a perilous mission to explore a distant galaxy, only to uncover a conspiracy that shakes the foundation of everything humanity believes in.',
                'A skilled thief assembles a team of misfits for one last score, but betrayal and unforeseen challenges turn the heist into a desperate fight for survival.',
                'Haunted by a tragic event, a detective returns to her hometown to solve a series of chilling murders. As secrets unravel, she must face the ghosts of her own history.',
                'A struggling artist discovers a portal to a dream world where imagination comes to life. But when dreams turn into nightmares, he must confront his fears to escape.',
                'A retired war veteran is forced back into action when his small town is threatened by a dangerous gang. Against all odds, he rises to protect the people he loves.',
                'In a futuristic world, a programmer creates an AI to save lives, but the creation evolves beyond control. Now, she must team up with unlikely allies to stop a technological uprising.',
                'A young girl discovers a magical forest hidden from the modern world, filled with mythical creatures. But when the forest is threatened, she must become its unlikely guardian.'
            ]
            
            # Generate random movie data
            movie = {
                "movie_id": movie_id,
                "title": title,
                "plot_summary": f"In this compelling story, {random.choice(actor_pool)} stars as the protagonist who must overcome incredible odds in a world where nothing is as it seems." if i > 10 else random_summaries[i-1],
                "release_date": release_date.strftime("%Y-%m-%d"),
                "runtime": random.randint(90, 180),
                "budget": round(random.uniform(1000000, 200000000), 2),
                "revenue": round(random.uniform(5000000, 500000000), 2),
                "genres": random.sample(genres, random.randint(1, 3)),
                "production_companies": random.sample(companies, random.randint(1, 2)),
                "cast": random.sample(actor_pool, random.randint(3, 5)),
                "director": random.choice(director_pool),
                "keywords": [f"keyword_{random.randint(1, 20)}" for _ in range(5)],
                "streaming_url": f"https://stream.example.com/movie/{movie_id}",
                "trailer_url": f"https://trailers.example.com/{movie_id}",
                "poster_url": f"/static/images/posters/movie{random.randint(1, 10)}.jpg",
                "imdb_rating": round(random.uniform(5.0, 9.5), 1),
                "content_rating": random.choice(content_ratings),
                "language": random.choice(languages),
                "popularity_score": round(random.uniform(1, 100), 2),
                "views": random.randint(1000, 1000000),
                "average_rating": round(random.uniform(3.0, 5.0), 1)
            }
            
            sample_movies.append(movie)
            
        return sample_movies

    def load_sample_data(self):
        """Load sample data into both PostgreSQL and Elasticsearch"""
        db = self.SessionLocal()
        sample_movies = self.generate_sample_data()
        
        try:
            # Load into PostgreSQL
            for movie in sample_movies:
                db_movie = MovieMetadata(**movie)
                db.add(db_movie)
            
            db.commit()
            
            # Load into Elasticsearch
            for movie in sample_movies:
                movie['embedding'] = model.encode(movie["plot_summary"]).tolist()
                self.es.index(index="movies", id=movie["movie_id"], document=movie)
                
            return {"message": f"Successfully loaded {len(sample_movies)} sample movies"}
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def search_movies(self, query=None, filters=None, page=1, size=10):
    
        try:
            from_ = (page - 1) * size
            
            # Build base query
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
                # Add semantic search
                query_embedding = model.encode(query).tolist()
                search_query['bool']['must'].append({
                    "script_score": {
                        "query": {
                        "match_all": {}
                        },
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {
                                "query_vector": query_embedding
                            }
                        }
                    }
                })
            else:
                search_query["bool"]["must"].append({"match_all": {}})

            # Add filters
            if filters:
                for field, value in filters.items():
                    if value:
                        search_query["bool"]["filter"].append({
                            "term": {field: value}
                        })

            # Execute search
            response = self.es.search(
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
            
            # Convert response to dictionary
            response_dict = response.body
            return response_dict

        except Exception as e:
            print(f"Search error in DatabaseManager: {str(e)}")
            raise e
        
    def get_movie_details(self, movie_id):
        """Get detailed movie information from PostgreSQL"""
        db = self.SessionLocal()
        try:
            movie = db.query(MovieMetadata).filter(MovieMetadata.movie_id == movie_id).first()
            if movie:
                return {
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "plot_summary": movie.plot_summary,
                    "release_date": movie.release_date.strftime("%Y-%m-%d"),
                    "runtime": movie.runtime,
                    "budget": movie.budget,
                    "revenue": movie.revenue,
                    "genres": movie.genres,
                    "production_companies": movie.production_companies,
                    "cast": movie.cast,
                    "director": movie.director,
                    "keywords": movie.keywords,
                    "streaming_url": movie.streaming_url,
                    "trailer_url": movie.trailer_url,
                    "poster_url": movie.poster_url,
                    "imdb_rating": movie.imdb_rating,
                    "content_rating": movie.content_rating,
                    "language": movie.language,
                    "popularity_score": movie.popularity_score,
                    "views": movie.views,
                    "average_rating": movie.average_rating
                }
            return None
        finally:
            db.close()

    def get_movie_count(self):
        """Get total number of movies in PostgreSQL"""
        db = self.SessionLocal()
        try:
            return db.query(MovieMetadata).count()
        finally:
            db.close()

    def get_all_genres(self):
        """Get list of all unique genres"""
        try:
            response = self.es.search(
                index="movies",
                body={
                    "size": 0,
                    "aggs": {
                        "unique_genres": {
                            "terms": {
                                "field": "genres",
                                "size": 100
                            }
                        }
                    }
                }
            )
            return [bucket["key"] for bucket in response["aggregations"]["unique_genres"]["buckets"]]
        except Exception as e:
            print(f"Error getting genres: {str(e)}")
            return []

    def get_trending_movies(self, size=10):
        """Get trending movies based on views and ratings"""
        try:
            response = self.es.search(
                index="movies",
                body={
                    "size": size,
                    "query": {
                        "function_score": {
                            "query": {"match_all": {}},
                            "functions": [
                                {
                                    "field_value_factor": {
                                        "field": "views",
                                        "modifier": "log1p",
                                        "factor": 0.5
                                    }
                                },
                                {
                                    "field_value_factor": {
                                        "field": "average_rating",
                                        "modifier": "log1p",
                                        "factor": 0.5
                                    }
                                }
                            ],
                            "boost_mode": "sum"
                        }
                    }
                }
            )
            return response["hits"]["hits"]
        except Exception as e:
            print(f"Error getting trending movies: {str(e)}")
            return []

    def get_recommendations(self, movie_id, size=5):
        """Get movie recommendations based on similar genres and keywords"""
        try:
            movie = self.get_movie_details(movie_id)
            if not movie:
                return []

            response = self.es.search(
                index="movies",
                body={
                    "size": size,
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "terms": {
                                        "genres": movie["genres"]
                                    }
                                }
                            ],
                            "must_not": [
                                {
                                    "term": {
                                        "movie_id": movie_id
                                    }
                                }
                            ]
                        }
                    }
                }
            )
            return response["hits"]["hits"]
        except Exception as e:
            print(f"Error getting recommendations: {str(e)}")
            return []

    def get_movies_by_genre(self, genre, page=1, size=10):
        """Get movies by genre"""
        try:
            response = self.es.search(
                index="movies",
                body={
                    "from": (page - 1) * size,
                    "size": size,
                    "query": {
                        "term": {
                            "genres": genre
                        }
                    },
                    "sort": [
                        {"popularity_score": {"order": "desc"}},
                        "_score"
                    ]
                }
            )
            return response["hits"]["hits"]
        except Exception as e:
            print(f"Error getting movies by genre: {str(e)}")
            return []