# Media-Streaming-Service
## homepage with search functionality supporting fuzzy and semantic search powered by elastic search database:
<img width="1438" alt="image" src="https://github.com/user-attachments/assets/6e526f37-2f06-46d5-b7ed-2a9843dab208">

## Movie Information Fetched from postgresql database:
<img width="1438" alt="image" src="https://github.com/user-attachments/assets/4c8aa703-6e21-4fa1-b843-aa84d328efb4">

## Movie recommendations considering Genre, Cast and IMDB Ratings of the movie:
<img width="1438" alt="image" src="https://github.com/user-attachments/assets/39d9e665-81f4-48e6-918d-40d93a3f4c50">

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

3. Install All Python dependencies:
```
pip install -r requirement.txt
```

4. Set up PostgreSQL and add your passwords in db_handler.py file:
- Install PostgreSQL
- Create a new database:
psql -U postgres
CREATE DATABASE moviedb;


5. Set up Elasticsearch and Kibana on localhost(Not in Docker) and add your passwords in db_handler.py file:
- Install Elasticsearch
- Start Elasticsearch service
- Make sure it's running on http://localhost:9200

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
│   │   └── movie_player.js
│   └── images/
│       └── posters/
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
    id SERIAL PRIMARY KEY,
    movie_id VARCHAR UNIQUE,
    title VARCHAR,
    plot_summary TEXT,
    release_date DATE,
    runtime INTEGER,
    budget FLOAT,
    revenue FLOAT,
    genres VARCHAR[],
    production_companies VARCHAR[],
    cast VARCHAR[],
    director VARCHAR,
    keywords VARCHAR[],
    streaming_url VARCHAR,
    trailer_url VARCHAR,
    poster_url VARCHAR,
    imdb_rating FLOAT,
    content_rating VARCHAR,
    language VARCHAR,
    popularity_score FLOAT
);
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
                    "keyword": {"type": "keyword"}
                }
            },
            "plot_summary": {"type": "text"},
            "genres": {"type": "keyword"},
            "cast": {"type": "keyword"},
            "director": {"type": "keyword"},
            "language": {"type": "keyword"},
            "content_rating": {"type": "keyword"},
            "popularity_score": {"type": "float"}
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
