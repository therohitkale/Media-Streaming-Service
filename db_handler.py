from sqlalchemy import create_engine, Column, Integer, String, Float, ARRAY, JSON, Text, Date, text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
from cassandra.cluster import Cluster
from datetime import datetime, timedelta
import random
import json
from sentence_transformers import SentenceTransformer

# Database configurations
POSTGRES_URL = "postgresql://postgres:postgres@localhost/moviedb"
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASSWORD = "0wM4UnTI"

# Load the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

Base = declarative_base()

class MovieMetadata(Base):
    __tablename__ = "movie_metadata"
    __table_args__ = (
        UniqueConstraint("movie_id", "language", name="uq_movie_id_language"),
        {'postgresql_partition_by': 'LIST (language)'},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    language = Column(String, nullable=False, primary_key=True)
    movie_id = Column(String, nullable=False)
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

        cassandra_hosts = [('localhost', 9042), ('localhost', 9043)]
        
        self.cluster = Cluster(contact_points=cassandra_hosts)
        self.cassandra_session = self.cluster.connect()

        rows = self.cassandra_session.execute("SELECT keyspace_name FROM system_schema.keyspaces;")
        print("Keyspaces in Cassandra cluster:")
        for row in rows:
            print(f"- {row.keyspace_name}")
        
        print("Database connections initialized")

    def create_language_partitions(self, engine):
        try:
            partitions = [
                ("English", "movie_metadata_english"),
                ("Korean", "movie_metadata_korean"),
                ("Spanish", "movie_metadata_spanish"),
            ]

            with engine.connect() as conn:
                # Debugging: Log partition creation
                print("Creating default partition...")
                conn.execute(text("""
                    CREATE TABLE movie_metadata_default
                    PARTITION OF movie_metadata
                    DEFAULT;
                """))

                for language, partition_name in partitions:
                    print(f"Creating partition for language: {language}")
                    conn.execute(text(f"""
                        CREATE TABLE {partition_name}
                        PARTITION OF movie_metadata
                        FOR VALUES IN ('{language}');
                    """))
                print("Partitions created successfully!")

                result = conn.execute(text("""SELECT table_name FROM information_schema.tables WHERE table_name = 'movie_metadata';"""))
                for row in result:
                    print(row)
        except Exception as e:
            print(f"Error creating partitions: {e}")


    def init_postgres(self):
        """Initialize PostgreSQL database"""
        Base.metadata.create_all(bind=self.engine)
        self.create_language_partitions(self.engine)

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
                    "number_of_replicas": 2
                }
            }
        }
        
        if not self.es.indices.exists(index="movies"):
            self.es.indices.create(index="movies", body=movies_mapping)

    def init_cassandra(self):
        """Initialize Cassandra by creating the table if it doesn't exist"""
        try:
            # Check if the keyspace exists
            keyspace_query = """
            SELECT keyspace_name FROM system_schema.keyspaces
            WHERE keyspace_name = 'media_streaming';
            """
            rows = self.cassandra_session.execute(keyspace_query)
            
            # If keyspace doesn't exist, create it
            if not rows:
                create_keyspace_query = """
                CREATE KEYSPACE media_streaming
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 2};
                """
                self.cassandra_session.execute(create_keyspace_query)
                print("Keyspace 'media_streaming' created successfully.")
            else:
                print("Keyspace 'media_streaming' already exists.")

            # Set the keyspace
            self.cassandra_session.set_keyspace('media_streaming')

            # Define the Cassandra table schema
            create_table_query = """
            CREATE TABLE IF NOT EXISTS trending_movies (
                bucket TEXT,
                movie_id TEXT,
                play_count INT,
                PRIMARY KEY (bucket, movie_id)
            ) WITH CLUSTERING ORDER BY (movie_id ASC);
            """

            # Execute the query
            self.cassandra_session.execute(create_table_query)
            print("Cassandra table created or already exists.")
        except Exception as e:
            raise Exception(f"Error initializing Cassandra table: {str(e)}")

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

            poster_url = [
                "/3k8jv1kSAAc0rCfFGtWDDQL4dfK.jpg",
                "/vpnVM9B6NMmQpWeZvzLvDESb2QY.jpg",
                "/w39qKYjltCix18BwtoZ1e45usdb.jpg",
                "/ssFS25CiYQvRJqErqaEyHuVgyH7.jpg",
                "/spWV1eRzlDxvai8LbxwAWR0Vst4.jpg",
                "/pnXLFioDeftqjlCVlRmXvIdMsdP.jpg",
                "/ouCgGNEC7zOIreWIt3ivgzI8XGf.jpg",
                "/jrHIKDq9xvKJhYBDvYwmAfs8qvr.jpg",
                "/vb6qzT0egUPHcmUwusPNl9j943p.jpg",
                "/2uNW4WbgBXL25BAbXGLnLqX71Sw.jpg",
                "/ys0jZr0quHERDUEoCboGQEKPvgQ.jpg",
                "/qpdFKDvJS7oLKTcBLXOaMwUESbs.jpg",
                "/zw4kV7npGtaqvUxvJE9IdqdFsNc.jpg",
                "/xBJnIvRdL0nDHgvivr6EgBQizes.jpg",
                "/7fR3KxswtY8OHHZuOUB9td58CRX.jpg",
                "/6izwz7rsy95ARzTR3poZ8H6c5pp.jpg",
                "/jEvytxNa5mfW7VAUmDWsZtIdATc.jpg",
                "/uQhYBxOVFU6s9agD49FnGHwJqG5.jpg",
                "/1MJNcPZy46hIy2CmSqOeru0yr5C.jpg",
                "/mQC3nIJ9DQ74t9vFzUjqP8eohgX.jpg",
                "/4YZpsylmjHbqeWzjKpUEF8gcLNW.jpg",
                "/aosm8NMQ3UyoBVpSxyimorCQykC.jpg",
                "/ht8Uv9QPv9y7K0RvUyJIaXOZTfd.jpg",
                "/wTnV3PCVW5O92JMrFvvrRcV39RU.jpg",
                "/2cxhvwyEwRlysAmRH4iodkvo0z5.jpg",
                "/c5Tqxeo1UpBvnAc3csUm7j3hlQl.jpg",
                "/xFSIygDiX70Esp9dheCgGX0Nj77.jpg",
                "/ory8WuAqznTE7lfopTSymHpop2t.jpg",
                "/l1175hgL5DoXnqeZQCcU3eZIdhX.jpg",
                "/wIGJnIFQlESkC2rLpfA8EDHqk4g.jpg",
                "/cNtAslrDhk1i3IOZ16vF7df6lMy.jpg",
                "/bx92hl70NUhojjO3eV6LqKllj4L.jpg",
                "/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg",
                "/y1xm0jMIlx9Oo2a3jWNyLGm43sJ.jpg",
                "/lqoMzCcZYEFK729d6qzt349fB4o.jpg",
                "/4dRtXjk1rcsZlaMJpBn6Nh9cTfO.jpg",
                "/cdqLnri3NEGcmfnqwk2TSIYtddg.jpg",
                "/b33nnKl1GSFbao4l3fZDDqsMx0F.jpg",
                "/qbkAqmmEIZfrCO8ZQAuIuVMlWoV.jpg",
                "/wWba3TaojhK7NdycRhoQpsG0FaH.jpg",
                "/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg",
                "/i77OInTKcrnRlAozFOaB6D5mk15.jpg",
                "/7Z2K08J0WantJHNa0vLTOmii41l.jpg",
                "/hq1EaYIqUNrPM3QFYAbnH2UHoX8.jpg",
                "/ooHEL3XyLYu3hus5cMnpjeH4e7A.jpg",
                "/hhiR6uUbTYYvKoACkdAIQPS5c6f.jpg",
                "/w46Vw536HwNnEzOa7J24YH9DPRS.jpg",
                "/oGythE98MYleE6mZlGs5oBGkux1.jpg",
                "/b2YL2kncIqlcDcqly78AsOPJi6r.jpg",
                "/dzDMewC0Hwv01SROiWgKOi4iOc1.jpg",
                "/uCkANtG6ezb7hjRKVudY3PUcbvn.jpg",
                "/gBenxR01Uy0Ev9RTIw6dVBPoyQU.jpg",
                "/jvug7Esd89yNLJwGvUfeQ9j69cE.jpg",
                "/8XsQVmGQukwIVDM88Aa0C7L5hCp.jpg",
                "/raDMchyq3dJMqso2TVh75A123Xb.jpg",
                "/d8Ryb8AunYAuycVKDp5HpdWPKgC.jpg",
                "/8fYluTtB3b3HKO7KQa5tzrvGaps.jpg",
                "/zPOOyw6HBb5Qo6uaWJ5UxrBR6Ll.jpg",
                "/hf94ySIzdP3KwHau9VSWh7b7Qu2.jpg",
                "/hklQwv6QVoOp5bWyh1bjuF2ydyG.jpg",
                "/kDp1vUBnMpe8ak4rjgl3cLELqjU.jpg",
                "/xNLiMNyFzKTL9PVIEulG55Hei8j.jpg",
                "/m5x8D0bZ3eKqIVWZ5y7TnZ2oTVg.jpg",
                "/blRsgsexoBqnjcEJkV8beKAVT6J.jpg",
                "/7d8VB7xZcsjClsE6JaUr8BCbkCh.jpg",
                "/8rdB1wkheEMMqcY8qLAKjCMPcnZ.jpg",
                "/58QT4cPJ2u2TqWZkterDq9q4yxQ.jpg",
                "/hzrvol8K2VWm2BsDTwb8YvRMzIH.jpg",
                "/p6AbOJvMQhBmffd0PIv0u8ghWeY.jpg",
                "/kKgQzkUCnQmeTPkyIwHly2t6ZFI.jpg",
                "/oqhaffnQqSzdLrYAQA5W4IdAoCX.jpg",
                "/nUKfbKv4RD1YxlsNWd0BwabEf3P.jpg",
                "/AmUs3hximCKa90sHuIRr5Bz8ci5.jpg",
                "/pXENxAzOBrTSDJGxDcUnlNTNmWr.jpg",
                "/o8qtMeCskitW5QwSu6O1nP4jN6z.jpg",
                "/oEJC05CqPugMxC4rFu9r6r6vg6m.jpg",
                "/8Sok3HNA3r1GHnK2lCytHyBz1A.jpg",
                "/xbKFv4KF3sVYuWKllLlwWDmuZP7.jpg",
                "/ilMXOocCCwPWCcDLLa6M0ga8vWt.jpg",
                "/92olhXYaIX6lvB8jwFz4OSfPaKq.jpg",
                "/gKkl37BQuKTanygYQG1pyYgLVgf.jpg",
                "/z1p34vh7dEOnLDmyCrlUVLuoDzd.jpg",
                "/kYp5C3oIHV98E5NnObCuadLyOml.jpg",
                "/cfkcrKySRyJiIdLo6c6kNSyLFh7.jpg",
                "/dFu8oHN805ZRzpQZNOjkiLzMbep.jpg",
                "/f6PfAXtFEkJRcBtOjbzOgz8qqSK.jpg",
                "/1iPuEIcybEc9Y6aKJ8BGAnMadFX.jpg",
                "/ae434jM5NG2kKX1rRkG5giMhpPI.jpg",
                "/5ikADeVa7HAEOMmi0CZWiT95KHl.jpg",
                "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
                "/hU42CRk14JuPEdqZG3AWmagiPAP.jpg",
                "/7SBOaeKcPsvquHKhyKUN8gZ4tzo.jpg",
                "/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg",
                "/pjnD08FlMAIXsfOLKQbvmO0f0MD.jpg",
                "/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg",
                "/iADOJ8Zymht2JPMoy3R7xceZprc.jpg",
                "/1Bc9VNd9CIHIyJtPKFqSQzrXWru.jpg",
                "/fiVW06jE7z9YnO4trhaMEdclSiC.jpg",
                "/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg",
                "/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg",
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
                "poster_url": f"https://image.tmdb.org/t/p/w500{poster_url[i%100]}",
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