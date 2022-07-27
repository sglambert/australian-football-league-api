# Australian-Football-League-API
The Australian-Football-League-API (AFL-API) provides a free and simple way to retrieve AFL data from various sources.

For more information, please see the [documentation](https://australian-football-league-api.herokuapp.com/api/docs).

### Built with
- Python
- Flask
- Docker

## Getting Started

### Usage

The API can be used to retrieve 6 different types of data, including: ```fixture, ladder, lineup, player details, player statistics``` and ```results```.


The following examples (below) display how to get data from the ```fixture``` API endpoint. In both instances the returned object will be JSON.

|Request|Python|
--- | --- |

```
import requests

response = requests.request(
    'GET',
    'https://australian-football-league-api.herokuapp.com/fixture',
    params={
        'season': 2022,
        'round_number': 1,
        'source': 'AFL',
        'competition': 'AFLM'
    }
)
```

|Request|cURL|
--- | --- |

```
curl -X GET "https://australian-football-league-api.herokuapp.com/fixture?season=2022&round_number=1&source=AFL&competition=AFLM" -H "accept: application/json"
```

The [documentation](https://australian-football-league-api.herokuapp.com/api/docs) provides further information and examples on how to retrieve data from the API.

### Contributing
Any contributions and/or suggestions to improve the API are much appreciated!

If you have an idea that would improve the project please feel free to [raise an issue](https://github.com/sglambert/australian-football-league-api/issues), fork the repo and create a pull request.

    Fork the project
    Create your feature branch (git checkout -b feature/featureName)
    Commit your changes (git commit -m 'Added some feature')
    Push to github (git push origin feature/featureName)
    Open a pull request

### Testing Locally

```docker build -t afl-api .```

```docker run -it -p 5000:5000 afl-api```

The following resources will then available on your local machine:

Localhost home page: ```http://127.0.0.1:5000```

Localhost API docs: ```http://127.0.0.1:5000/api/docs```

### License

Distributed under the MIT License. Please see [MIT](https://choosealicense.com/licenses/mit/) for more details.

### Contact
Sammy Lambert - sam.gervase.lambert@gmail.com

### Acknowledgments
[AFL](https://www.afl.com.au/)

[afltables](https://afltables.com/afl/afl_index.html)

[fitzRoy](https://github.com/jimmyday12/fitzRoy)

[footywire](https://www.footywire.com/)

[fryzigg](https://twitter.com/fryzigg?lang=en)

[Squiggle](https://api.squiggle.com.au/)
