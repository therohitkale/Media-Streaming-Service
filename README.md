# Media-Streaming-Service
### Distributed and Scalable media streaming platform leveraging PostgreSQL, Elasticsearch, and Cassandra for advanced search, real-time analytics, and fault tolerance.

![Alt Text](static\images\home_img.jpg)

## Movie Information Fetched from postgresql database:
![Alt Text](static\images\movie_detail.jpg)

## Movie recommendations considering Genre, Cast and IMDB Ratings of the movie:
![Alt Text](static\images\recommendation.jpg)

# Media Streaming Service

A Netflix-style streaming service built with Flask, Elasticsearch, and PostgreSQL.

## Features
- Movie search with filters
- Genre-based browsing
- Trending movies section
- Movie details with recommendations
- Netflix-style UI
- Advanced search filters
- Responsive design

## Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Elasticsearch 7.x or higher
- Node.js and npm (for frontend development)

## Installation Steps

1. Clone the repository:
git clone https://github.com/therohit/media-streaming-service.git
cd media-streaming-service

2. Create and activate a virtual environment:
- Create a Virtual Environment
```
python -m venv venv
```

- Activate the Virtual Environment

### For Windows
```
venv\Scripts\activate
```
### For Mac
```
source venv/bin/activate
```

3. Install All Python dependencies:
```
pip install -r requirement.txt
```

4. Set up PostgreSQL and add your passwords in db_handler.py file:
- Install PostgreSQL
- Create a new database:
```
psql -U postgres
CREATE DATABASE moviedb;
```
- Create movie_metadata table
```
CREATE TABLE movie_metadata (
    id SERIAL,
    language TEXT NOT NULL,
    movie_id TEXT NOT NULL,
    title TEXT,
    plot_summary TEXT,
    release_date DATE,
    runtime INTEGER,
    budget FLOAT,
    revenue FLOAT,
    genres TEXT[],
    production_companies TEXT[],
    "cast" TEXT[],
    director TEXT,
    keywords TEXT[],
    streaming_url TEXT,
    trailer_url TEXT,
    poster_url TEXT,
    imdb_rating FLOAT,
    content_rating TEXT,
    popularity_score FLOAT,
    views INTEGER DEFAULT 0,
    average_rating FLOAT DEFAULT 0.0,
    PRIMARY KEY (id, language),
    UNIQUE (movie_id, language)
) PARTITION BY LIST (language);
```
- Create partition tables on language
```
CREATE TABLE IF NOT EXISTS movie_metadata_language_default
    PARTITION OF movie_metadata
    DEFAULT;

CREATE TABLE IF NOT EXISTS movie_metadata_english
    PARTITION OF movie_metadata
    FOR VALUES IN ('English');

CREATE TABLE IF NOT EXISTS movie_metadata_spanish
    PARTITION OF movie_metadata
    FOR VALUES IN ('Spanish');

CREATE TABLE IF NOT EXISTS movie_metadata_korean
    PARTITION OF movie_metadata
    FOR VALUES IN ('Korean');
```

5. Set up Elasticsearch and Kibana on localhost(Not in Docker) and add your passwords in db_handler.py file:
- Download ElasticSearch and unzip by following the link. https://www.elastic.co/downloads/elasticsearch

- Download Kibana and unzip by following the link. https://www.elastic.co/downloads/kibana

- Run ElasticSearch in the ElasticSearch directory.
- Save the generated password for the elastic user and the enrollment token
for Kibana in a secure location. These values are shown only once when you
start Elasticsearch for the rst time. Also, note that the enrollment token for
Kibana is only valid for the next 30 min!
```
bin/elasticsearch for Linux/MacOS
bin\elasticsearch.bat for Windows
```

- Make three copies of elasticsearch folder to create the multinode cluster and follow the same above steps for each folder to setup 3 elasticsearch nodes

- Run Kibana in the Kibana directory:
```
bin/kibana for Linux/MacOS
bin\kibana.bat for Windows
```
- Go to the localhost link written in the terminal. If your enrollment token is not
valid, generate a new enrollment token by running the following command
from the Elasticsearch installation directory:
```
bin\elasticsearch-create-enrollment-token.bat --scope kibana
```
- After completing Kibana setup, enter username and password to login Kibana.
- Install elasticsearch
```
pip install elasticsearch
```

6. Set up Multinode cassandra on docker
- docker pull cassandra:latest
- Run the first node
```
docker run --name cassandra-1 -p 9042:9042 -d cassandra
INSTANCE1=$(docker inspect --format="{{ .NetworkSettings.IPAddress }}" cassandra-1)
echo "INSTANCE1: ${INSTANCE1}"
```

- Run the second node
```
docker run --name cassandra-2 -p 9043:9042 -d -e CASSANDRA_SEEDS=$INSTANCE1 cassandra
INSTANCE2=$(docker inspect --format="{{ .NetworkSettings.IPAddress }}" cassandra-2)
echo "INSTANCE2: ${INSTANCE2}"
```


7. Initialize the database and load sample data:
python movapp.py


## Project Structure
```
media-streaming-service/
├── movapp.py                  # Main Flask application
├── db_handler.py           # Database operations
├── requirements.txt        # Python dependencies
├── static/                 # Static files
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   ├── main.js
│   │   ├── search.js
│   │   └── moviePlayer.js
│   └── images/
│       └── posters/
│       └── actors/
├── templates/              # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── search.html
│   └── movie_details.html
└── README.md
```


Update database configurations in `db_handler.py` if not using .env:
```python
POSTGRES_URL = "postgresql://postgres:your_password@localhost/moviedb"
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASSWORD = "your_elastic_password"
```

## Running the Application

1. Make sure PostgreSQL and Elasticsearch are running

2. Start the Flask application:
```bash
python movapp.py
```

3. Access the application:
```
http://localhost:5000
```

## Python modules Requirements

```
flask==2.3.3
elasticsearch==8.10.0
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
flask-cors==4.0.0
python-dotenv==1.0.0
Werkzeug==2.3.7
Jinja2==3.1.2
```



## API Endpoints

- `GET /api/movies/search` - Search movies with filters
- `GET /api/movies/<movie_id>` - Get movie details
- `GET /api/genres` - Get all genres
- `GET /api/trending` - Get trending movies
- `GET /api/recommendations/<movie_id>` - Get movie recommendations

## Database Schema

### PostgreSQL

Movie metadata table:
```sql
CREATE TABLE movie_metadata (
    id SERIAL,
    language TEXT NOT NULL,
    movie_id TEXT NOT NULL,
    title TEXT,
    plot_summary TEXT,
    release_date DATE,
    runtime INTEGER,
    budget FLOAT,
    revenue FLOAT,
    genres TEXT[],
    production_companies TEXT[],
    "cast" TEXT[],
    director TEXT,
    keywords TEXT[],
    streaming_url TEXT,
    trailer_url TEXT,
    poster_url TEXT,
    imdb_rating FLOAT,
    content_rating TEXT,
    popularity_score FLOAT,
    views INTEGER DEFAULT 0,
    average_rating FLOAT DEFAULT 0.0,
    PRIMARY KEY (id, language),
    UNIQUE (movie_id, language)
) PARTITION BY LIST (language);
```

### Elasticsearch

Movie index mapping:
```json
{
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
```

## Common Issues

1. Elasticsearch SSL Warning:
   - Add `verify_certs=False` and `ssl_show_warn=False` to Elasticsearch client configuration

2. PostgreSQL Connection:
   - Ensure correct credentials in connection string
   - Check if PostgreSQL service is running

3. Static Files Not Found:
   - Ensure correct directory structure
   - Check file permissions
   - Verify static folder configuration in Flask app

## License

This project is licensed under the MIT License - see the LICENSE file for details.
```
